"""
Module 4/7: SUBTITLE GENERATION
Tạo file phụ đề .srt cho toàn bộ video.

BẢN MỚI: dùng faster-whisper (chạy local) để lấy WORD-LEVEL TIMESTAMP THẬT từ
chính file audio mỗi cảnh (scene.audio_path), thay vì ước lượng timing theo tỉ
lệ số từ như bản cũ. Nhờ vậy phụ đề khớp đúng với giọng đọc thật (đọc nhanh/
chậm không đều giữa các câu không còn làm lệch phụ đề).

QUAN TRỌNG: whisper CHỈ được dùng để lấy MỐC THỜI GIAN (word timestamps), text
hiển thị trên phụ đề vẫn lấy từ scene.narration GỐC (không dùng text whisper
tự nhận diện), để tránh sai chính tả/dấu tiếng Việt do whisper đoán nhầm. Số từ
whisper nhận được và số từ trong narration gốc có thể lệch (whisper gộp/tách từ
khác) -> ánh xạ theo TỈ LỆ VỊ TRÍ (từ thứ k trong N từ narration -> lấy mốc
thời gian của từ ở vị trí tương ứng k/N trong danh sách timestamp whisper trả
về), không map 1-1 tuyệt đối.

FALLBACK: nếu faster-whisper lỗi (chưa cài, tải model lỗi, audio hỏng...) với
BẤT KỲ cảnh nào, toàn bộ video rơi về cách ước lượng theo tỉ lệ số từ (bản cũ)
để pipeline không bị dừng giữa chừng.
"""
import os
import sys
import datetime
import re

import srt

import config
from modules.cli_progress import write_progress
from modules.script_parser import Scene

MAX_CHARS_PER_SUBTITLE_LINE = 42  # chuẩn phổ biến để phụ đề không tràn khung hình

_whisper_model = None  # cache model, chỉ load 1 lần cho cả video


def _split_narration_into_chunks(text: str) -> list[str]:
    """Chia narration thành các câu/cụm ngắn để hiển thị phụ đề dễ đọc."""
    sentences = re.split(r"(?<=[.!?…])\s+", text.strip())
    chunks = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= MAX_CHARS_PER_SUBTITLE_LINE * 2:
            chunks.append(sentence)
        else:
            words = sentence.split()
            current = ""
            for w in words:
                if len(current) + len(w) + 1 > MAX_CHARS_PER_SUBTITLE_LINE * 2:
                    chunks.append(current.strip())
                    current = w
                else:
                    current = f"{current} {w}".strip()
            if current:
                chunks.append(current.strip())
    return chunks or [text.strip()]


def _get_whisper_model():
    """Load model faster-whisper 1 lần duy nhất (cache toàn cục). Ném lỗi ra
    ngoài nếu package chưa cài hoặc model tải lỗi -- caller (generate_srt) sẽ
    bắt lỗi này để fallback toàn bộ về cách ước lượng cũ."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        model_size = getattr(config, "WHISPER_MODEL_SIZE", "small")
        device = getattr(config, "WHISPER_DEVICE", "cpu")
        compute_type = getattr(config, "WHISPER_COMPUTE_TYPE", "int8")
        _whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _whisper_model


def _get_word_timestamps(audio_path: str) -> list[tuple[float, float]]:
    """Chạy whisper trên 1 file audio, trả về danh sách (start, end) của TỪNG
    TỪ theo đúng thứ tự xuất hiện trong audio. Có thể trả về danh sách rỗng
    nếu audio toàn khoảng lặng (không có lời nói).

    QUAN TRỌNG [sửa lỗi hiệu năng]: language LUÔN lấy từ config.WHISPER_LANGUAGE
    (mặc định "en") thay vì hard-code "vi" như bản trước -- hard-code sai ngôn
    ngữ so với giọng TTS thật (kịch bản/giọng đọc hiện tại của pipeline là tiếng
    Anh) khiến whisper CHẬM ĐI RÕ RỆT (decoder phải vật lộn ép âm thanh đúng
    sang ngôn ngữ sai) và cho ra timestamp kém chính xác hơn, dù không lỗi cú
    pháp nên không bị phát hiện ngay."""
    model = _get_whisper_model()
    language = getattr(config, "WHISPER_LANGUAGE", "en")
    segments, _ = model.transcribe(audio_path, language=language, word_timestamps=True)
    word_spans = []
    for segment in segments:
        if not segment.words:
            continue
        for w in segment.words:
            word_spans.append((w.start, w.end))
    return word_spans


def _map_chunks_to_timestamps(chunks: list[str], word_spans: list[tuple[float, float]],
                               scene_duration: float) -> list[tuple[float, float]]:
    """Ánh xạ từng chunk (cụm câu hiển thị phụ đề) sang khoảng thời gian THẬT,
    dựa trên vị trí TỈ LỆ của từ đầu/cuối chunk đó trong tổng số từ narration,
    tra vào danh sách word_spans (timestamp thật theo whisper).

    Nếu word_spans rỗng (whisper không nhận ra từ nào, ví dụ audio lỗi/câm) ->
    ném lỗi để caller fallback cách ước lượng cho riêng cảnh này."""
    if not word_spans:
        raise ValueError("Whisper không nhận diện được từ nào trong audio cảnh này.")

    total_words = sum(len(c.split()) for c in chunks) or 1
    num_spans = len(word_spans)

    result = []
    word_cursor = 0  # vị trí từ (theo narration) đã đi qua
    prev_end = 0.0  # đảm bảo các chunk không chồng lấn/lùi thời gian (monotonic)
    for chunk in chunks:
        chunk_word_count = len(chunk.split())
        start_word_idx = word_cursor
        end_word_idx = word_cursor + chunk_word_count - 1
        word_cursor += chunk_word_count

        # Ánh xạ tỉ lệ: vị trí từ trong khoảng [0, total_words-1] -> vị trí
        # tương ứng trong khoảng [0, num_spans-1] của whisper.
        start_span_idx = int(start_word_idx / total_words * num_spans)
        end_span_idx = int(end_word_idx / total_words * num_spans)
        start_span_idx = min(max(start_span_idx, 0), num_spans - 1)
        end_span_idx = min(max(end_span_idx, 0), num_spans - 1)

        chunk_start = max(word_spans[start_span_idx][0], prev_end)
        chunk_end = word_spans[end_span_idx][1]
        if chunk_end <= chunk_start:
            chunk_end = min(chunk_start + 0.8, scene_duration)
        chunk_end = max(chunk_end, chunk_start)  # an toàn tuyệt đối, không bao giờ end < start

        result.append((chunk_start, chunk_end))
        prev_end = chunk_end

    return result


def _estimate_chunks_by_word_ratio(chunks: list[str], scene_duration: float) -> list[tuple[float, float]]:
    """Cách ước lượng CŨ (fallback): chia đều theo tỉ lệ số từ trên tổng thời
    lượng cảnh, không dùng timestamp thật."""
    total_words = sum(len(c.split()) for c in chunks) or 1
    result = []
    cursor = 0.0
    for chunk in chunks:
        weight = len(chunk.split()) / total_words
        chunk_duration = max(scene_duration * weight, 0.8)
        result.append((cursor, cursor + chunk_duration))
        cursor += chunk_duration
    return result


def _print_step_progress(done: int, total: int, label: str) -> None:
    write_progress("SUBTITLE", done, total, label)


def generate_srt(scenes: list[Scene], work_dir: str) -> str:
    """Lưu ý: audio các cảnh luôn nối liền tuần tự (không chồng lên nhau,
    xem modules/video_compose.py), nên mốc thời gian phụ đề = tổng cộng dồn
    thời lượng audio thật, KHÔNG trừ transition (hình ảnh có hoà tan/crossfade
    nhưng đó chỉ là hiệu ứng thị giác, không dịch mốc audio).

    Timing từng dòng phụ đề trong 1 cảnh ưu tiên lấy từ WORD-LEVEL TIMESTAMP
    thật (faster-whisper, xem _get_word_timestamps). Nếu whisper lỗi (thiếu
    package, model tải lỗi, audio hỏng...) với BẤT KỲ cảnh nào, toàn bộ video
    tự động rơi về cách ước lượng theo tỉ lệ số từ (bản cũ), không dừng pipeline."""
    use_whisper = True
    try:
        _get_whisper_model()
    except Exception as e:
        print(f"  [SUBTITLE] CẢNH BÁO: không khởi tạo được faster-whisper ({e}). "
              f"-> Dùng cách ước lượng timing theo tỉ lệ số từ (kém chính xác hơn) cho TOÀN BỘ video.")
        use_whisper = False

    subtitles = []
    sub_index = 1
    scene_start = 0.0

    for index, scene in enumerate(scenes, start=1):
        _print_step_progress(index, len(scenes), f"cảnh {scene.index}")
        chunks = _split_narration_into_chunks(scene.narration)
        scene_duration = scene.duration or (sum(len(c.split()) for c in chunks) / config.WORDS_PER_SECOND)

        spans = None
        if use_whisper:
            try:
                word_spans = _get_word_timestamps(scene.audio_path)
                spans = _map_chunks_to_timestamps(chunks, word_spans, scene_duration)
            except Exception as e:
                print(f"  [SUBTITLE] Cảnh {scene.index}: whisper lỗi ({e}) -> dùng ước lượng "
                      f"theo tỉ lệ số từ CHỈ CHO CẢNH NÀY.")
                spans = None

        if spans is None:
            spans = _estimate_chunks_by_word_ratio(chunks, scene_duration)

        for chunk, (rel_start, rel_end) in zip(chunks, spans):
            start = datetime.timedelta(seconds=scene_start + rel_start)
            end = datetime.timedelta(seconds=scene_start + rel_end)
            subtitles.append(srt.Subtitle(index=sub_index, start=start, end=end, content=chunk))
            sub_index += 1

        scene_start += scene_duration

    srt_content = srt.compose(subtitles)
    out_path = os.path.join(work_dir, "subtitles.srt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    sys.stdout.write("\r")
    sys.stdout.flush()
    print(f"  [SUBTITLE] Đã tạo phụ đề -> {out_path} ({'whisper timestamp thật' if use_whisper else 'ước lượng theo tỉ lệ từ'})")
    return out_path

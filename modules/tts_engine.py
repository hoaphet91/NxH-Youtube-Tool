"""
Module 2/7: TTS ENGINE
Chuyển narration text của từng cảnh thành file audio (.mp3), hỗ trợ 3 provider:
- ElevenLabs (chất lượng giọng tự nhiên cao, cần ELEVENLABS_API_KEY + ELEVENLABS_VOICE_ID)
- OpenAI TTS (model tts-1 / tts-1-hd, cần OPENAI_API_KEY)
- edge-tts (Microsoft, MIỄN PHÍ, không cần API key, gọi qua CLI "edge-tts")

Nếu config.TTS_ENABLED = False (đặt TTS_ENABLED=false trong .env), module này
KHÔNG gọi API TTS thật -> thay vào đó lấy audio có sẵn trong config.LOCAL_AUDIO_DIR
(người dùng tự chuẩn bị, sắp theo thời gian tạo file) để test nhanh các bước
sau mà không tốn phí/token API. Xem _sync_local_audio_for_scenes().

TỰ ĐỘNG THỬ LẠI KHI LỖI: cả 3 provider đều phụ thuộc mạng nên có thể gặp lỗi
tạm thời (timeout, mất kết nối, edge-tts bị ngắt giữa chừng...). Mỗi cảnh lỗi
sẽ được tự động thử lại tối đa TTS_MAX_RETRIES lần (xem _run_with_retry). Nếu
1 cảnh vẫn lỗi sau khi đã thử hết số lần đó, pipeline KHÔNG dừng ngay -- vẫn
TIẾP TỤC tạo audio cho các cảnh còn lại, rồi báo cáo tổng kết đầy đủ các cảnh
lỗi ở cuối và dừng lại (vì bước sau cần audio đầy đủ 100% mới chạy được).
"""
import os
import shutil
import subprocess
import sys
import time
import requests
from pydub.utils import mediainfo

import config
from modules.cli_progress import write_progress
from modules.script_parser import Scene

VALID_AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a")

# Số lần thử lại tối đa khi 1 cảnh bị lỗi TTS (mạng chập chờn, edge-tts bị
# ngắt giữa chừng...), và thời gian nghỉ (giây) giữa mỗi lần thử lại.
TTS_MAX_RETRIES = 3
TTS_RETRY_DELAY_SECONDS = 3.0

# Sau khi chạy hết 1 lượt toàn bộ cảnh, nếu vẫn còn cảnh lỗi (đã thử
# TTS_MAX_RETRIES lần/cảnh mà không được), tự động QUAY LẠI chạy riêng các
# cảnh đó thêm 1 lượt nữa -- lặp lại tối đa TTS_MAX_PASSES lượt, KHÔNG hỏi
# lại người dùng. Chỉ dừng hẳn (raise) nếu sau đủ số lượt này vẫn còn lỗi.
TTS_MAX_PASSES = 3


def _print_tts_progress(done: int, total: int, scene_index: int, status: str,
                        provider: str | None = None, duration: float | None = None) -> None:
    extra = []
    if provider:
        extra.append(provider)
    if duration is not None:
        extra.append(f"{duration:.1f}s")
    extra_text = " | ".join(extra) if extra else None
    write_progress("TTS", done, total, f"Cảnh {scene_index}: {status}", extra=extra_text)


def _append_silence(audio_path: str, gap_seconds: float) -> None:
    """Nối THẬT một khoảng lặng gap_seconds vào cuối file audio_path (ghi đè
    tại chỗ qua file tạm). Dùng filter 'apad' của ffmpeg. Nếu gap_seconds <= 0
    thì không làm gì (không gọi ffmpeg)."""
    if gap_seconds <= 0:
        return

    tmp_path = audio_path + ".gap_tmp" + os.path.splitext(audio_path)[1]
    cmd = [
        "ffmpeg", "-y", "-i", audio_path,
        "-af", f"apad=pad_dur={gap_seconds:.6f}",
        tmp_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg lỗi khi thêm khoảng lặng vào '{audio_path}':\n{result.stderr[-2000:]}"
        )
    os.replace(tmp_path, audio_path)


def _apply_scene_gaps(scenes: list[Scene]) -> None:
    """Thêm config.SCENE_AUDIO_GAP giây lặng vào cuối audio của MỌI cảnh TRỪ
    cảnh cuối cùng (cảnh cuối không cần lặng sau nó), rồi đo lại scene.duration
    cho khớp với độ dài file thật sau khi đã pad.

    QUAN TRỌNG [sửa lệch Ken Burns "trôi" theo giọng đọc]: TRƯỚC khi pad gap,
    lưu lại scene.speech_duration = thời lượng lời thoại THẬT (chưa gồm gap).
    video_compose.py dùng speech_duration này (thay vì scene.duration) làm mốc
    tiến trình cho hiệu ứng Ken Burns -> camera dừng chuyển động ĐÚNG lúc giọng
    đọc dứt, phần gap phía sau chỉ là khung hình đứng yên, không tiếp tục
    pan/zoom sau khi tiếng đã im. Gán TRƯỚC nhánh return sớm (gap<=0) để
    speech_duration luôn đúng bằng duration khi tính năng gap bị tắt."""
    for scene in scenes:
        scene.speech_duration = scene.duration

    gap = config.SCENE_AUDIO_GAP
    if gap <= 0:
        return

    n = len(scenes)
    for i, scene in enumerate(scenes):
        if i == n - 1:
            continue  # cảnh cuối: không thêm lặng sau
        _append_silence(scene.audio_path, gap)
        info = mediainfo(scene.audio_path)
        scene.duration = float(info.get("duration", 0.0))


def _get_creation_time(path: str) -> float:
    """Giống logic trong modules/image_sync.py: dùng creation time thật trên
    Windows/macOS, dùng min(ctime, mtime) làm proxy trên Linux."""
    stat = os.stat(path)
    if hasattr(stat, "st_birthtime"):
        return stat.st_birthtime
    return min(stat.st_ctime, stat.st_mtime) if stat.st_ctime else stat.st_mtime


def _sync_local_audio_for_scenes(scenes: list[Scene], work_dir: str) -> None:
    """Dùng khi config.TTS_ENABLED=False: lấy audio có sẵn trong
    config.LOCAL_AUDIO_DIR (sắp theo thời gian tạo file, cũ -> mới), COPY
    (không rename, để giữ nguyên file gốc cho lần test sau) vào work_dir/audio/
    và gán trực tiếp vào scene.audio_path + scene.duration -- không gọi API TTS."""
    audio_dir = os.path.join(work_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    source_dir = config.LOCAL_AUDIO_DIR
    if not os.path.isdir(source_dir):
        raise FileNotFoundError(
            f"TTS_ENABLED=false nhưng không tìm thấy thư mục audio test: {source_dir}\n"
            f"      -> Tạo thư mục này, bỏ vào audio có sẵn cho từng cảnh (đúng thứ tự thời "
            f"gian tạo, tên file tuỳ ý) trước khi chạy pipeline."
        )

    paths = [
        os.path.join(source_dir, f) for f in os.listdir(source_dir)
        if f.lower().endswith(VALID_AUDIO_EXTENSIONS)
    ]
    if not paths:
        raise FileNotFoundError(
            f"Không tìm thấy file audio (.mp3/.wav/.m4a) nào trong: {source_dir}\n"
            f"      -> Bỏ audio có sẵn cho từng cảnh vào thư mục này trước khi chạy pipeline."
        )

    if len(paths) != len(scenes):
        raise ValueError(
            f"Số file audio test ({len(paths)}) KHÔNG khớp số cảnh trong kịch bản ({len(scenes)}).\n"
            f"      -> Thư mục: {source_dir}\n"
            f"      -> Mỗi cảnh cần đúng 1 file audio test, không thừa không thiếu."
        )

    paths.sort(key=_get_creation_time)

    print(f"  [TTS] TTS_ENABLED=false -> dùng {len(paths)} audio có sẵn từ {source_dir} (KHÔNG gọi API).")
    total = len(scenes)
    for i, (scene, src_path) in enumerate(zip(scenes, paths), start=1):
        ext = os.path.splitext(src_path)[1].lower()
        dest_path = os.path.join(audio_dir, f"scene_{scene.index:03d}{ext}")
        shutil.copyfile(src_path, dest_path)

        scene.audio_path = dest_path
        info = mediainfo(dest_path)
        scene.duration = float(info.get("duration", 0.0))
        _print_tts_progress(
            i, total, scene.index,
            f"dùng '{os.path.basename(src_path)}'",
            duration=scene.duration,
        )
    text = str(e).strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return type(e).__name__

    # Tìm dòng dạng "Something.Error: mô tả" (có dấu ':' và phần trước dấu ':'
    # trông giống tên exception -- không có khoảng trắng ở giữa, trừ khoảng
    # trắng ĐẦU dòng đã bị strip).
    for ln in lines:
        if ":" in ln:
            prefix = ln.split(":", 1)[0]
            if prefix and " " not in prefix and not prefix.startswith("-"):
                return ln[:200]

    return f"{type(e).__name__}: {lines[0][:180]}"


def _run_with_retry(fn, text: str, out_path: str, provider_name: str) -> None:
    """Gọi fn(text, out_path) với TỰ ĐỘNG THỬ LẠI (TTS_MAX_RETRIES lần, nghỉ
    TTS_RETRY_DELAY_SECONDS giây giữa mỗi lần) -- dùng chung cho cả 3 provider
    (ElevenLabs/OpenAI/edge-tts), vì cả 3 đều phụ thuộc mạng và có thể gặp lỗi
    tạm thời (timeout, mất kết nối, rate-limit thoáng qua...). Nếu file audio
    bị dở dang từ lần thử trước, xoá đi trước khi thử lại. Chỉ raise lỗi ra
    ngoài khi đã thử hết TTS_MAX_RETRIES lần.

    Log lúc ĐANG thử lại chỉ in 1 dòng ngắn gọn (_short_error_summary) --
    không in traceback/stderr dài dòng, vì đây là lỗi tạm thời thường tự
    khỏi ở lần thử sau (vd NoAudioReceived của edge-tts do rate-limit/mạng
    chập chờn). Thông báo lỗi ĐẦY ĐỦ chỉ xuất hiện trong exception cuối cùng
    (RuntimeError raise ở cuối hàm), dùng khi pipeline thực sự cần dừng."""
    last_error: Exception | None = None
    for attempt in range(1, TTS_MAX_RETRIES + 1):
        try:
            fn(text, out_path)
            return
        except Exception as e:
            last_error = e
            if os.path.exists(out_path):
                os.remove(out_path)  # xoá file dở dang/lỗi, tránh nhầm lẫn
            if attempt < TTS_MAX_RETRIES:
                print(f"  [TTS] {provider_name}: thử lại (lần {attempt}/{TTS_MAX_RETRIES} lỗi: "
                      f"{_short_error_summary(e)}) -> nghỉ {TTS_RETRY_DELAY_SECONDS:.0f}s...")
                time.sleep(TTS_RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"{provider_name} lỗi liên tục sau {TTS_MAX_RETRIES} lần thử -> bỏ qua, chuyển sang "
        f"cảnh tiếp theo. Lỗi cuối cùng: {last_error}"
    )



def _tts_elevenlabs_once(text: str, out_path: str) -> None:
    if not config.ELEVENLABS_API_KEY or not config.ELEVENLABS_VOICE_ID:
        raise EnvironmentError("Thiếu ELEVENLABS_API_KEY hoặc ELEVENLABS_VOICE_ID trong .env")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    if not resp.ok:
        raise RuntimeError(
            f"ElevenLabs trả về lỗi {resp.status_code}: {resp.text}\n"
            f"      -> Kiểm tra lại: (1) ELEVENLABS_API_KEY có copy đủ, không thiếu/thừa ký tự "
            f"khoảng trắng; (2) ELEVENLABS_VOICE_ID có thuộc tài khoản/plan hiện tại của bạn "
            f"không (vào elevenlabs.io > Voices để lấy đúng Voice ID); (3) tài khoản còn credit "
            f"không (free tier có giới hạn ký tự/tháng)."
        )
    with open(out_path, "wb") as f:
        f.write(resp.content)


def _tts_elevenlabs(text: str, out_path: str) -> None:
    """ElevenLabs với tự động thử lại -- xem _run_with_retry. Lỗi do thiếu
    API key/quota (EnvironmentError/lỗi 401/402...) VẪN được thử lại đủ số
    lần như lỗi mạng thông thường, vì hàm này không phân biệt loại lỗi --
    nếu là lỗi cấu hình thật (không phải tạm thời), pipeline vẫn dừng đúng
    sau khi hết lượt thử, chỉ chậm hơn vài giây so với raise ngay lập tức."""
    _run_with_retry(_tts_elevenlabs_once, text, out_path, "ElevenLabs")


def _tts_openai_once(text: str, out_path: str) -> None:
    from openai import OpenAI

    if not config.OPENAI_API_KEY:
        raise EnvironmentError("Thiếu OPENAI_API_KEY trong .env")

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    with client.audio.speech.with_streaming_response.create(
        model="tts-1-hd",
        voice="alloy",
        input=text,
    ) as response:
        response.stream_to_file(out_path)


def _tts_openai(text: str, out_path: str) -> None:
    """OpenAI TTS với tự động thử lại -- xem _run_with_retry (và ghi chú
    tương tự ở _tts_elevenlabs về lỗi cấu hình vs lỗi tạm thời)."""
    _run_with_retry(_tts_openai_once, text, out_path, "OpenAI TTS")


def _tts_edge_once(text: str, out_path: str) -> None:
    """1 lần gọi CLI "edge-tts" (miễn phí, không cần API key). Yêu cầu đã cài:
    pip install edge-tts. Ví dụ lệnh tương đương:
    edge-tts --voice en-US-AndrewNeural --rate=-15% --pitch=-10Hz --text "..." --write-media out.mp3"""
    cmd = [
        "edge-tts",
        "--voice", config.EDGE_TTS_VOICE,
        f"--rate={config.EDGE_TTS_RATE}",
        f"--pitch={config.EDGE_TTS_PITCH}",
        "--text", text,
        "--write-media", out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"edge-tts lỗi:\n{result.stderr[-2000:]}\n"
            f"      -> Kiểm tra: (1) đã cài package chưa (pip install edge-tts); "
            f"(2) EDGE_TTS_VOICE '{config.EDGE_TTS_VOICE}' có hợp lệ không (chạy "
            f"'edge-tts --list-voices' để xem danh sách); (3) có kết nối mạng không."
        )
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError(f"edge-tts chạy xong nhưng không tạo được file audio hợp lệ tại: {out_path}")


def _tts_edge(text: str, out_path: str) -> None:
    """edge-tts với tự động thử lại -- xem _run_with_retry. edge-tts đặc biệt
    hay bị NGẮT GIỮA CHỪNG hoặc lỗi kết nối tạm thời do phụ thuộc mạng tới
    server Microsoft (khác ElevenLabs/OpenAI vốn có API ổn định hơn), nên
    đây là provider hưởng lợi nhiều nhất từ cơ chế retry này."""
    _run_with_retry(_tts_edge_once, text, out_path, "edge-tts")


def _generate_audio_for_one_scene(scene: Scene, audio_dir: str) -> str | None:
    """Tạo audio cho ĐÚNG 1 cảnh (đã tự động thử lại TTS_MAX_RETRIES lần bên
    trong _tts_elevenlabs/_tts_openai/_tts_edge). Trả về None nếu thành công
    (đã gán scene.audio_path/scene.duration), hoặc trả về CHUỖI THÔNG BÁO LỖI
    nếu vẫn lỗi sau khi đã thử hết số lần -- không raise ra ngoài, để caller
    (generate_audio_for_scenes) tự quyết định có quét lại lượt sau hay không."""
    out_path = os.path.join(audio_dir, f"scene_{scene.index:03d}.mp3")
    try:
        if config.TTS_PROVIDER == "elevenlabs":
            _tts_elevenlabs(scene.narration, out_path)
        elif config.TTS_PROVIDER == "openai":
            _tts_openai(scene.narration, out_path)
        elif config.TTS_PROVIDER == "edge":
            _tts_edge(scene.narration, out_path)
        else:
            raise ValueError(f"TTS_PROVIDER không hợp lệ: {config.TTS_PROVIDER}")
    except Exception as e:
        return str(e)

    scene.audio_path = out_path
    info = mediainfo(out_path)
    scene.duration = float(info.get("duration", 0.0))
    return None


def generate_audio_for_scenes(scenes: list[Scene], work_dir: str) -> None:
    """Sinh audio cho từng scene, cập nhật scene.audio_path và scene.duration.
    Nếu config.TTS_ENABLED=False -> dùng audio có sẵn (xem _sync_local_audio_for_scenes),
    không gọi API TTS thật. Sau khi có audio (cả 2 nhánh), chèn khoảng lặng thật
    (config.SCENE_AUDIO_GAP) vào cuối audio mỗi cảnh (trừ cảnh cuối) để tránh
    2 câu thoại liền cảnh bị dính sát nhau -- xem _apply_scene_gaps().

    QUAN TRỌNG -- 2 lớp tự động phục hồi khi lỗi, KHÔNG dừng hỏi người dùng:
    1. Trong 1 cảnh: mỗi lần gọi TTS đã tự động thử lại TTS_MAX_RETRIES lần
       (xem _run_with_retry) trước khi coi là lỗi thật.
    2. Toàn bộ danh sách cảnh: nếu sau lượt chạy đầu vẫn còn cảnh lỗi, tự
       động QUAY LẠI chạy riêng CHỈ những cảnh đó thêm 1 lượt (pass) nữa,
       lặp lại tối đa TTS_MAX_PASSES lượt -- không hỏi lại, không dừng giữa
       chừng. Cảnh đã có audio (thành công) ở lượt trước không bị tạo lại.
       Chỉ khi hết TTS_MAX_PASSES lượt mà vẫn còn cảnh lỗi, pipeline mới thật
       sự dừng (raise), kèm báo cáo đầy đủ cảnh nào lỗi + lý do, vì các bước
       sau (subtitle/video_compose) cần audio đầy đủ 100% mới chạy được."""
    if not config.TTS_ENABLED:
        _sync_local_audio_for_scenes(scenes, work_dir)
        _apply_scene_gaps(scenes)
        return

    audio_dir = os.path.join(work_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)

    total = len(scenes)
    pending = list(scenes)  # danh sách cảnh CHƯA có audio, quét dần qua các lượt
    last_errors: dict[int, str] = {}  # scene.index -> thông báo lỗi mới nhất

    for pass_num in range(1, TTS_MAX_PASSES + 1):
        if not pending:
            break

        if pass_num > 1:
            print(f"\n  [TTS] === LƯỢT {pass_num}/{TTS_MAX_PASSES}: quay lại tạo nốt "
                  f"{len(pending)} cảnh bị lỗi ở lượt trước ===")

        still_failed: list[Scene] = []
        for i, scene in enumerate(pending, start=1):
            done_so_far = total - len(pending) + i - 1
            _print_tts_progress(
                done_so_far + 1,
                total,
                scene.index,
                "đang tạo audio",
                provider=config.TTS_PROVIDER,
            )

            error = _generate_audio_for_one_scene(scene, audio_dir)
            if error is not None:
                _print_tts_progress(
                    done_so_far + 1,
                    total,
                    scene.index,
                    "lỗi",
                    provider=config.TTS_PROVIDER,
                )
                is_last_pass = pass_num == TTS_MAX_PASSES
                if is_last_pass:
                    print(f"  [TTS] LỖI Cảnh {scene.index} (hết {TTS_MAX_PASSES} lượt): {error}")
                else:
                    print(f"  [TTS] Cảnh {scene.index}: chưa tạo được, sẽ tự động thử lại ở lượt sau.")
                last_errors[scene.index] = error
                still_failed.append(scene)
                continue

            last_errors.pop(scene.index, None)
            _print_tts_progress(
                done_so_far + 1,
                total,
                scene.index,
                "xong",
                provider=config.TTS_PROVIDER,
                duration=scene.duration,
            )
        sys.stdout.write("\r")

        pending = still_failed

    if pending:
        print(f"\n  [TTS] TỔNG KẾT: {len(pending)}/{total} cảnh vẫn lỗi TTS sau {TTS_MAX_PASSES} "
              f"lượt tự động quay lại (mỗi lượt đã thử lại {TTS_MAX_RETRIES} lần/cảnh):")
        for scene in pending:
            print(f"    - Cảnh {scene.index}: {last_errors.get(scene.index, '(không rõ lỗi)')}")
        raise RuntimeError(
            f"Dừng pipeline: {len(pending)}/{total} cảnh không tạo được audio sau {TTS_MAX_PASSES} "
            f"lượt tự động thử lại. Xem chi tiết lỗi từng cảnh ở log phía trên."
        )

    _apply_scene_gaps(scenes)

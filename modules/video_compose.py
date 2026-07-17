"""
Module 5/7: VIDEO COMPOSE (bản ffmpeg theo BATCH, GPU NVENC)
Ghép ẢNH TĨNH (hiệu ứng Ken Burns) HOẶC VIDEO DỰNG SẴN (scene.video_path,
xem modules/script_parser.py field VIDEO:) thành video hoàn chỉnh.

KIẾN TRÚC 2 TẦNG [cập nhật 2026-07-15, xem _BATCH_SIZE]:
  - TẦNG 1 (trong 1 batch, tối đa config.VIDEO_COMPOSE_BATCH_SIZE cảnh, mặc
    định 25): pipeline (crop/zoom hoặc scale video + hoà tan/cắt cảnh + nối
    audio + burn phụ đề + encode) chạy trong ĐÚNG 1 LỆNH FFMPEG DUY NHẤT/batch
    (dùng "-filter_complex_script" đọc filter graph từ file thay vì truyền
    thẳng trên dòng lệnh, xem _run_ffmpeg_with_filter_script) -> 1 lần encode
    duy nhất/batch, không có frame nào đi qua Python.
  - TẦNG 2 (giữa các batch): mỗi batch render ra 1 file .mp4 riêng trong
    work_dir, sau đó NỐI LẠI bằng concat DEMUXER (stream copy, "-c copy",
    KHÔNG re-encode lần 2, không mất chất lượng) thành video cuối cùng -- xem
    _concat_batches(). Kịch bản ngắn (không vượt quá 1 batch) thì chỉ có đúng
    1 file, không cần bước nối này.
  LÝ DO CHIA BATCH: kịch bản dài (vd 100-150+ cảnh) đưa TOÀN BỘ input (2/cảnh:
  ảnh/video + audio) vào 1 lệnh ffmpeg duy nhất có thể vượt giới hạn độ dài
  dòng lệnh của Windows (lỗi "WinError 206: filename or extension is too
  long" khi gọi CreateProcess) -- xem ghi chú đầy đủ tại _BATCH_SIZE.
  ĐÁNH ĐỔI: bên trong mỗi batch, crossfade giữa các cảnh vẫn hoà tan mượt như
  trước; ở RANH GIỚI GIỮA 2 BATCH là CẮT CỨNG (không hoà tan hình). Vì mỗi
  batch bắt đầu lại từ t=0 cục bộ, phụ đề cũng được cắt/dịch mốc riêng cho
  từng batch -- xem _slice_srt_for_batch().

KIẾN TRÚC:
  1. _prepare_padded_image(): NHƯ CŨ (PIL), resize kiểu "cover" + phóng to thêm
     zoom_ratio -> lưu ra 1 PNG trung gian. Chạy 1 lần/ảnh, không phải bottleneck.
  2. _crop_filter_for_effect(): build filter "crop=...,scale=...,format=yuv420p"
     với công thức w(t)/h(t)/x(t)/y(t) tương đương make_frame(t) của bản
     Python cũ (progress = t/duration). CHỈ áp dụng cho cảnh dùng ẢNH.
  3. _video_cover_filter(): filter "scale=...,crop=...,tpad=...,format=yuv420p"
     kiểu "cover" cho cảnh dùng VIDEO dựng sẵn (scene.video_path) -- KHÔNG áp
     dụng Ken Burns (video đã tự có chuyển động), chỉ chuẩn hoá kích thước/tỉ
     lệ khung hình. Video KHÔNG loop (chỉ phát ĐÚNG 1 LẦN từ đầu, xem
     config.SCENE_VIDEO_DURATION, mặc định 8 giây -- đúng bằng độ dài chuẩn
     mà bạn tự dựng cho mỗi video): nếu ngắn hơn thời lượng cần, filter "tpad"
     (stop_mode=clone) giữ nguyên (đứng yên) frame cuối cho đủ độ dài thay vì
     lặp lại từ đầu; nếu dài hơn, bị cắt bớt bằng "-t". compose_video() in
     cảnh báo (không chặn pipeline) nếu scene.duration (đo từ audio TTS thật)
     lệch quá config.SCENE_VIDEO_DURATION_WARN_THRESHOLD giây so với
     config.SCENE_VIDEO_DURATION, để biết mà chỉnh lại narration cho khớp
     ~8 giây.
  4. compose_video() dựng 1 filter_complex DUY NHẤT gồm:
     - N nhánh video: mỗi cảnh 1 input (ảnh loop hoặc video loop) -> crop/scale
       -> label [v{i}]
     - Nối video: "xfade" (chế độ crossfade, mặc định) hoặc "concat" kèm
       fade/afade 2 đầu (chế độ fade_black) -> [vcat]
     - Burn phụ đề lên [vcat] bằng filter "subtitles" (libass) -> [vout]
     - N nhánh audio: mỗi cảnh 1 nhánh TTS narration (nguồn giọng đọc CHÍNH,
       luôn quyết định thời lượng/timing) -> chuẩn hoá format (tránh lỗi nếu
       các file audio khác sample rate, hay gặp khi TTS_ENABLED=false và audio
       test do người dùng tự chuẩn bị). Nếu cảnh dùng VIDEO: VÀ video đó có
       audio track VÀ config.VIDEO_ORIGINAL_AUDIO_VOLUME > 0, TRỘN (amix) thêm
       audio gốc của video (đã giảm âm lượng theo config) vào cùng nhánh này
       trước khi afade -- xem _has_audio_stream(). Không còn tắt tiếng hoàn
       toàn video gốc như bản trước, chỉ hạ nhỏ để không lấn át lời TTS.
     - afade nhẹ chống tiếng "click" -> "concat" nối tuần tự KHÔNG chồng -> [aout]
     - NHẠC NỀN (tuỳ chọn, xem scene.music_path/modules/music_engine.py): build
       1 track ĐỘC LẬP dài bằng tổng scene.duration. QUAN TRỌNG: từ khi bỏ cơ
       chế Freesound, mọi scene dùng CHUNG 1 music_path cố định (config.
       BACKGROUND_MUSIC_PATH) -> "_group_scenes_by_music" gộp toàn bộ video
       thành ĐÚNG 1 cụm duy nhất, nên track nhạc thực chất là 1 file LOOP (nếu
       ngắn hơn) hoặc CẮT BỚT (nếu dài hơn) xuyên suốt toàn video, fade nhẹ 2
       đầu -> hạ volume theo config.MUSIC_VOLUME -> "amix" với [aout]
       (narration) thành [aout_final]. Cơ chế nhóm-theo-cụm vẫn được giữ
       nguyên trong code (không xoá) vì nó hoạt động đúng với cả trường hợp
       đặc biệt này, chỉ là số cụm giờ luôn = 1. KHÔNG đụng tới logic
       narration/xfade ở trên -- track nhạc hoàn toàn tách biệt, chỉ trộn vào
       ở bước cuối cùng. Nhạc nền tắt/không có file -> mọi scene.music_path
       rỗng -> bỏ qua toàn bộ bước này, giữ nguyên hành vi cũ ([aout] dùng thẳng).
     - Encode 1 lần: "-map [vout] -map [aout_final hoặc aout]" -> NVENC (hoặc libx264 CPU)

BẤT BIẾN QUAN TRỌNG (giữ nguyên từ các bản trước, xem PROJECT_MEMORY.md mục 4):
  - Chế độ crossfade: mỗi cảnh có pre_roll/post_roll (đóng băng, mỗi bên
    transition/2) làm vùng overlap cho "xfade". Vì "xfade" ăn mất đúng
    `transition` giây ở mỗi mối nối, và pre/post_roll đã cộng thêm đúng bằng
    phần đó, TỔNG THỜI LƯỢNG VIDEO CUỐI = TỔNG scene.duration = TỔNG AUDIO,
    không bị lệch/co ngắn theo số lần chuyển cảnh. Với cảnh dùng video dựng
    sẵn, pre_roll/post_roll vẫn hoạt động đúng vì video cũng được pad (tpad,
    KHÔNG loop) tới đúng total_duration (pre_roll + scene.duration + post_roll)
    y hệt cách ảnh được "-loop 1" tới đúng độ dài đó.
  - Audio TTS luôn nối tuần tự, KHÔNG chồng giọng đọc (khác hẳn hoà tan hình
    ảnh). Audio gốc của video (nếu trộn vào) chỉ cộng thêm vào ĐÚNG cửa sổ
    thời gian tương ứng với scene.duration của cảnh đó (dùng atrim theo
    pre_roll để cắt đúng đoạn "core", loại bỏ phần pre/post_roll đóng băng),
    không làm lệch timeline tổng thể.

YÊU CẦU MÔI TRƯỜNG: ffmpeg có h264_nvenc (GPU NVIDIA) + libass (đọc .srt) +
fontconfig (chọn font hệ thống cho phụ đề) + ffprobe (kiểm tra audio track
của video dựng sẵn). Không có GPU NVIDIA -> đặt config.VIDEO_ENCODER="libx264"
để dùng CPU.
"""
import os
import subprocess
import sys
import datetime

import srt
from PIL import Image

import config
from modules.cli_progress import write_progress
from modules.script_parser import Scene
from modules.effect_selector import select_effects_for_scenes

# QUAN TRỌNG [2026-07-15]: pipeline giờ CHIA NHỎ kịch bản dài thành nhiều
# "batch" (mỗi batch tối đa _BATCH_SIZE cảnh), render riêng từng batch ra 1
# file .mp4 tạm bằng đúng cơ chế 1-lệnh-ffmpeg/batch như trước, rồi NỐI các
# batch bằng concat DEMUXER (stream copy, KHÔNG re-encode lần 2) thành video
# cuối cùng. Lý do: với kịch bản ~100-150 cảnh, 1 lệnh ffmpeg DUY NHẤT cho
# TOÀN BỘ video (bản trước đây) có quá nhiều "-i <path>" (2 input/cảnh: 1
# ảnh/video + 1 audio, cộng thêm input nhạc nền nếu có) khiến độ dài dòng
# lệnh vượt giới hạn CreateProcess của Windows (~32KB, nhưng thực tế lỗi
# "WinError 206: filename or extension is too long" đã xuất hiện sớm hơn
# nhiều tuỳ cách Windows đo) -- KHÔNG PHẢI chỉ giới hạn 8191 ký tự của
# cmd.exe (giới hạn đó chỉ áp dụng khi gõ trực tiếp trong cmd.exe, còn
# subprocess.run gọi CreateProcess trực tiếp, không qua cmd.exe, nhưng vẫn
# có giới hạn riêng của WinAPI).
#
# Batch size 25 được chọn làm mặc định an toàn: mỗi cảnh cần ~2 input +
# hàng chục dòng filter_complex, 25 cảnh/batch giữ độ dài lệnh trong khoảng
# vài nghìn ký tự, an toàn trên mọi phiên bản Windows. Có thể chỉnh qua
# config.VIDEO_COMPOSE_BATCH_SIZE nếu cần.
#
# HỆ QUẢ VỀ CHẤT LƯỢNG: bên trong mỗi batch, crossfade (xfade) giữa các cảnh
# vẫn hoà tan mượt như cũ. Ở RANH GIỚI GIỮA 2 BATCH (cứ mỗi _BATCH_SIZE cảnh),
# 2 file .mp4 được nối bằng concat demuxer (cắt cứng, không hoà tan hình) --
# đây là đánh đổi bắt buộc để tránh vượt giới hạn dòng lệnh. Số điểm cắt cứng
# này rất nhỏ so với tổng số cảnh (vd 145 cảnh / batch 25 = chỉ 5 điểm cắt
# cứng), và audio TTS vẫn nối liền mạch tuyệt đối vì concat demuxer không đụng
# tới nội dung từng batch, chỉ nối các file .mp4 đã render sẵn lại với nhau.
_BATCH_SIZE = getattr(config, "VIDEO_COMPOSE_BATCH_SIZE", 25)


# ============================================================
# TIỆN ÍCH GỌI FFMPEG
# ============================================================

def _run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg lỗi khi chạy lệnh (độ dài lệnh: {len(' '.join(cmd))} ký tự):\n"
            f"  {' '.join(cmd)}\n\n--- stderr (cuối) ---\n{result.stderr[-4000:]}"
        )


def _run_ffmpeg_with_filter_script(cmd_prefix: list[str], filter_complex: str,
                                    cmd_suffix: list[str], work_dir: str, tag: str) -> None:
    """Giống _run_ffmpeg, nhưng ghi filter_complex ra 1 file .txt trong
    work_dir và truyền qua '-filter_complex_script <path>' thay vì
    '-filter_complex <chuỗi>' trực tiếp trên dòng lệnh. filter_complex của
    mỗi batch có thể dài hàng chục nghìn ký tự (nhiều cảnh x nhiều filter/cảnh)
    -- đưa hẳn ra file giúp dòng lệnh thực tế truyền cho CreateProcess ngắn đi
    đáng kể, chỉ còn phụ thuộc số lượng '-i <path>' (đã được giới hạn bởi
    _BATCH_SIZE)."""
    script_path = os.path.join(work_dir, f"filter_complex_{tag}.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(filter_complex)

    cmd = cmd_prefix + ["-filter_complex_script", script_path] + cmd_suffix
    _run_ffmpeg(cmd)


def _print_compose_progress(done: int, total: int, label: str) -> None:
    write_progress("COMPOSE", done, total, label)


def _video_encode_args() -> list[str]:
    """Tham số encode video dùng chung, tuỳ config.VIDEO_ENCODER."""
    if config.VIDEO_ENCODER == "h264_nvenc":
        return [
            "-c:v", "h264_nvenc",
            "-preset", config.VIDEO_NVENC_PRESET,
            "-rc", "vbr",
            "-cq", str(config.VIDEO_CQ),
            "-b:v", "0",  # bỏ giới hạn bitrate cứng, để -cq quyết định chất lượng
        ]
    return ["-c:v", "libx264", "-preset", config.VIDEO_PRESET, "-crf", str(config.VIDEO_CRF)]


def _has_audio_stream(video_path: str) -> bool:
    """Kiểm tra file video dựng sẵn có audio track hay không (dùng ffprobe).
    Lỗi ffprobe (thiếu binary, file hỏng...) coi như KHÔNG có audio, để
    pipeline không dừng giữa chừng vì lỗi kiểm tra phụ này."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=index", "-of", "csv=p=0", video_path],
            capture_output=True, text=True,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


# ============================================================
# CHUẨN BỊ ẢNH "PADDED" (cover-crop + phóng to dự phòng) -- 1 lần/ảnh
# ============================================================

def _prepare_padded_image(image_path: str, target_w: int, target_h: int, zoom_ratio: float,
                           out_path: str) -> tuple[int, int]:
    img = Image.open(image_path).convert("RGB")
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        base_h = target_h
        base_w = int(round(base_h * img_ratio))
    else:
        base_w = target_w
        base_h = int(round(base_w / img_ratio))
    img = img.resize((base_w, base_h), Image.LANCZOS)

    left = (base_w - target_w) / 2
    top = (base_h - target_h) / 2
    img = img.crop((left, top, left + target_w, top + target_h))

    padded_w = max(target_w + 2, int(round(target_w * zoom_ratio)))
    padded_h = max(target_h + 2, int(round(target_h * zoom_ratio)))
    img = img.resize((padded_w, padded_h), Image.LANCZOS)
    img.save(out_path)

    return padded_w, padded_h


# ============================================================
# KEN BURNS: build filter ffmpeg crop+scale (CHỈ cho cảnh dùng ẢNH)
# ============================================================

def _crop_filter_for_effect(effect: str, padded_w: int, padded_h: int, target_w: int, target_h: int,
                             pre_roll: float, core_duration: float) -> str:
    """Trả về filter 'crop=...,scale=...,format=yuv420p'. 'format=yuv420p' ở
    cuối đảm bảo MỌI cảnh ra cùng 1 pixel format trước khi đưa vào xfade/concat
    -- thiếu bước này dễ gây lỗi "Input link parameters do not match" của
    ffmpeg khi các ảnh nguồn có mode màu khác nhau.

    Hỗ trợ ĐỦ 21 hiệu ứng khai báo trong effect_selector.AVAILABLE_EFFECTS
    (xem nhật ký PROJECT_MEMORY.md [2026-07-13] "Bổ sung 14 hiệu ứng Ken Burns
    còn thiếu"): 7 cơ bản (công thức GIỮ NGUYÊN 100% như bản cũ, không đổi
    hành vi) + 8 kết hợp zoom+pan chéo + 4 pan chéo góc + 2 hiệu ứng "breathe"
    (zoom vào rồi ra, hoặc ngược lại, trong cùng 1 cảnh)."""
    d = max(core_duration, 0.001)
    t_core = f"min(max(t-{pre_roll},0),{d})"
    p = f"(({t_core})/{d})"
    # Tiến trình dạng tam giác (0 -> 1 -> 0) dùng cho 2 hiệu ứng "breathe".
    tri_p = f"(1-abs(2*{p}-1))"
    max_dx = padded_w - target_w
    max_dy = padded_h - target_h

    def _zoom_in_wh(prog: str) -> tuple[str, str]:
        w = f"({padded_w}-({padded_w}-{target_w})*{prog})"
        h = f"({padded_h}-({padded_h}-{target_h})*{prog})"
        return w, h

    def _zoom_out_wh(prog: str) -> tuple[str, str]:
        w = f"({target_w}+({padded_w}-{target_w})*{prog})"
        h = f"({target_h}+({padded_h}-{target_h})*{prog})"
        return w, h

    def _centered_xy(w: str, h: str) -> tuple[str, str]:
        x = f"({padded_w}-({w}))/2"
        y = f"({padded_h}-({h}))/2"
        return x, y

    if effect == "zoom_in":
        w, h = _zoom_in_wh(p)
        x, y = _centered_xy(w, h)
    elif effect == "zoom_out":
        w, h = _zoom_out_wh(p)
        x, y = _centered_xy(w, h)
    elif effect == "pan_left":
        w, h = str(target_w), str(target_h)
        x = f"({max_dx})*(1-{p})"
        y = f"({max_dy})/2"
    elif effect == "pan_right":
        w, h = str(target_w), str(target_h)
        x = f"({max_dx})*{p}"
        y = f"({max_dy})/2"
    elif effect == "pan_up":
        w, h = str(target_w), str(target_h)
        x = f"({max_dx})/2"
        y = f"({max_dy})*(1-{p})"
    elif effect == "pan_down":
        w, h = str(target_w), str(target_h)
        x = f"({max_dx})/2"
        y = f"({max_dy})*{p}"

    # --- 2 hiệu ứng "breathe": zoom vào-rồi-ra hoặc ra-rồi-vào, dùng lại
    # đúng công thức w/h của zoom_in/zoom_out ở trên, chỉ thay tiến trình p
    # tuyến tính bằng tri_p (tam giác 0->1->0). ---
    elif effect == "zoom_in_out":
        w, h = _zoom_in_wh(tri_p)
        x, y = _centered_xy(w, h)
    elif effect == "zoom_out_in":
        w, h = _zoom_out_wh(tri_p)
        x, y = _centered_xy(w, h)

    # --- 4 hiệu ứng pan chéo góc-tới-góc, kích thước khung giữ nguyên target
    # (không zoom), chỉ di chuyển vị trí crop theo đường chéo. ---
    elif effect == "pan_diagonal_tl_br":  # góc trên-trái -> dưới-phải
        w, h = str(target_w), str(target_h)
        x = f"({max_dx})*{p}"
        y = f"({max_dy})*{p}"
    elif effect == "pan_diagonal_tr_bl":  # góc trên-phải -> dưới-trái
        w, h = str(target_w), str(target_h)
        x = f"({max_dx})*(1-{p})"
        y = f"({max_dy})*{p}"
    elif effect == "pan_diagonal_bl_tr":  # góc dưới-trái -> trên-phải
        w, h = str(target_w), str(target_h)
        x = f"({max_dx})*{p}"
        y = f"({max_dy})*(1-{p})"
    elif effect == "pan_diagonal_br_tl":  # góc dưới-phải -> trên-trái
        w, h = str(target_w), str(target_h)
        x = f"({max_dx})*(1-{p})"
        y = f"({max_dy})*(1-{p})"

    # --- 8 hiệu ứng kết hợp zoom (in/out) + pan chéo (left/right/up/down):
    # dùng công thức w/h của zoom_in hoặc zoom_out, nhưng x/y pan theo hướng
    # chỉ định dựa trên khoảng trống ĐỘNG còn lại tại thời điểm t (padded -
    # w(t)/h(t)), vì w/h thay đổi liên tục trong lúc zoom. ---
    elif effect in (
        "zoom_in_pan_left", "zoom_in_pan_right", "zoom_in_pan_up", "zoom_in_pan_down",
        "zoom_out_pan_left", "zoom_out_pan_right", "zoom_out_pan_up", "zoom_out_pan_down",
    ):
        direction = effect.rsplit("_", 1)[-1]  # left/right/up/down
        if effect.startswith("zoom_in_pan_"):
            w, h = _zoom_in_wh(p)
        else:
            w, h = _zoom_out_wh(p)
        if direction == "left":
            x = f"({padded_w}-({w}))*(1-{p})"
            y = f"({padded_h}-({h}))/2"
        elif direction == "right":
            x = f"({padded_w}-({w}))*{p}"
            y = f"({padded_h}-({h}))/2"
        elif direction == "up":
            x = f"({padded_w}-({w}))/2"
            y = f"({padded_h}-({h}))*(1-{p})"
        else:  # "down"
            x = f"({padded_w}-({w}))/2"
            y = f"({padded_h}-({h}))*{p}"
    else:
        # "static" hoặc hiệu ứng không xác định -> khung hình chính giữa, đứng yên
        w, h = str(target_w), str(target_h)
        x = f"({max_dx})/2"
        y = f"({max_dy})/2"

    return f"crop=w='{w}':h='{h}':x='{x}':y='{y}',scale={target_w}:{target_h}:flags=lanczos,format=yuv420p"


# ============================================================
# VIDEO DỰNG SẴN: filter scale+crop kiểu "cover" (CHỈ cho cảnh dùng VIDEO:)
# ============================================================

def _video_cover_filter(target_w: int, target_h: int, fps: int,
                        start_pad: float, stop_pad: float) -> str:
    """Trả về filter chuẩn hoá 1 video input bất kỳ về đúng target_w x target_h.

    start_pad: độ dài freeze frame đầu cảnh (pre-roll) khi cần xfade từ cảnh
    trước sang cảnh này.
    stop_pad: độ dài freeze frame cuối cảnh (post-roll) + phần kéo dài nếu
    audio narration dài hơn video.
    """
    return (
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},fps={fps},"
        f"tpad=start_mode=clone:start_duration={start_pad:.6f}:"
        f"stop_mode=clone:stop_duration={stop_pad:.6f},format=yuv420p"
    )


def _subtitles_filter(srt_path: str) -> str:
    """Filter 'subtitles=' dùng libass. Escape dấu ':' (ổ đĩa Windows) theo
    đúng yêu cầu cú pháp filter của ffmpeg."""
    escaped = srt_path.replace("\\", "/").replace(":", "\\:")
    style = "FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=30"
    return f"subtitles='{escaped}':force_style='{style}'"


def _scene_needs_original_audio_mix(scene: Scene) -> bool:
    """Cảnh cần trộn thêm audio gốc của video dựng sẵn khi: có video_path,
    config cho phép (volume > 0), VÀ video đó thực sự có audio track."""
    return bool(
        scene.video_path
        and config.VIDEO_ORIGINAL_AUDIO_VOLUME > 0
        and _has_audio_stream(scene.video_path)
    )


# ============================================================
# NHẠC NỀN: nhóm cảnh liên tiếp cùng music_path thành từng "cụm", build track
# nhạc nền độc lập dài bằng tổng thời lượng video, rồi amix với track TTS.
# Từ khi bỏ Freesound, mọi scene dùng chung 1 music_path cố định nên luôn chỉ
# có ĐÚNG 1 cụm -- hàm này vẫn tổng quát, không cần sửa gì thêm.
# ============================================================

def _group_scenes_by_music(scenes: list[Scene]) -> list[tuple[str, float]]:
    """Gộp các cảnh liên tiếp có CÙNG music_path thành từng cụm (music_path,
    tổng scene.duration của cụm đó). music_path rỗng = cụm không có nhạc nền
    (khoảng lặng). Dùng scene.duration THUẦN (không cộng pre/post_roll) vì
    track nhạc nền là track ĐỘC LẬP, không cần đồng bộ crossfade hình ảnh."""
    groups: list[tuple[str, float]] = []
    for scene in scenes:
        if groups and groups[-1][0] == scene.music_path:
            path, dur = groups[-1]
            groups[-1] = (path, dur + scene.duration)
        else:
            groups.append((scene.music_path, scene.duration))
    return groups


def _has_any_music(scenes: list[Scene]) -> bool:
    return any(s.music_path for s in scenes)


def _build_music_track(scenes: list[Scene], input_offset: int) -> tuple[list[str], list[str], str]:
    """Trả về (inputs ffmpeg, filter_parts, label) cho track nhạc nền hoàn
    chỉnh, dài đúng bằng tổng scene.duration. Mỗi cụm cảnh cùng music_path
    được loop (nếu ngắn hơn cụm) + cắt đúng độ dài, fade nhẹ 2 đầu cụm để
    tránh giật khi đổi/tắt nhạc; cụm không có nhạc dùng anullsrc (im lặng).
    Nối tất cả cụm bằng concat -> áp volume MUSIC_VOLUME -> label cuối."""
    groups = _group_scenes_by_music(scenes)
    inputs: list[str] = []
    filter_parts: list[str] = []
    labels: list[str] = []
    music_fade = 0.5  # fade nhẹ ở đầu/cuối mỗi cụm nhạc, tránh cắt cụt đột ngột

    for gi, (music_path, dur) in enumerate(groups):
        lbl = f"music{gi}"
        if music_path:
            idx = input_offset + gi
            inputs += ["-stream_loop", "-1", "-t", f"{dur:.6f}", "-i", music_path]
            fade_out_start = max(dur - music_fade, 0.0)
            filter_parts.append(
                f"[{idx}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
                f"afade=t=in:d={music_fade:.6f},afade=t=out:st={fade_out_start:.6f}:d={music_fade:.6f}[{lbl}]"
            )
        else:
            filter_parts.append(
                f"anullsrc=channel_layout=stereo:sample_rate=44100,atrim=duration={dur:.6f}[{lbl}]"
            )
        labels.append(f"[{lbl}]")

    if len(groups) > 1:
        filter_parts.append("".join(labels) + f"concat=n={len(groups)}:v=0:a=1[music_cat]")
        cat_label = "music_cat"
    else:
        cat_label = "music0"

    out_label = "music_out"
    filter_parts.append(f"[{cat_label}]volume={config.MUSIC_VOLUME:.3f}[{out_label}]")

    return inputs, filter_parts, out_label


# ============================================================
# CHUẨN BỊ ẢNH PADDED CHO TOÀN BỘ CẢNH (CHỈ cảnh dùng ẢNH, video bỏ qua)
# ============================================================

def _prepare_all_padded_images(scenes: list[Scene], target_w: int, target_h: int, zoom_ratio: float,
                                work_dir: str) -> dict[int, tuple[str, int, int]]:
    """Trả về dict {scene.index: (padded_path, padded_w, padded_h)}, CHỈ chứa
    entry cho các cảnh KHÔNG có video_path (cảnh dùng video_path không cần
    ảnh padded, xử lý riêng bằng _video_cover_filter)."""
    result = {}
    for scene in scenes:
        if scene.video_path:
            continue
        padded_path = os.path.join(work_dir, f"padded_{scene.index:03d}.png")
        pw, ph = _prepare_padded_image(scene.image_path, target_w, target_h, zoom_ratio, padded_path)
        result[scene.index] = (padded_path, pw, ph)
    return result


# ============================================================
# SOẠN 1 CẢNH RIÊNG LẺ: xử lý duration mismatch CHO VIDEO DỰNG SẴN
# ============================================================

def _compose_single_scene(scene: Scene, scene_index: int, padded_info: dict[int, tuple[str, int, int]], 
                          srt_path: str, target_w: int, target_h: int, fps: int, out_path: str,
                          work_dir: str, pre_roll: float = 0.0, post_roll: float = 0.0) -> None:
    """Soạn 1 cảnh duy nhất thành file video.

    Mỗi cảnh gồm video/image + audio + phụ đề, dựng riêng từng scene trước khi gộp.

    QUAN TRỌNG [sửa lỗi crossfade cắt cứng + lệch audio/video, xem
    _compose_all_scenes_with_xfade]: pre_roll/post_roll giờ THỰC SỰ được dùng,
    không chỉ "chấp nhận cho tương thích" như trước:
    - VIDEO: freeze-frame thêm pre_roll giây ở đầu + post_roll giây ở cuối
      (giống hệt cơ chế pre_roll/post_roll trong _compose_crossfade gốc) ->
      output file dài total_duration = pre_roll + scene.duration + post_roll.
      Đây chính là "vùng dự phòng" để _compose_all_scenes_with_xfade dùng cho
      xfade, KHÔNG ăn vào nội dung thật của cảnh.
    - AUDIO: track audio trong file này ĐƯỢC PAD THÊM khoảng lặng đúng bằng
      pre_roll/post_roll (adelay phía trước + apad phía sau) để khớp ĐÚNG
      total_duration với video track trong cùng file -- nếu không mux 2 track
      lệch độ dài trong 1 file MP4 sẽ gây lỗi/hành vi không xác định. Phần
      audio "core" (đúng scene.duration, đúng lời thoại) vẫn nằm nguyên vẹn ở
      giữa, dùng atrim ở bước concat để lấy lại đúng phần đó -- xem
      _compose_all_scenes_with_xfade.
    """
    
    inputs = []
    filter_parts = []
    
    # Input video/ảnh
    if scene.video_path:
        # Probe video duration từ file
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
             "-of", "default=noprint_wrappers=1:nokey=1", scene.video_path],
            capture_output=True, text=True
        )
        video_duration = float(result.stdout.strip()) if result.stdout.strip() else config.SCENE_VIDEO_DURATION

        # QUAN TRỌNG [sửa lỗi nghiêm trọng: video dừng sớm, audio vẫn chạy tiếp]:
        # KHÔNG được đặt "-r {fps}" TRƯỚC "-i" ở đây. "-r" trước "-i" là INPUT
        # framerate override -- nó buộc ffmpeg diễn giải lại timestamp gốc của
        # file theo framerate ép buộc, KHÔNG phải resample thật. Với video AI-gen
        # (Runway/Pika/Kling/Sora/Luma...) thường xuất 24fps (khác VIDEO_FPS=30
        # mặc định), ép "-r 30" ở input khiến ffmpeg tính lại timeline sai: cùng
        # số frame vật lý (vd 192 frame) nhưng bị chia cho 30 thay vì 24 fps thật
        # -> mất đúng (1 - 24/30) = 20% độ dài thật (video 8s thật chỉ còn đọc
        # được 6.4s). Hậu quả: file scene ngắn hơn hẳn total_duration mà
        # _compose_all_scenes_with_xfade dùng để tính offset xfade -> xfade sau
        # đó "cạn nguồn" giữa chừng, làm TOÀN BỘ chuỗi video từ điểm đó trở đi bị
        # cắt cụt (không báo lỗi gì), trong khi audio track (không phụ thuộc
        # video) vẫn phát đủ -> video dừng hẳn nhưng audio vẫn tiếp tục chạy.
        # Việc resample về đúng {fps} đã được filter "fps={fps}" bên trong vf
        # (_video_cover_filter / nhánh setpts dưới đây) đảm nhiệm ĐÚNG CÁCH --
        # filter đó chạy SAU khi decode, biết chính xác timestamp gốc của video,
        # nên không cần (và không được) ép framerate ngay ở input.
        if scene.duration <= video_duration:
            # Narration ngắn hơn hoặc bằng video -> cắt bớt video cho khớp.
            inputs += ["-t", f"{scene.duration:.6f}", "-i", scene.video_path]
            vf = _video_cover_filter(target_w, target_h, fps, pre_roll, post_roll)
        else:
            ratio = scene.duration / max(video_duration, 0.001)
            # Narration dài hơn video -> slow toàn bộ video để kéo dài theo tỷ lệ.
            inputs += ["-i", scene.video_path]
            vf = (
                f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
                f"crop={target_w}:{target_h},fps={fps},setpts=PTS*{ratio:.6f},"
                f"tpad=start_mode=clone:start_duration={pre_roll:.6f}:"
                f"stop_mode=clone:stop_duration={post_roll:.6f},format=yuv420p"
            )

        filter_parts.append(f"[0:v]{vf}[v{scene.index}]")
        audio_idx = 1
    else:
        # Ảnh -> Ken Burns
        padded_path, pw, ph = padded_info[scene.index]
        total_duration = scene.duration + pre_roll + post_roll
        inputs += ["-loop", "1", "-r", str(fps), "-t", f"{total_duration:.6f}", "-i", padded_path]
        motion_duration = scene.speech_duration if scene.speech_duration > 0 else scene.duration
        vf = _crop_filter_for_effect(scene.effect, pw, ph, target_w, target_h, pre_roll, motion_duration)
        filter_parts.append(f"[0:v]{vf}[v{scene.index}]")
        audio_idx = 1

    # Input audio (TTS narration)
    inputs += ["-i", scene.audio_path]

    # Burn subtitles
    filter_parts.append(f"[v{scene.index}]{_subtitles_filter(srt_path)}[vout]")

    # Audio: narration
    click_fade = 0.08
    fade_out_start = max(scene.duration - click_fade, 0.0)
    
    filter_parts.append(f"[{audio_idx}:a]aformat=sample_rates=44100:channel_layouts=stereo[narr0]")
    mix_src = "narr0"

    # Mix with original video audio if exists
    if _scene_needs_original_audio_mix(scene):
        filter_parts.append(
            f"[0:a]volume={config.VIDEO_ORIGINAL_AUDIO_VOLUME:.3f},"
            f"aformat=sample_rates=44100:channel_layouts=stereo[vorig0]"
        )
        filter_parts.append(f"[narr0][vorig0]amix=inputs=2:duration=first:normalize=0[mixed0]")
        mix_src = "mixed0"

    # Fade audio at start/end
    filter_parts.append(
        f"[{mix_src}]afade=t=in:d={click_fade:.6f},afade=t=out:st={fade_out_start:.6f}:d={click_fade:.6f}[aout]"
    )

    # QUAN TRỌNG [sửa lỗi nhạc nền bị lặp mỗi khi chuyển cảnh]: KHÔNG còn mix
    # nhạc nền ở đây. Trước đây mỗi scene tự cắt riêng 1 đoạn nhạc từ ĐẦU file
    # nhạc gốc (_build_music_track([scene], ...) -> "-stream_loop -1 -t
    # scene.duration") rồi nối các đoạn "luôn bắt đầu từ giây 0" đó lại với
    # nhau -- nghe như nhạc bị restart ở mỗi lần chuyển cảnh, DÙ file nhạc gốc
    # đã đủ dài cho cả video. Nhạc nền giờ được xử lý là 1 TRACK ĐỘC LẬP DUY
    # NHẤT cho toàn bộ video, mix vào SAU KHI mọi cảnh đã được ghép nối liền
    # -- xem _mix_background_music(), gọi từ compose_video().
    audio_out_label = "aout"

    # QUAN TRỌNG [sửa lỗi crossfade/lệch audio-video]: pad thêm khoảng lặng
    # đúng bằng pre_roll (đầu)/post_roll (cuối) vào track audio cuối cùng, để
    # khớp ĐÚNG total_duration với video track (đã dài thêm pre_roll+post_roll
    # nhờ tpad ở _video_cover_filter/_crop_filter_for_effect phía trên). Thiếu
    # bước này, audio track ngắn hơn video track trong CÙNG 1 file MP4 -> mux
    # lệch độ dài 2 track, ffmpeg tự lấp bằng silence không kiểm soát được vị
    # trí, hoặc bị cắt theo track ngắn nhất tuỳ encoder -- cả 2 đều làm hỏng
    # đồng bộ khi _compose_all_scenes_with_xfade dùng atrim lấy lại phần audio
    # "core" ở bước sau. adelay dùng mili-giây (KHÔNG phải giây) nên phải nhân 1000.
    if pre_roll > 0 or post_roll > 0:
        pre_ms = int(round(pre_roll * 1000))
        filter_parts.append(
            f"[{audio_out_label}]adelay=delays={pre_ms}:all=1,"
            f"apad=pad_dur={post_roll:.6f}[{audio_out_label}_padded]"
        )
        audio_out_label = f"{audio_out_label}_padded"

    filter_complex = ";".join(filter_parts)

    cmd_prefix = ["ffmpeg", "-y"] + inputs
    cmd_suffix = [
        "-map", "[vout]",
        "-map", f"[{audio_out_label}]",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
    ] + _video_encode_args() + ["-c:a", "aac", out_path]
    _run_ffmpeg_with_filter_script(cmd_prefix, filter_complex, cmd_suffix, work_dir, tag=f"scene_{scene.index:03d}")


# ============================================================
# NỐI TẤT CẢ CÁC CẢNH VỚI XFADE TRANSITIONS
# ============================================================

def _compose_all_scenes_with_xfade(scene_videos: list[str], scene_pads: list[tuple[float, float, float]],
                                    out_path: str, fps: int, transition: float, work_dir: str) -> None:
    """Nối tất cả các file video riêng lẻ (từ _compose_single_scene) với xfade transitions.

    scene_videos: list các đường dẫn video file của từng cảnh (đã được soạn riêng).
    scene_pads: list song song với scene_videos, mỗi phần tử là
        (pre_roll, scene_duration, post_roll) ĐÚNG như đã truyền cho
        _compose_single_scene khi dựng file đó -- dùng để biết chính xác
        total_duration của từng file (= pre_roll + scene_duration + post_roll,
        KHÔNG cần ffprobe lại/đoán) và để atrim audio đúng phần "core".

    QUAN TRỌNG [sửa lỗi crossfade cắt cứng/hình bị ăn mất + lệch audio-video]:
    - VIDEO: mỗi file scene giờ đã có freeze-frame pre_roll/post_roll (xem
      _compose_single_scene), nên "offset" của xfade phải tính trên
      total_duration (bao gồm pre/post_roll) của từng file -- xfade khi đó
      chỉ ăn vào đúng vùng freeze-frame dự phòng, KHÔNG ăn vào nội dung thật
      của cảnh (khác bản trước dùng thẳng duration probe được, vốn = scene.duration
      thật khi file có pre/post_roll -> tính offset sai, ăn lẹm nội dung).
    - AUDIO: track audio trong mỗi file đã được pad thêm silence đúng bằng
      pre_roll (đầu)/post_roll (cuối) -- xem _compose_single_scene. Ở đây
      dùng atrim(start=pre_roll, duration=scene_duration) để LOẠI BỎ phần
      silence đó, lấy lại đúng phần audio "core", rồi concat các phần core
      này lại -- audio kết quả nối liền KHÔNG chồng, KHÔNG có khoảng câm dư,
      và tổng thời lượng audio LUÔN khớp tổng scene_duration, độc lập với số
      lần xfade (bất biến này giống hệt bản gốc _compose_crossfade, xem
      PROJECT_MEMORY.md mục 4)."""
    n = len(scene_videos)

    if n == 1:
        # Chỉ 1 cảnh -> copy file không cần xfade
        import shutil
        shutil.copy2(scene_videos[0], out_path)
        return

    total_durations = [pre + dur + post for pre, dur, post in scene_pads]

    # Build filter chain: label inputs first, then xfade
    inputs = []
    filter_parts = []

    for video_path in scene_videos:
        inputs += ["-i", video_path]

    # Video: label inputs then xfade chain
    for i in range(n):
        filter_parts.append(f"[{i}:v]settb=1/30,fps={fps},format=yuv420p[v{i}]")

    # Xfade chain -- offset dựa trên total_duration (bao gồm pre/post_roll)
    label_prev = "v0"
    cumulative = total_durations[0]

    for i in range(1, n):
        label_out = f"vx{i}" if i < n - 1 else "vout"
        offset = max(cumulative - transition, 0.0)
        filter_parts.append(
            f"[{label_prev}][v{i}]xfade=transition=fade:duration={transition:.6f}:offset={offset:.6f}[{label_out}]"
        )
        cumulative = cumulative + total_durations[i] - transition
        label_prev = label_out

    # Audio: atrim lấy lại đúng phần "core" (bỏ silence pad ở pre/post_roll),
    # rồi concat tuần tự -- KHÔNG chồng, KHÔNG lệch so với tổng scene_duration.
    audio_labels = []
    for i, (pre_roll, scene_duration, _post_roll) in enumerate(scene_pads):
        lbl = f"acore{i}"
        filter_parts.append(
            f"[{i}:a]atrim=start={pre_roll:.6f}:duration={scene_duration:.6f},"
            f"asetpts=PTS-STARTPTS[{lbl}]"
        )
        audio_labels.append(f"[{lbl}]")

    filter_parts.append("".join(audio_labels) + f"concat=n={n}:v=0:a=1[aout]")

    filter_complex = ";".join(filter_parts)

    cmd_prefix = ["ffmpeg", "-y"] + inputs
    cmd_suffix = [
        "-map", "[vout]",
        "-map", "[aout]",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
    ] + _video_encode_args() + ["-c:a", "aac", out_path]
    _run_ffmpeg_with_filter_script(cmd_prefix, filter_complex, cmd_suffix, work_dir, tag="xfade")


# ============================================================
# CHẾ ĐỘ CROSSFADE (mặc định): 1 lệnh ffmpeg duy nhất
# ============================================================

def _compose_crossfade(scenes: list[Scene], padded_info: dict[int, tuple[str, int, int]], srt_path: str,
                        target_w: int, target_h: int, fps: int, transition: float, out_path: str,
                        work_dir: str, tag: str = "single") -> None:
    n = len(scenes)
    half = transition / 2.0

    inputs = []
    clip_durations = []
    for i, scene in enumerate(scenes):
        pre_roll = half if i > 0 else 0.0
        post_roll = half if i < n - 1 else 0.0
        total_duration = pre_roll + scene.duration + post_roll
        clip_durations.append(total_duration)
        if scene.video_path:
            # Video dựng sẵn: KHÔNG loop nữa (video chỉ phát ĐÚNG 1 LẦN từ
            # đầu, xem config.SCENE_VIDEO_DURATION). "-t" chỉ để phòng khi
            # video dài hơn total_duration (cắt bớt phần dư); nếu ngắn hơn,
            # filter 'tpad' ở _video_cover_filter tự giữ nguyên frame cuối
            # cho đủ độ dài (xem vòng lặp build filter phía dưới). Input này
            # giữ nguyên audio track gốc (nếu có) để nhánh audio phía dưới
            # có thể trộn vào.
            inputs += ["-r", str(fps), "-t", f"{total_duration:.6f}", "-i", scene.video_path]
        else:
            padded_path, _, _ = padded_info[scene.index]
            inputs += ["-loop", "1", "-r", str(fps), "-t", f"{total_duration:.6f}", "-i", padded_path]

    audio_offset = n
    for scene in scenes:
        inputs += ["-i", scene.audio_path]

    filter_parts = []

    # --- video: crop/zoom (ảnh) hoặc scale cover (video dựng sẵn) từng cảnh ---
    for i, scene in enumerate(scenes):
        pre_roll = half if i > 0 else 0.0
        if scene.video_path:
            vf = _video_cover_filter(target_w, target_h, fps, clip_durations[i])
        else:
            _, pw, ph = padded_info[scene.index]
            motion_duration = scene.speech_duration if scene.speech_duration > 0 else scene.duration
            vf = _crop_filter_for_effect(scene.effect, pw, ph, target_w, target_h, pre_roll, motion_duration)
        filter_parts.append(f"[{i}:v]{vf}[v{i}]")

    # --- nối video bằng xfade (hoà tan thật) ---
    label_prev = "v0"
    cumulative = clip_durations[0]
    for i in range(1, n):
        label_out = f"vx{i}" if i < n - 1 else "vcat"
        offset = cumulative - transition
        filter_parts.append(
            f"[{label_prev}][v{i}]xfade=transition=fade:duration={transition:.6f}:offset={offset:.6f}[{label_out}]"
        )
        cumulative = cumulative + clip_durations[i] - transition
        label_prev = label_out
    video_cat_label = label_prev  # "v0" nếu chỉ có 1 cảnh (không cần xfade)

    # --- burn phụ đề ---
    filter_parts.append(f"[{video_cat_label}]{_subtitles_filter(srt_path)}[vout]")

    # --- audio: TTS narration là nguồn CHÍNH, trộn thêm audio gốc video (nếu
    # có + được bật) rồi mới chuẩn hoá/nối tuần tự, không chồng giọng đọc. ---
    # click_fade tăng nhẹ (0.03 -> 0.08s) để việc bắt đầu/kết thúc mỗi audio
    # mượt hơn; khoảng lặng THẬT giữa 2 cảnh đến từ config.SCENE_AUDIO_GAP đã
    # được chèn vào cuối scene.audio_path ở bước TTS (xem tts_engine._apply_scene_gaps),
    # nên scene.duration ở đây đã bao gồm khoảng lặng đó -- không cần xử lý gì thêm ở đây.
    click_fade = 0.08
    audio_labels = []
    for i, scene in enumerate(scenes):
        idx = audio_offset + i
        pre_roll = half if i > 0 else 0.0
        fade_out_start = max(scene.duration - click_fade, 0.0)
        lbl = f"a{i}"

        filter_parts.append(f"[{idx}:a]aformat=sample_rates=44100:channel_layouts=stereo[narr{i}]")
        mix_src = f"narr{i}"

        if _scene_needs_original_audio_mix(scene):
            # atrim theo pre_roll để lấy đúng đoạn "core" (bỏ phần pre/post_roll
            # đóng băng chỉ dùng cho hình), khớp đúng scene.duration của TTS.
            filter_parts.append(
                f"[{i}:a]atrim=start={pre_roll:.6f}:duration={scene.duration:.6f},asetpts=PTS-STARTPTS,"
                f"volume={config.VIDEO_ORIGINAL_AUDIO_VOLUME:.3f},"
                f"aformat=sample_rates=44100:channel_layouts=stereo[vorig{i}]"
            )
            filter_parts.append(f"[narr{i}][vorig{i}]amix=inputs=2:duration=first:normalize=0[mixed{i}]")
            mix_src = f"mixed{i}"

        filter_parts.append(
            f"[{mix_src}]afade=t=in:d={click_fade:.6f},afade=t=out:st={fade_out_start:.6f}:d={click_fade:.6f}[{lbl}]"
        )
        audio_labels.append(f"[{lbl}]")

    if n > 1:
        filter_parts.append("".join(audio_labels) + f"concat=n={n}:v=0:a=1[aout]")
        audio_out_label = "aout"
    else:
        audio_out_label = "a0"

    # --- nhạc nền: track độc lập dài bằng tổng scene.duration, amix với
    # narration ở cuối cùng -- không đụng logic narration/xfade phía trên. ---
    if _has_any_music(scenes):
        music_inputs, music_filters, music_label = _build_music_track(scenes, input_offset=audio_offset + n)
        inputs += music_inputs
        filter_parts += music_filters
        filter_parts.append(
            f"[{audio_out_label}][{music_label}]amix=inputs=2:duration=first:normalize=0[aout_final]"
        )
        audio_out_label = "aout_final"

    filter_complex = ";".join(filter_parts)

    cmd_prefix = ["ffmpeg", "-y"] + inputs
    cmd_suffix = [
        "-map", "[vout]",
        "-map", f"[{audio_out_label}]",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
    ] + _video_encode_args() + ["-c:a", "aac", "-shortest", out_path]
    _run_ffmpeg_with_filter_script(cmd_prefix, filter_complex, cmd_suffix, work_dir, tag)


# ============================================================
# CHẾ ĐỘ FADE_BLACK (hoặc transition=0): 1 lệnh ffmpeg duy nhất
# ============================================================

def _compose_fade_black(scenes: list[Scene], padded_info: dict[int, tuple[str, int, int]], srt_path: str,
                         target_w: int, target_h: int, fps: int, transition: float, out_path: str,
                         work_dir: str, tag: str = "single") -> None:
    n = len(scenes)

    inputs = []
    for i, scene in enumerate(scenes):
        if scene.video_path:
            # Không loop -- xem ghi chú tương ứng trong _compose_crossfade.
            inputs += ["-r", str(fps), "-t", f"{scene.duration:.6f}", "-i", scene.video_path]
        else:
            padded_path, _, _ = padded_info[scene.index]
            inputs += ["-loop", "1", "-r", str(fps), "-t", f"{scene.duration:.6f}", "-i", padded_path]

    audio_offset = n
    for scene in scenes:
        inputs += ["-i", scene.audio_path]

    filter_parts = []

    # --- video: crop/zoom (ảnh) hoặc scale cover (video) + fade qua đen ở 2 đầu (nếu transition > 0) ---
    for i, scene in enumerate(scenes):
        if scene.video_path:
            vf = _video_cover_filter(target_w, target_h, fps, scene.duration)
        else:
            _, pw, ph = padded_info[scene.index]
            motion_duration = scene.speech_duration if scene.speech_duration > 0 else scene.duration
            vf = _crop_filter_for_effect(scene.effect, pw, ph, target_w, target_h, 0.0, motion_duration)
        if transition > 0 and i > 0:
            vf += f",fade=t=in:d={transition:.6f}"
        if transition > 0 and i < n - 1:
            st = max(scene.duration - transition, 0.0)
            vf += f",fade=t=out:st={st:.6f}:d={transition:.6f}"
        filter_parts.append(f"[{i}:v]{vf}[v{i}]")

    if n > 1:
        video_labels = "".join(f"[v{i}]" for i in range(n))
        filter_parts.append(f"{video_labels}concat=n={n}:v=1:a=0[vcat]")
        video_cat_label = "vcat"
    else:
        video_cat_label = "v0"

    filter_parts.append(f"[{video_cat_label}]{_subtitles_filter(srt_path)}[vout]")

    # --- audio: TTS narration là nguồn CHÍNH, trộn thêm audio gốc video (nếu
    # có + được bật), rồi mới fade 2 đầu (nếu transition > 0) và nối tuần tự. ---
    # Không có pre_roll ở chế độ này (video/ảnh input đã cắt đúng scene.duration
    # ngay từ "-t" của input) -> audio gốc video lấy trọn vẹn, không cần atrim.
    audio_labels = []
    for i, scene in enumerate(scenes):
        idx = audio_offset + i

        filter_parts.append(f"[{idx}:a]aformat=sample_rates=44100:channel_layouts=stereo[narr{i}]")
        mix_src = f"narr{i}"

        if _scene_needs_original_audio_mix(scene):
            filter_parts.append(
                f"[{i}:a]volume={config.VIDEO_ORIGINAL_AUDIO_VOLUME:.3f},"
                f"aformat=sample_rates=44100:channel_layouts=stereo[vorig{i}]"
            )
            filter_parts.append(f"[narr{i}][vorig{i}]amix=inputs=2:duration=first:normalize=0[mixed{i}]")
            mix_src = f"mixed{i}"

        af_parts = []
        if transition > 0 and i > 0:
            af_parts.append(f"afade=t=in:d={transition:.6f}")
        if transition > 0 and i < n - 1:
            st = max(scene.duration - transition, 0.0)
            af_parts.append(f"afade=t=out:st={st:.6f}:d={transition:.6f}")
        if not af_parts:
            af_parts.append("anull")  # giữ invariant: luôn có 1 filter -> luôn ra được label a{i}

        lbl = f"a{i}"
        filter_parts.append(f"[{mix_src}]{','.join(af_parts)}[{lbl}]")
        audio_labels.append(f"[{lbl}]")

    if n > 1:
        filter_parts.append("".join(audio_labels) + f"concat=n={n}:v=0:a=1[aout]")
        audio_out_label = "aout"
    else:
        audio_out_label = "a0"

    # --- nhạc nền: track độc lập dài bằng tổng scene.duration, amix với
    # narration ở cuối cùng -- không đụng logic narration/concat phía trên. ---
    if _has_any_music(scenes):
        music_inputs, music_filters, music_label = _build_music_track(scenes, input_offset=audio_offset + n)
        inputs += music_inputs
        filter_parts += music_filters
        filter_parts.append(
            f"[{audio_out_label}][{music_label}]amix=inputs=2:duration=first:normalize=0[aout_final]"
        )
        audio_out_label = "aout_final"

    filter_complex = ";".join(filter_parts)

    cmd_prefix = ["ffmpeg", "-y"] + inputs
    cmd_suffix = [
        "-map", "[vout]",
        "-map", f"[{audio_out_label}]",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
    ] + _video_encode_args() + ["-c:a", "aac", "-shortest", out_path]
    _run_ffmpeg_with_filter_script(cmd_prefix, filter_complex, cmd_suffix, work_dir, tag)


# ============================================================
# NỐI CÁC BATCH (concat demuxer, stream copy -- KHÔNG re-encode)
# ============================================================

def _probe_duration(path: str) -> float:
    """Đo thời lượng thật (giây) của 1 file media bằng ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip()) if result.stdout.strip() else 0.0


def _mix_background_music(video_path: str, music_path: str, work_dir: str) -> None:
    """Mix 1 file nhạc nền CỐ ĐỊNH vào toàn bộ video đã ghép xong (video_path),
    GHI ĐÈ tại chỗ lên chính video_path. Thay thế cơ chế cũ (mỗi cảnh tự cắt
    riêng 1 đoạn nhạc luôn bắt đầu từ giây 0 -- xem ghi chú trong
    _compose_single_scene) gây lặp nhạc mỗi khi chuyển cảnh.

    Nhạc nền giờ là 1 TRACK ĐỘC LẬP DUY NHẤT, dài đúng bằng tổng thời lượng
    video thật (đo bằng ffprobe sau khi mọi cảnh đã ghép nối liền):
    - File nhạc NGẮN hơn video -> "-stream_loop -1" tự lặp lại LIÊN TỤC
      (không cắt-dán-restart từng đoạn nhỏ như bản cũ) cho tới khi đủ độ dài,
      "-t <video_duration>" cắt đúng tại điểm kết thúc video.
    - File nhạc DÀI hơn video -> tự động bị cắt bớt bởi "-t <video_duration>",
      không cần xử lý gì thêm.
    Fade nhẹ 2 đầu toàn bộ track nhạc (không phải fade ở mỗi cảnh) để mở
    đầu/kết thúc êm, rồi amix với audio hiện có (giọng đọc TTS) của video."""
    video_duration = _probe_duration(video_path)
    if video_duration <= 0:
        print(f"  [MUSIC] CẢNH BÁO: không đo được thời lượng video -> bỏ qua nhạc nền.")
        return

    music_fade = 0.5
    fade_out_start = max(video_duration - music_fade, 0.0)

    filter_complex = (
        f"[0:a]aformat=sample_rates=44100:channel_layouts=stereo[narr];"
        f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,"
        f"afade=t=in:d={music_fade:.6f},afade=t=out:st={fade_out_start:.6f}:d={music_fade:.6f},"
        f"volume={config.MUSIC_VOLUME:.3f}[music];"
        f"[narr][music]amix=inputs=2:duration=first:normalize=0[aout]"
    )

    tmp_out = os.path.join(work_dir, "with_music.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-t", f"{video_duration:.6f}", "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        tmp_out,
    ]
    _run_ffmpeg(cmd)
    os.replace(tmp_out, video_path)


def _concat_batches(batch_paths: list[str], out_path: str, work_dir: str) -> None:
    """Nối nhiều file .mp4 (mỗi file là 1 batch đã render đầy đủ: video +
    audio + phụ đề + nhạc nền) thành 1 file cuối cùng bằng concat DEMUXER của
    ffmpeg (chế độ stream copy, "-c copy") -- KHÔNG giải mã/encode lại, nên
    KHÔNG mất thêm chất lượng và chạy gần như tức thời (chỉ ghép container).
    Yêu cầu mọi batch cùng codec/timebase (đúng vì mọi batch dùng chung
    _video_encode_args() + "-c:a aac"). Nếu chỉ có 1 batch, không cần concat,
    chỉ đơn giản đổi tên file batch thành out_path."""
    if len(batch_paths) == 1:
        os.replace(batch_paths[0], out_path)
        return

    list_path = os.path.join(work_dir, "concat_batches.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for p in batch_paths:
            # ffmpeg concat demuxer yêu cầu escape dấu nháy đơn trong đường dẫn
            escaped = p.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-c", "copy",
        out_path,
    ]
    _run_ffmpeg(cmd)


# ============================================================
# PHỤ ĐỀ THEO BATCH: cắt file .srt gốc (mốc thời gian TUYỆT ĐỐI cho toàn bộ
# video) thành từng file .srt con cho mỗi batch, dịch mốc về 0 tại đầu batch.
# ============================================================

def _slice_srt_for_batch(srt_path: str, batch_start: float, batch_end: float,
                          work_dir: str, tag: str) -> str:
    """QUAN TRỌNG: file .srt gốc (từ subtitle_gen.generate_srt) có mốc thời
    gian TUYỆT ĐỐI tính từ đầu TOÀN BỘ video (tổng dồn scene.duration). Nhưng
    mỗi batch được render RIÊNG, bắt đầu lại từ t=0 cục bộ của chính batch đó
    -- nếu dùng thẳng file .srt gốc cho mọi batch (như bản trước khi sửa),
    phụ đề của batch 2 trở đi sẽ hiện SAI THỜI ĐIỂM hoàn toàn (vd phụ đề đáng
    lẽ hiện ở giây 500 của toàn video lại bị filter 'subtitles' tìm ở giây 500
    của 1 file chỉ dài ~200s -> không hiện được, hoặc hiện sai chỗ).

    Hàm này lọc ra các dòng phụ đề có start time nằm trong [batch_start,
    batch_end), rồi DỊCH (trừ đi batch_start) để mốc thời gian trở thành
    tương đối trong batch đó (bắt đầu gần 0), ghi ra 1 file .srt con riêng
    trong work_dir, trả về đường dẫn file đó để _subtitles_filter dùng thay
    cho file .srt gốc."""
    with open(srt_path, "r", encoding="utf-8") as f:
        subs = list(srt.parse(f.read()))

    offset = datetime.timedelta(seconds=batch_start)
    end_bound = datetime.timedelta(seconds=batch_end)

    sliced = []
    for sub in subs:
        if sub.start >= end_bound or sub.end <= offset:
            continue
        new_start = max(sub.start - offset, datetime.timedelta(0))
        new_end = max(sub.end - offset, new_start)
        sliced.append(srt.Subtitle(index=len(sliced) + 1, start=new_start, end=new_end, content=sub.content))

    out_path = os.path.join(work_dir, f"subtitles_{tag}.srt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(sliced))
    return out_path


# ============================================================
# ORCHESTRATOR CHÍNH
# ============================================================

def compose_video(scenes: list[Scene], srt_path: str, work_dir: str, output_name: str = "final_video.mp4") -> str:
    select_effects_for_scenes(scenes)

    transition = max(0.0, config.TRANSITION_DURATION)
    transition_style = getattr(config, "TRANSITION_STYLE", "crossfade")
    fps = config.VIDEO_FPS

    for scene in scenes:
        if scene.video_path:
            if not os.path.exists(scene.video_path):
                raise FileNotFoundError(
                    f"Cảnh {scene.index}: không tìm thấy video dựng sẵn tại '{scene.video_path}'. "
                    f"Kiểm tra lại tên file trong dòng VIDEO: của kịch bản và "
                    f"config.INPUT_VIDEOS_DIR."
                )
            lech = abs(scene.duration - config.SCENE_VIDEO_DURATION)
            if lech > config.SCENE_VIDEO_DURATION_WARN_THRESHOLD:
                huong = "dài hơn" if scene.duration > config.SCENE_VIDEO_DURATION else "ngắn hơn"
                print(
                    f"  [COMPOSE] CẢNH BÁO Cảnh {scene.index}: audio TTS dài {scene.duration:.1f}s, "
                    f"{huong} video chuẩn {config.SCENE_VIDEO_DURATION:.1f}s tới {lech:.1f}s. "
                    f"Video KHÔNG loop -- nếu audio dài hơn video, video bị kéo dãn theo % sai lệch "
                    f"để khớp với narration; nếu audio ngắn hơn, video bị cắt bớt. Nên chỉnh lại narration "
                    f"cảnh này cho khớp gần đúng {config.SCENE_VIDEO_DURATION:.0f} giây."
                )
        else:
            if not scene.image_path or not os.path.exists(scene.image_path):
                raise FileNotFoundError(
                    f"Cảnh {scene.index}: chưa có ảnh (image_path trống). "
                    f"Kiểm tra lại bước image_sync đã chạy chưa."
                )

        if not scene.audio_path or not os.path.exists(scene.audio_path):
            raise FileNotFoundError(
                f"Cảnh {scene.index}: chưa có audio (audio_path trống). "
                f"Kiểm tra lại bước TTS đã chạy chưa."
            )

    for scene in scenes:
        if _scene_needs_original_audio_mix(scene):
            print(
                f"  [COMPOSE] Cảnh {scene.index}: trộn thêm audio gốc của video "
                f"(âm lượng {config.VIDEO_ORIGINAL_AUDIO_VOLUME:.0%}) cùng giọng đọc TTS."
            )

    if _has_any_music(scenes):
        music_groups = _group_scenes_by_music(scenes)
        num_music_groups = sum(1 for path, _ in music_groups if path)
        print(f"  [COMPOSE] Nhạc nền: {num_music_groups} đoạn nhạc khác nhau "
              f"(âm lượng {config.MUSIC_VOLUME:.0%} so với giọng đọc).")

    padded_info = _prepare_all_padded_images(scenes, config.VIDEO_WIDTH, config.VIDEO_HEIGHT,
                                              config.KEN_BURNS_ZOOM_RATIO, work_dir)

    out_path = os.path.join(config.OUTPUT_DIR, output_name)

    # QUAN TRỌNG [sửa lỗi crossfade cắt cứng]: chế độ crossfade cần mỗi file
    # scene có freeze-frame pre_roll/post_roll (giống hệt _compose_crossfade
    # gốc, xem PROJECT_MEMORY.md mục 4) để _compose_all_scenes_with_xfade có
    # "vùng dự phòng" cho xfade mà KHÔNG ăn vào nội dung thật. Cảnh đầu tiên
    # không có pre_roll (không có cảnh nào trước để hoà tan từ), cảnh cuối
    # cùng không có post_roll -- giống hệt công thức "half" trong
    # _compose_crossfade gốc.
    use_crossfade = transition > 0 and len(scenes) > 1 and transition_style != "fade_black"
    half = transition / 2.0 if use_crossfade else 0.0
    n = len(scenes)

    # Dựng từng scene riêng biệt: mỗi scene thành một file MP4 độc lập.
    # Điều này cho phép video/image/audio/subtitles của mỗi scene đồng bộ chặt,
    # rồi mới ghép các scene thành video hoàn chỉnh.
    scene_paths = []
    scene_pads: list[tuple[float, float, float]] = []  # (pre_roll, scene.duration, post_roll), song song với scene_paths
    cursor = 0.0
    total_scenes = len(scenes)
    for idx, scene in enumerate(scenes, start=1):
        pre_roll = half if (use_crossfade and idx > 1) else 0.0
        post_roll = half if (use_crossfade and idx < n) else 0.0

        scene_out = os.path.join(work_dir, f"scene_{scene.index:03d}.mp4")
        scene_srt = _slice_srt_for_batch(
            srt_path,
            cursor,
            cursor + scene.duration,
            work_dir,
            f"scene_{scene.index:03d}",
        )
        _print_compose_progress(idx, total_scenes, f"Đang dựng cảnh {scene.index}: {os.path.basename(scene_out)}")
        _compose_single_scene(
            scene,
            scene.index,
            padded_info,
            scene_srt,
            config.VIDEO_WIDTH,
            config.VIDEO_HEIGHT,
            fps,
            scene_out,
            work_dir,
            pre_roll=pre_roll,
            post_roll=post_roll,
        )
        scene_paths.append(scene_out)
        scene_pads.append((pre_roll, scene.duration, post_roll))
        cursor += scene.duration

    sys.stdout.write("\r")
    sys.stdout.flush()

    if len(scene_paths) == 1:
        os.replace(scene_paths[0], out_path)
    elif use_crossfade:
        print(f"  [COMPOSE] Đang nối {len(scene_paths)} cảnh bằng crossfade (hoà tan {transition:.1f}s)...")
        _compose_all_scenes_with_xfade(scene_paths, scene_pads, out_path, fps, transition, work_dir)
    else:
        # transition=0 hoặc TRANSITION_STYLE=fade_black -> cắt cứng giữa các
        # cảnh (đúng theo cấu hình, KHÔNG phải bug) bằng concat demuxer.
        print(f"  [COMPOSE] Đang nối {len(scene_paths)} scene (cắt cứng, "
              f"transition={transition:.1f}s/style={transition_style})...")
        _concat_batches(scene_paths, out_path, work_dir)

    # QUAN TRỌNG [sửa lỗi nhạc nền bị lặp mỗi khi chuyển cảnh]: nhạc nền được
    # mix ở ĐÂY, SAU KHI toàn bộ video đã ghép nối liền thành 1 file duy nhất
    # -- KHÔNG còn mix riêng theo từng scene như trước (xem ghi chú trong
    # _compose_single_scene + _mix_background_music). Vì mọi scene dùng CHUNG
    # 1 music_path cố định (modules/music_engine.py), chỉ cần lấy music_path
    # của cảnh đầu tiên có nhạc.
    music_path = next((s.music_path for s in scenes if s.music_path), "")
    if music_path:
        print(f"  [COMPOSE] Đang trộn nhạc nền xuyên suốt video -> {music_path} "
              f"(âm lượng {config.MUSIC_VOLUME:.0%})...")
        _mix_background_music(out_path, music_path, work_dir)

    print(f"  [COMPOSE] Video hoàn chỉnh -> {out_path}")
    return out_path

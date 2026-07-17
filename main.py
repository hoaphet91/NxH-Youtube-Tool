"""
PIPELINE SINH VIDEO TỰ ĐỘNG TỪ KỊCH BẢN — CLI chính

Cách dùng:
    python main.py --script example_script.txt --title "Tên video của tôi"

CHUẨN BỊ TRƯỚC KHI CHẠY:
    Tự tạo ảnh tĩnh cho từng cảnh, LƯU LẦN LƯỢT ĐÚNG THỨ TỰ CẢNH vào thư mục
    config.INPUT_IMAGES_DIR (mặc định: input_images/). KHÔNG cần tự đặt tên
    file theo quy tắc scene_001.png — tool sẽ tự động đổi tên ảnh dựa theo
    THỜI GIAN TẠO FILE để khớp đúng thứ tự cảnh (xem modules/image_sync.py).
    Quan trọng: ảnh cho cảnh 1 phải được lưu TRƯỚC ảnh cho cảnh 2, cảnh 2 trước
    cảnh 3, v.v. Số lượng ảnh phải khớp chính xác số cảnh trong kịch bản.

    Pipeline này KHÔNG tự sinh ảnh AI và KHÔNG cần GPU/ComfyUI/Wan2.1 — video
    được dựng bằng hiệu ứng "Ken Burns" (pan/zoom camera ảo) ngay trên ảnh
    tĩnh bạn cung cấp.

Pipeline 8 bước:
    1. script_parser  -> tách kịch bản thành scenes
    2. tts_engine      -> sinh audio (ElevenLabs/OpenAI/edge-tts) cho từng scene.
                          Đặt TTS_ENABLED=false trong .env để TẮT gọi API TTS
                          thật, dùng audio có sẵn trong input_audio/ để test
                          (tiết kiệm chi phí/token) — xem modules/tts_engine.py.
    2.5. music_engine  -> gán 1 file nhạc nền CỐ ĐỊNH (config.BACKGROUND_
                          MUSIC_PATH, do bạn tự chọn) xuyên suốt toàn bộ
                          video. Đặt MUSIC_ENABLED=false trong .env để tắt
                          hoàn toàn — xem modules/music_engine.py.
    3. image_sync      -> tự động đổi tên ảnh theo thời gian tạo (scene_XXX)
                          và gán vào scene.image_path
    4. subtitle_gen    -> tạo file .srt từ timing audio thật
    5. video_compose   -> chọn hiệu ứng Ken Burns (effect_selector nội bộ),
                          ghép ảnh tĩnh + audio + nhạc nền + phụ đề thành video
    6. policy_check    -> rà soát tự động dựa theo checklist YouTube
    7. export          -> lưu báo cáo + đường dẫn output cuối cùng
"""
import os
import sys
import shutil
import argparse
import tempfile

# QUAN TRỌNG: ép stdout/stderr dùng UTF-8, bất kể console đang ở codepage nào.
# Trên Windows, console mặc định thường dùng codepage cp1252 (hoặc codepage
# theo ngôn ngữ hệ điều hành) -- codepage này KHÔNG mã hoá được nhiều ký tự
# tiếng Việt có dấu, khiến print() các dòng log tiếng Việt (vd "BẮT ĐẦU") ném
# UnicodeEncodeError và crash pipeline ngay từ dòng log đầu tiên. Lỗi này xảy
# ra CẢ KHI chạy trực tiếp "python main.py ..." trong cmd.exe/PowerShell, LẪN
# khi chạy qua Web UI (subprocess con kế thừa encoding mặc định của hệ thống,
# không phải UTF-8, nếu không set rõ). reconfigure() có từ Python 3.7+; bọc
# try/except vì 1 số môi trường hiếm gặp có stdout không phải TextIOWrapper
# (không hỗ trợ reconfigure) -- khi đó im lặng bỏ qua, không chặn chương trình.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import config
from modules.script_parser import parse_script
from modules.tts_engine import generate_audio_for_scenes
from modules.music_engine import assign_music_to_scenes
from modules.image_sync import sync_images_to_scenes
from modules.subtitle_gen import generate_srt
from modules.video_compose import compose_video
from modules.policy_check import run_policy_check
from modules.export import export_report, format_ad_breaks


def _check_env_or_die() -> None:
    """Kiểm tra sớm xem .env đã được load đúng và có key cần thiết chưa,
    báo lỗi rõ ràng ngay từ đầu thay vì để chạy nửa chừng mới gãy."""
    problems = []

    if not os.path.exists(os.path.join(config.BASE_DIR, ".env")):
        problems.append(
            f"Không tìm thấy file .env tại: {os.path.join(config.BASE_DIR, '.env')}\n"
            f"      -> Chạy: copy .env.example .env (Windows) hoặc cp .env.example .env (Mac/Linux),\n"
            f"         rồi mở file .env vừa tạo và điền key thật vào."
        )
    else:
        if config.TTS_ENABLED:
            if config.TTS_PROVIDER == "elevenlabs" and (not config.ELEVENLABS_API_KEY or not config.ELEVENLABS_VOICE_ID
                    or "your_" in config.ELEVENLABS_API_KEY or "your_" in config.ELEVENLABS_VOICE_ID):
                problems.append(
                    "TTS_PROVIDER=elevenlabs nhưng ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID trong .env "
                    "vẫn còn để giá trị mẫu hoặc trống. Điền key thật từ elevenlabs.io vào."
                )
            if config.TTS_PROVIDER == "openai" and (not config.OPENAI_API_KEY or "your_" in config.OPENAI_API_KEY):
                problems.append("TTS_PROVIDER=openai nhưng OPENAI_API_KEY trong .env vẫn trống/còn giá trị mẫu.")
            if config.TTS_PROVIDER == "edge" and shutil.which("edge-tts") is None:
                problems.append(
                    "TTS_PROVIDER=edge nhưng không tìm thấy lệnh 'edge-tts' trong PATH.\n"
                    "      -> Cài đặt: pip install edge-tts"
                )

    if not config.TTS_ENABLED and not os.path.isdir(config.LOCAL_AUDIO_DIR):
        problems.append(
            f"TTS_ENABLED=false (đang tắt gọi API TTS để test) nhưng không tìm thấy thư mục audio "
            f"có sẵn: {config.LOCAL_AUDIO_DIR}\n"
            f"      -> Tạo thư mục này và bỏ vào audio có sẵn cho từng cảnh (đúng thứ tự) trước khi chạy,\n"
            f"         hoặc đặt TTS_ENABLED=true trong .env để gọi API TTS thật."
        )

    if not os.path.isdir(config.INPUT_IMAGES_DIR):
        problems.append(
            f"Không tìm thấy thư mục ảnh đầu vào: {config.INPUT_IMAGES_DIR}\n"
            f"      -> Tự tạo ảnh cho từng cảnh, LƯU LẦN LƯỢT ĐÚNG THỨ TỰ CẢNH\n"
            f"         (không cần đặt tên file gì đặc biệt, tool tự đổi tên theo\n"
            f"         thời gian tạo) và bỏ vào đúng thư mục trên trước khi chạy pipeline."
        )

    if config.MUSIC_ENABLED and not os.path.exists(getattr(config, "BACKGROUND_MUSIC_PATH", "")):
        print(
            f"  [CẢNH BÁO] MUSIC_ENABLED=true nhưng không tìm thấy file nhạc nền tại "
            f"'{config.BACKGROUND_MUSIC_PATH}'.\n"
            f"      -> Video sẽ KHÔNG có nhạc nền (không chặn pipeline).\n"
            f"      -> Bỏ file nhạc bạn chọn vào đúng đường dẫn trên, hoặc set biến "
            f"BACKGROUND_MUSIC_PATH trong .env trỏ tới file nhạc thật.\n"
        )

    if problems:
        print("\n=== KHÔNG THỂ CHẠY PIPELINE — thiếu cấu hình ===\n")
        for p in problems:
            print(f"  - {p}\n")
        print(f"File .env cần nằm chính xác tại: {os.path.join(config.BASE_DIR, '.env')}")
        print("Lưu ý trên Windows: đảm bảo file thật sự tên '.env', không phải '.env.txt'")
        print("(Windows Explorer mặc định ẩn phần đuôi file, dễ bị đặt nhầm tên).\n")
        raise SystemExit(1)


def run_pipeline(script_path: str, title: str, output_name: str) -> None:
    print(f"\n=== BẮT ĐẦU PIPELINE: {title} ===\n")
    _check_env_or_die()

    with tempfile.TemporaryDirectory(dir=config.BASE_DIR) as work_dir:
        print("[1/8] Đang tách kịch bản thành các cảnh...")
        scenes = parse_script(script_path)
        print(f"      -> {len(scenes)} cảnh được tách ra.\n")

        print("[2/8] Đang sinh audio (TTS)...")
        generate_audio_for_scenes(scenes, work_dir)
        print()

        print("[2.5/8] Đang tải nhạc nền (Freesound)...")
        assign_music_to_scenes(scenes)
        print()

        print("[3/8] Đang đồng bộ ảnh (theo thời gian tạo)...")
        sync_images_to_scenes(scenes)
        print()

        print("[4/8] Đang tạo phụ đề (.srt)...")
        srt_path = generate_srt(scenes, work_dir)
        print()

        print("[5/8] Đang dựng video (hiệu ứng Ken Burns + audio + nhạc nền + phụ đề)...")
        video_path = compose_video(scenes, srt_path, work_dir, output_name=output_name)
        print()

        total_duration = sum(s.duration for s in scenes)

        print("[6/8] Đang chạy policy check tự động...")
        policy_report = run_policy_check(scenes, title, total_duration)
        report_text = policy_report.render(title)
        ad_breaks_text = format_ad_breaks(scenes)
        if ad_breaks_text:
            report_text = report_text + "\n\n" + ad_breaks_text
        print("\n" + report_text + "\n")

        print("[7/8] Đang xuất báo cáo cuối cùng...")
        final_srt_path = os.path.join(config.OUTPUT_DIR, "subtitles.srt")
        with open(srt_path, "r", encoding="utf-8") as f_in, open(final_srt_path, "w", encoding="utf-8") as f_out:
            f_out.write(f_in.read())
        export_report(title, video_path, final_srt_path, report_text)

    print(f"\n=== HOÀN TẤT. Video: {os.path.join(config.OUTPUT_DIR, output_name)} ===")
    print("Nhắc lại: hãy tự kiểm tra thumbnail + nguồn nhạc nền (nếu có) trước khi đăng.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sinh video tự động từ kịch bản text.")
    parser.add_argument("--script", required=True, help="Đường dẫn tới file kịch bản .txt")
    parser.add_argument("--title", required=True, help="Tiêu đề video (dùng cho báo cáo policy check)")
    parser.add_argument("--output", default="final_video.mp4", help="Tên file video xuất ra (trong thư mục output/)")
    args = parser.parse_args()

    run_pipeline(args.script, args.title, args.output)

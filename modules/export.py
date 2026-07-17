"""
Module 7/7: EXPORT
Lưu báo cáo policy check ra file .txt kèm timestamp trong thư mục output/,
và in tóm tắt đường dẫn các file kết quả cuối cùng (video, srt, report).

format_ad_breaks(): liệt kê timecode ước tính của các marker
***SPONSOR_BREAK***/***MIDROLL_BREAK*** (nếu kịch bản có dùng -- xem skill
prehistoric-humans-script-SKILL-US.md + modules/script_parser.py), để người
dùng tự chèn quảng cáo khi edit video. Pipeline KHÔNG tự động chèn quảng cáo
vào file video xuất ra, chỉ báo cáo vị trí.
"""
import os
import sys
import datetime

import config
from modules.cli_progress import write_progress
from modules.script_parser import Scene


def format_ad_breaks(scenes: list[Scene]) -> str:
    """Tính timecode ước tính (dựa trên tổng dồn scene.duration, cùng cách
    subtitle_gen.py tính mốc phụ đề) cho từng marker quảng cáo tìm thấy
    trong scene.ad_markers. Trả về chuỗi rỗng nếu kịch bản không có marker
    nào (không thêm mục thừa vào report)."""
    lines = []
    cumulative = 0.0
    for scene in scenes:
        for marker in scene.ad_markers:
            total_seconds = int(cumulative)
            hh, rem = divmod(total_seconds, 3600)
            mm, ss = divmod(rem, 60)
            lines.append(f"- Cảnh {scene.index}: {marker} tại khoảng {hh:02d}:{mm:02d}:{ss:02d}")
        cumulative += scene.duration

    if not lines:
        return ""

    return (
        "ĐIỂM CHÈN QUẢNG CÁO (từ marker trong kịch bản -- PIPELINE KHÔNG TỰ "
        "CHÈN, chỉ báo vị trí để tự chỉnh sửa video):\n" + "\n".join(lines)
    )


def export_report(title: str, video_path: str, srt_path: str, report_text: str) -> str:
    """Ghi report_text ra file report_<timestamp>.txt trong OUTPUT_DIR, trả về đường dẫn file đó."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"report_{timestamp}.txt"
    report_path = os.path.join(config.OUTPUT_DIR, report_filename)

    header = f"Tiêu đề video: {title}\nThời gian xuất báo cáo: {datetime.datetime.now().isoformat()}\n"
    header += f"Video: {video_path}\nSubtitle: {srt_path}\n\n"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(report_text)

    write_progress("EXPORT", 100, 100, "lưu báo cáo và kết quả cuối cùng")
    print(f"\n  [EXPORT] Đã lưu báo cáo -> {report_path}")
    print(f"  [EXPORT] Video cuối cùng -> {video_path}")
    print(f"  [EXPORT] Phụ đề cuối cùng -> {srt_path}")

    return report_path

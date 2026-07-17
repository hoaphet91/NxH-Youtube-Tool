"""
Module 2.5/7: MUSIC ENGINE
QUAN TRỌNG [thay thế cơ chế Freesound cũ]: KHÔNG còn tải nhạc theo sound ID
từ Freesound.org theo dòng MUSIC: trong kịch bản nữa. Giờ chỉ đơn giản gán
ĐÚNG 1 file nhạc nền cố định (config.BACKGROUND_MUSIC_PATH, do người dùng tự
chọn/tải sẵn) vào scene.music_path của TẤT CẢ các cảnh -- nhạc nền áp dụng
XUYÊN SUỐT toàn bộ video, không đổi theo cảnh/đoạn nữa.

modules/video_compose.py không cần sửa gì để dùng cơ chế mới này: nó chỉ đọc
scene.music_path (không quan tâm nguồn gốc), và cơ chế "gộp các cảnh liên tiếp
cùng music_path thành 1 cụm" (modules/video_compose.py::_group_scenes_by_music)
tự động gộp toàn bộ video thành ĐÚNG 1 cụm duy nhất vì mọi scene giờ dùng
chung 1 đường dẫn -- kết quả là 1 track nhạc nền loop xuyên suốt toàn video
(nếu file ngắn hơn tổng thời lượng) hoặc bị cắt bớt (nếu dài hơn), fade nhẹ ở
đầu/cuối, mix vào giọng đọc TTS ở âm lượng config.MUSIC_VOLUME.

Nếu config.MUSIC_ENABLED=False, hoặc BACKGROUND_MUSIC_PATH trống/không tồn
tại -> mọi scene.music_path để rỗng (không có nhạc nền), KHÔNG chặn pipeline.
"""
import os

import config
from modules.script_parser import Scene


def assign_music_to_scenes(scenes: list[Scene]) -> None:
    """Gán CÙNG 1 đường dẫn nhạc nền cố định (config.BACKGROUND_MUSIC_PATH)
    vào scene.music_path của mọi scene, nếu MUSIC_ENABLED=True và file tồn
    tại. Nếu không, để trống toàn bộ (video chỉ có giọng đọc, không chặn
    pipeline)."""
    if not config.MUSIC_ENABLED:
        print("  [MUSIC] MUSIC_ENABLED=false -> bỏ qua nhạc nền cho toàn bộ video.")
        return

    music_path = getattr(config, "BACKGROUND_MUSIC_PATH", "")

    if not music_path:
        print("  [MUSIC] Chưa cấu hình BACKGROUND_MUSIC_PATH -> video không có nhạc nền.")
        return

    if not os.path.exists(music_path):
        print(
            f"  [MUSIC] CẢNH BÁO: không tìm thấy file nhạc nền tại '{music_path}' "
            f"-> video sẽ KHÔNG có nhạc nền (không chặn pipeline).\n"
            f"      -> Bỏ file nhạc bạn chọn vào đúng đường dẫn trên, hoặc set biến "
            f"BACKGROUND_MUSIC_PATH trong .env trỏ tới file nhạc thật."
        )
        return

    for scene in scenes:
        scene.music_path = music_path

    print(f"  [MUSIC] Dùng 1 file nhạc nền xuyên suốt video -> {music_path} "
          f"(âm lượng {config.MUSIC_VOLUME:.0%} so với giọng đọc).")

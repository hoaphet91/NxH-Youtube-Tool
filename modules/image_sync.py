"""
Module 3/7: IMAGE SYNC
Bạn chỉ cần tạo ảnh cho từng cảnh và lưu vào config.INPUT_IMAGES_DIR theo ĐÚNG
THỨ TỰ THỜI GIAN bạn tạo/lưu chúng (ảnh cảnh 1 lưu trước, cảnh 2 lưu sau, ...).
KHÔNG cần tự đặt tên file theo quy tắc scene_001.png — tên file gốc tuỳ ý.

LƯU Ý: cảnh nào đã có scene.video_path (khai báo VIDEO: trong kịch bản, xem
modules/script_parser.py) sẽ dùng VIDEO thay ảnh tĩnh -- module này TỰ ĐỘNG
LOẠI TRỪ các cảnh đó khỏi việc quét/đối chiếu/gán ảnh. Số ảnh cần chuẩn bị chỉ
cần khớp với SỐ CẢNH KHÔNG CÓ VIDEO:, không phải tổng số cảnh trong kịch bản.

QUAN TRỌNG (sửa [2026-07-14]): nội dung sau field VIDEO: trong kịch bản (do
các skill viết kịch bản sinh ra) thường là PROMPT tạo video AI, KHÔNG PHẢI tên
file thật. Vì vậy module KHÔNG còn tìm file theo đúng tên đó nữa -- video được
đồng bộ theo THỜI GIAN TẠO FILE, giống hệt cơ chế ảnh: bạn tự tạo video (từ
prompt trong kịch bản/file *-prompts.md), lưu LẦN LƯỢT ĐÚNG THỨ TỰ CẢNH vào
config.INPUT_VIDEOS_DIR (tên file tuỳ ý), tool tự sắp xếp + đổi tên + gán vào
đúng scene -- xem _sync_videos_to_scenes().

Module này sẽ:
1. Quét toàn bộ ảnh hợp lệ (.png/.jpg/.jpeg) trong INPUT_IMAGES_DIR
2. Sắp xếp theo thời gian tạo file (creation time trên Windows/macOS; trên Linux
   không có creation time thật nên dùng thời gian sửa đổi gần nhất - mtime -
   làm proxy tốt nhất có thể)
3. Đối chiếu số lượng ảnh với số cảnh KHÔNG CÓ video_path — báo lỗi rõ ràng nếu lệch
4. Đổi tên lần lượt thành scene_001.<ext>, scene_002.<ext>, ... theo đúng thứ tự
   thời gian đó, và GÁN TRỰC TIẾP vào scene.image_path (chỉ cho các cảnh KHÔNG
   CÓ video_path) để modules/video_compose.py dùng ảnh này dựng hiệu ứng Ken
   Burns (pan/zoom).

LƯU Ý QUAN TRỌNG:
- Việc đổi tên là ĐỔI TÊN THẬT trên ổ đĩa (os.rename), không phải copy. Ảnh gốc
  của bạn sẽ có tên mới sau khi chạy pipeline. Backup trước nếu muốn giữ tên gốc.
- Nếu số ảnh và số cảnh (không tính cảnh có VIDEO:) không khớp, KHÔNG đoán mò
  — dừng lại và báo lỗi để bạn tự kiểm tra (thừa/thiếu ảnh, hoặc kịch bản tách
  sai số cảnh).
"""
import os
import sys

import config
from modules.cli_progress import write_progress
from modules.script_parser import Scene

VALID_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
VALID_VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".webm", ".avi")


def _print_step_progress(done: int, total: int, label: str) -> None:
    write_progress("IMAGE-SYNC", done, total, label)


def _get_creation_time(path: str) -> float:
    """Lấy thời gian tạo file tốt nhất có thể theo từng hệ điều hành.
    Windows/macOS: st_birthtime phản ánh đúng thời gian tạo.
    Linux: không có creation time thật qua Python stat thông thường -> dùng
    thời gian sớm hơn giữa ctime/mtime làm proxy."""
    stat = os.stat(path)
    if hasattr(stat, "st_birthtime"):  # macOS, một số bản BSD
        return stat.st_birthtime
    return min(stat.st_ctime, stat.st_mtime) if stat.st_ctime else stat.st_mtime


def _list_valid_images(image_dir: str) -> list[str]:
    names = [
        f for f in os.listdir(image_dir)
        if f.lower().endswith(VALID_IMAGE_EXTENSIONS) and not f.startswith("__tmp_sync_")
    ]
    return [os.path.join(image_dir, f) for f in names]


def _list_valid_videos(video_dir: str) -> list[str]:
    names = [
        f for f in os.listdir(video_dir)
        if f.lower().endswith(VALID_VIDEO_EXTENSIONS) and not f.startswith("__tmp_sync_")
    ]
    return [os.path.join(video_dir, f) for f in names]


def _sync_videos_to_scenes(scenes: list[Scene]) -> None:
    """Cảnh có field VIDEO: trong kịch bản (nội dung thường là PROMPT tạo
    video AI, KHÔNG PHẢI tên file -- xem docstring đầu module) được xử lý
    giống HỆT cơ chế ảnh: quét config.INPUT_VIDEOS_DIR, sắp theo thời gian
    tạo file, đổi tên thành scene_video_XXX.<ext>, rồi GHI ĐÈ scene.video_path
    (từ nội dung prompt gốc) thành đường dẫn file video thật, theo ĐÚNG THỨ TỰ
    cảnh xuất hiện trong kịch bản."""
    scenes_needing_video = [s for s in scenes if s.video_path]
    if not scenes_needing_video:
        return

    video_dir = config.INPUT_VIDEOS_DIR
    if not os.path.isdir(video_dir):
        raise FileNotFoundError(
            f"Kịch bản có {len(scenes_needing_video)} cảnh dùng VIDEO: nhưng không tìm thấy "
            f"thư mục video đầu vào: {video_dir}\n"
            f"      -> Tự tạo video (từ prompt trong kịch bản) và lưu LẦN LƯỢT ĐÚNG THỨ TỰ "
            f"CẢNH vào thư mục này trước khi chạy pipeline."
        )

    video_paths = _list_valid_videos(video_dir)

    if not video_paths:
        raise FileNotFoundError(
            f"Không tìm thấy video nào ({'/'.join(VALID_VIDEO_EXTENSIONS)}) trong: {video_dir}\n"
            f"      -> Lưu video cho từng cảnh có VIDEO: vào thư mục này trước khi chạy pipeline."
        )

    if len(video_paths) != len(scenes_needing_video):
        raise ValueError(
            f"Số video tìm thấy ({len(video_paths)}) KHÔNG khớp số cảnh CẦN VIDEO trong kịch "
            f"bản ({len(scenes_needing_video)}).\n"
            f"      -> Thư mục: {video_dir}\n"
            f"      -> Kiểm tra lại: mỗi cảnh có dòng VIDEO: cần đúng 1 video, không thừa không thiếu."
        )

    video_paths.sort(key=_get_creation_time)

    temp_paths = []
    for i, path in enumerate(video_paths, start=1):
        ext = os.path.splitext(path)[1].lower()
        temp_path = os.path.join(video_dir, f"__tmp_sync_{i:03d}{ext}")
        os.rename(path, temp_path)
        temp_paths.append(temp_path)

    print(f"  [VIDEO-SYNC] Đã tìm thấy {len(temp_paths)} video, đang đồng bộ theo thời gian tạo...")
    for i, temp_path in enumerate(temp_paths, start=1):
        ext = os.path.splitext(temp_path)[1]
        final_path = os.path.join(video_dir, f"scene_video_{i:03d}{ext}")
        os.rename(temp_path, final_path)
        target_scene = scenes_needing_video[i - 1]
        target_scene.video_path = final_path
        _print_step_progress(i, len(temp_paths), f"video {os.path.basename(final_path)}")
    sys.stdout.write("\r")
    sys.stdout.flush()


def sync_images_to_scenes(scenes: list[Scene]) -> None:
    """Quét, sắp xếp theo thời gian tạo, đổi tên ảnh thành scene_XXX.<ext>, và
    gán đường dẫn ảnh tương ứng vào từng scene.image_path theo đúng thứ tự --
    CHỈ áp dụng cho các cảnh KHÔNG CÓ scene.video_path (cảnh dùng VIDEO: được
    bỏ qua hoàn toàn ở phần xử lý ảnh, nhưng video_path của chúng vẫn được
    đồng bộ theo thời gian tạo file thành đường dẫn đầy đủ ở đây -- xem
    _sync_videos_to_scenes)."""
    _sync_videos_to_scenes(scenes)

    image_dir = config.INPUT_IMAGES_DIR

    # Chỉ những cảnh KHÔNG dùng video có sẵn mới cần ảnh tĩnh.
    scenes_needing_image = [s for s in scenes if not s.video_path]
    num_scenes = len(scenes_needing_image)

    if num_scenes == 0:
        print("  [IMAGE-SYNC] Mọi cảnh đều dùng VIDEO: có sẵn, không cần ảnh tĩnh -> bỏ qua bước này.")
        return

    if not os.path.isdir(image_dir):
        raise FileNotFoundError(
            f"Không tìm thấy thư mục ảnh đầu vào: {image_dir}\n"
            f"      -> Tạo thư mục này và lưu ảnh cho từng cảnh (không tính cảnh có VIDEO:) "
            f"vào đó trước khi chạy pipeline."
        )

    image_paths = _list_valid_images(image_dir)

    if not image_paths:
        raise FileNotFoundError(
            f"Không tìm thấy ảnh nào (.png/.jpg/.jpeg) trong: {image_dir}\n"
            f"      -> Tự tạo ảnh cho từng cảnh (không tính cảnh có VIDEO:) và lưu vào "
            f"thư mục này trước khi chạy pipeline."
        )

    if len(image_paths) != num_scenes:
        raise ValueError(
            f"Số ảnh tìm thấy ({len(image_paths)}) KHÔNG khớp số cảnh CẦN ẢNH trong kịch bản "
            f"({num_scenes}, đã trừ các cảnh dùng VIDEO:).\n"
            f"      -> Thư mục: {image_dir}\n"
            f"      -> Kiểm tra lại: mỗi cảnh KHÔNG có dòng VIDEO: cần đúng 1 ảnh, không thừa không thiếu."
        )

    # Sắp xếp theo thời gian tạo tăng dần -> ảnh tạo trước = cảnh nhỏ hơn
    image_paths.sort(key=_get_creation_time)

    # Đổi tên qua bước trung gian (__tmp_sync_XXX) để tránh trường hợp đè lẫn
    # nhau khi tên đích trùng với tên một file khác đang có trong danh sách.
    temp_paths = []
    for i, path in enumerate(image_paths, start=1):
        ext = os.path.splitext(path)[1].lower()
        temp_path = os.path.join(image_dir, f"__tmp_sync_{i:03d}{ext}")
        os.rename(path, temp_path)
        temp_paths.append(temp_path)

    print(f"  [IMAGE-SYNC] Đã tìm thấy {len(temp_paths)} ảnh, đang đồng bộ theo thời gian tạo...")
    for i, temp_path in enumerate(temp_paths, start=1):
        ext = os.path.splitext(temp_path)[1]
        final_path = os.path.join(image_dir, f"scene_{i:03d}{ext}")
        os.rename(temp_path, final_path)
        target_scene = scenes_needing_image[i - 1]
        target_scene.image_path = final_path
        _print_step_progress(i, len(temp_paths), f"ảnh {os.path.basename(final_path)}")
    sys.stdout.write("\r")
    sys.stdout.flush()

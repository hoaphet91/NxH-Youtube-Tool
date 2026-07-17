"""
Module 1/7: SCRIPT PARSER
Đọc file kịch bản text và tách thành danh sách các "cảnh" (scene).

ĐỊNH DẠNG KỊCH BẢN HỖ TRỢ:

Cách 1 - Đơn giản (mỗi đoạn văn cách nhau bằng dòng trống = 1 cảnh):

    Đây là lời thoại của cảnh đầu tiên.

    Đây là lời thoại của cảnh thứ hai.

Cách 2 - Có cấu trúc rõ ràng (khuyến nghị):

    [SCENE]
    NARRATION: Đây là lời thoại của cảnh đầu tiên.
    MOTION: pan sang trái, nhấn mạnh không gian rộng

    [SCENE]
    NARRATION: Đây là lời thoại của cảnh thứ hai.
    VIDEO: intro_bien.mp4

Dòng MOTION: (tuỳ chọn) giờ đóng vai trò GỢI Ý chọn hiệu ứng Ken Burns
(pan/zoom trên ảnh tĩnh) cho modules/effect_selector.py, KHÔNG còn là mô tả
chuyển động nhân vật cho AI animate như bản Wan2.1 cũ.

Dòng VIDEO: (tuỳ chọn) đánh dấu cảnh đó DÙNG VIDEO THAY ẢNH TĨNH -- xem
modules/video_compose.py. Nội dung ghi sau VIDEO: THƯỜNG LÀ PROMPT tạo video
AI (do skill viết kịch bản sinh ra), KHÔNG PHẢI tên file -- parser chỉ lưu lại
nguyên văn, KHÔNG dùng làm tên file để tìm. Video thật được modules/image_sync.py
tự động đồng bộ theo THỜI GIAN TẠO FILE trong config.INPUT_VIDEOS_DIR, giống
hệt cơ chế ảnh (xem image_sync.py::_sync_videos_to_scenes) -- bạn chỉ cần tạo
video (theo prompt) và lưu LẦN LƯỢT ĐÚNG THỨ TỰ CẢNH vào thư mục đó, không cần
đặt tên file khớp nội dung kịch bản. Cảnh có VIDEO: sẽ KHÔNG cần ảnh trong
input_images/ (modules/image_sync.py tự loại trừ cảnh này khỏi bước đối
chiếu số ảnh/số cảnh). Vì video KHÔNG được cắt/loop theo audio làm cơ chế
chính (giọng đọc TTS narration LUÔN là audio CHÍNH của cảnh), khi viết kịch
bản cho cảnh dùng VIDEO: nên canh narration dài tương đương ĐỘ DÀI VIDEO THẬT
(khuyến nghị 6-8 giây đọc) để hình và giọng đọc khớp nhau tự nhiên. Audio GỐC
của video (nếu có) KHÔNG bị tắt hoàn toàn -- được TRỘN vào cùng giọng đọc TTS
với âm lượng nhỏ hơn theo config.VIDEO_ORIGINAL_AUDIO_VOLUME (mặc định 0.3;
đặt 0 để tắt hẳn) -- xem modules/video_compose.py::_scene_needs_original_audio_mix.

MARKER QUẢNG CÁO ***SPONSOR_BREAK***/***MIDROLL_BREAK*** (dùng bởi skill
prehistoric-humans-script-SKILL-US.md): 2 marker này được viết XEN GIỮA nội
dung NARRATION (không phải field riêng, cố tình để lọt vào vùng regex bắt
narration). Parser TỰ ĐỘNG tách 2 marker này ra khỏi narration trước khi gán
vào Scene -- tránh TTS đọc to ký tự "*" thành lời -- và lưu lại vào
scene.ad_markers theo đúng thứ tự xuất hiện để biết cảnh nào cần chèn quảng
cáo (xem modules/export.py::format_ad_breaks, gọi từ main.py, in ra timecode
ước tính dựa trên scene.duration sau bước TTS). Pipeline KHÔNG tự động chèn
quảng cáo vào file video, chỉ báo cáo vị trí để người dùng tự làm ở bước edit.

NHẠC NỀN: kịch bản KHÔNG còn field MUSIC: nữa (đã bỏ cơ chế tải theo sound ID
từ Freesound.org). Toàn bộ video giờ dùng CHUNG 1 file nhạc nền cố định do
người dùng tự chọn (config.BACKGROUND_MUSIC_PATH) -- xem modules/music_engine.py.
Nếu kịch bản cũ vẫn còn dòng MUSIC: sót lại, parser sẽ KHÔNG nhận diện field
này nữa và toàn bộ dòng đó sẽ bị gộp vào NARRATION (regex NARRATION: không
còn dừng ở "\nMUSIC:"), gây đọc nhầm thành lời thoại -- xoá thủ công mọi dòng
MUSIC: còn sót trong kịch bản cũ trước khi chạy pipeline với bản parser này.
"""
import re
from dataclasses import dataclass, field


@dataclass
class Scene:
    index: int
    narration: str
    motion_prompt: str = ""    # gợi ý hiệu ứng Ken Burns (dòng MOTION:, tuỳ chọn)
    image_path: str = ""       # đường dẫn ảnh tĩnh của cảnh (gán bởi image_sync.py)
    video_path: str = ""       # đường dẫn video dựng sẵn (dòng VIDEO:, tuỳ chọn -- nếu có, DÙNG THAY image_path)
    effect: str = ""           # hiệu ứng Ken Burns được chọn (gán bởi effect_selector.py, bỏ qua nếu có video_path)
    audio_path: str = ""
    duration: float = 0.0
    speech_duration: float = 0.0  # thời lượng lời thoại THẬT, chưa gồm SCENE_AUDIO_GAP (gán bởi tts_engine._apply_scene_gaps) -- dùng làm mốc chuyển động Ken Burns để camera dừng đúng lúc giọng đọc dứt, xem video_compose.py
    ad_markers: list[str] = field(default_factory=list)  # ***SPONSOR_BREAK***/***MIDROLL_BREAK*** tìm thấy trong cảnh (đã tách khỏi narration, xem _extract_ad_markers)
    music_path: str = ""       # đường dẫn file nhạc nền CỐ ĐỊNH, giống nhau cho MỌI scene (gán bởi modules/music_engine.py từ config.BACKGROUND_MUSIC_PATH; rỗng nếu tắt/không có file)


_AD_MARKER_RE = re.compile(r"\s*\*\*\*\s*(SPONSOR_BREAK|MIDROLL_BREAK)\s*\*\*\*\s*")


def _extract_ad_markers(narration: str) -> tuple[str, list[str]]:
    """Tách marker ***SPONSOR_BREAK***/***MIDROLL_BREAK*** (nếu có) ra khỏi
    narration -- trả về (narration đã dọn sạch, danh sách marker theo đúng
    thứ tự xuất hiện). Kịch bản KHÔNG có marker (mọi kịch bản cũ) -> trả về
    nguyên văn, không đổi hành vi cũ."""
    markers = _AD_MARKER_RE.findall(narration)
    if not markers:
        return narration, []
    cleaned = _AD_MARKER_RE.sub(" ", narration).strip()
    cleaned = re.sub(r" {2,}", " ", cleaned)
    return cleaned, markers


def parse_script(file_path: str) -> list[Scene]:
    """Ảnh không do kịch bản chỉ định (người dùng tự tạo, lưu vào
    config.INPUT_IMAGES_DIR theo đúng thứ tự thời gian; xem modules/image_sync.py).
    Dòng MOTION: (tuỳ chọn) là gợi ý hiệu ứng camera cho cảnh đó.
    Dòng VIDEO: (tuỳ chọn) đánh dấu cảnh dùng video thay ảnh tĩnh; nội dung
    (thường là prompt) chỉ được lưu lại, KHÔNG dùng làm tên file -- video thật
    được modules/image_sync.py đồng bộ theo thời gian tạo file, xem
    modules/video_compose.py.
    Không còn field MUSIC: -- nhạc nền là 1 file cố định áp dụng cho toàn bộ
    video, xem config.BACKGROUND_MUSIC_PATH + modules/music_engine.py."""
    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()

    scenes: list[Scene] = []

    if "[SCENE]" in raw:
        # QUAN TRỌNG: raw.split("[SCENE]") luôn trả về phần tử đầu tiên là
        # nội dung đứng TRƯỚC dấu [SCENE] đầu tiên trong file (ví dụ: tiêu đề
        # markdown "# ...", bảng "| Word Count | ... |", dòng "---" ở các file
        # .md do skill viết kịch bản xuất ra -- xem prehistoric-humans-script-
        # SKILL-US.md Phase 7). Phần tử này KHÔNG rỗng sau .strip() nên trước
        # đây bị hiểu nhầm thành 1 "cảnh" giả (không có NARRATION: thật). Một
        # cảnh hợp lệ LUÔN bắt đầu bằng [SCENE] và LUÔN có dòng NARRATION: --
        # dùng đúng dấu hiệu này để lọc bỏ mọi block rác, thay vì giữ nguyên
        # mọi phần tử không rỗng như logic split thô trước đó.
        blocks = [b.strip() for b in raw.split("[SCENE]") if b.strip() and "NARRATION:" in b]
        for i, block in enumerate(blocks, start=1):
            narration_match = re.search(r"NARRATION:\s*(.+?)(?:\nMOTION:|\nIMAGE:|\nVIDEO:|\Z)", block, re.DOTALL)
            motion_match = re.search(r"MOTION:\s*(.+?)(?:\nIMAGE:|\nVIDEO:|\Z)", block, re.DOTALL)
            video_match = re.search(r"VIDEO:\s*(.+?)(?:\n|\Z)", block, re.DOTALL)
            narration = narration_match.group(1).strip() if narration_match else block.strip()
            motion_prompt = motion_match.group(1).strip() if motion_match else ""
            video_name = video_match.group(1).strip() if video_match else ""
            narration, ad_markers = _extract_ad_markers(narration)
            scenes.append(Scene(index=i, narration=narration, motion_prompt=motion_prompt, video_path=video_name, ad_markers=ad_markers))
    else:
        paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
        for i, para in enumerate(paragraphs, start=1):
            para, ad_markers = _extract_ad_markers(para)
            scenes.append(Scene(index=i, narration=para, ad_markers=ad_markers))

    if not scenes:
        raise ValueError("Không tách được cảnh nào từ kịch bản. Kiểm tra lại định dạng file input.")

    return scenes

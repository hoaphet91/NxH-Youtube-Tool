"""
Cấu hình trung tâm cho pipeline sinh video tự động.
Sửa các giá trị bên dưới để tuỳ chỉnh hành vi mà không cần đụng vào code chính.

PHIÊN BẢN NÀY: quay lại cách ghép ảnh tĩnh -> video kiểu "Ken Burns" (pan/zoom
camera ảo trên ảnh tĩnh), KHÔNG còn dùng Wan2.1/ComfyUI để animate ảnh nữa.
Không cần GPU, không cần cài ComfyUI.
"""
import os
from dotenv import load_dotenv

# QUAN TRỌNG: chỉ định rõ đường dẫn .env nằm CẠNH file config.py này, để load_dotenv()
# luôn tìm đúng file dù bạn chạy "python main.py" từ thư mục nào trên máy.
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=_ENV_PATH)

# ============ PROVIDER LỰA CHỌN ============
# TTS_PROVIDER: "elevenlabs" | "openai" | "edge" (edge-tts của Microsoft, MIỄN PHÍ,
# không cần API key, chạy qua CLI "edge-tts" -- cần cài: pip install edge-tts)
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")

# ============ API KEYS (đọc từ .env) ============
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ============ EDGE-TTS (chỉ dùng khi TTS_PROVIDER="edge") ============
# Chạy "edge-tts --list-voices" để xem toàn bộ giọng khả dụng.
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AndrewNeural")
# Tốc độ đọc, dạng chuỗi phần trăm có dấu +/-, vd "-15%", "+10%".
EDGE_TTS_RATE = os.getenv("EDGE_TTS_RATE", "-15%")
# Cao độ giọng, dạng chuỗi Hz có dấu +/-, vd "-10Hz", "+5Hz".
EDGE_TTS_PITCH = os.getenv("EDGE_TTS_PITCH", "-15Hz")

# ============ NHẠC NỀN (1 file cố định do người dùng tự chọn, xuyên suốt video) ============
# QUAN TRỌNG [thay thế cơ chế Freesound cũ]: KHÔNG còn tải nhạc theo sound ID
# từ Freesound.org theo dòng MUSIC: trong kịch bản nữa. Giờ chỉ dùng ĐÚNG 1
# file nhạc nền cố định, do bạn tự chọn/tải sẵn, áp dụng XUYÊN SUỐT toàn bộ
# video (mọi cảnh dùng chung 1 track, không đổi nhạc theo cảnh/đoạn nữa) --
# xem modules/music_engine.py.
# Bật/tắt tính năng nhạc nền. Đặt false -> bỏ qua hoàn toàn, video không có
# nhạc nền (chỉ giọng đọc).
MUSIC_ENABLED = os.getenv("MUSIC_ENABLED", "true").lower() == "true"
# Đường dẫn tới file nhạc nền cố định (.mp3/.wav/.m4a...). Có thể override
# trong .env bằng biến BACKGROUND_MUSIC_PATH (đường dẫn tuyệt đối hoặc tương
# đối so với thư mục chạy pipeline). Mặc định trỏ vào assets/background_music.mp3
# -- tự bỏ file nhạc bạn chọn vào đúng đường dẫn này, hoặc set biến .env để
# trỏ tới nơi khác. Nếu để trống hoặc file không tồn tại, pipeline in cảnh
# báo và bỏ qua nhạc nền (không chặn pipeline).
BACKGROUND_MUSIC_PATH = os.getenv(
    "BACKGROUND_MUSIC_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "background_music.mp3"),
)
# Âm lượng nhạc nền so với giọng đọc TTS (0.0 - 1.0). Mặc định thấp để không
# lấn giọng đọc.
MUSIC_VOLUME = float(os.getenv("MUSIC_VOLUME", "0.15"))

# ============ THÔNG SỐ VIDEO ============
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30

# ============ BẬT/TẮT GỌI API TTS (tiết kiệm chi phí/token khi test) ============
# Đặt "false" trong .env để KHÔNG gọi API TTS thật (ElevenLabs/OpenAI) -> dùng
# audio có sẵn trong LOCAL_AUDIO_DIR thay thế, để test nhanh các bước còn lại
# (image_sync, subtitle_gen, video_compose, policy_check) mà không tốn phí API.
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
# Thư mục chứa audio có sẵn dùng khi TTS_ENABLED=false. Lưu ĐÚNG THỨ TỰ CẢNH
# (audio cảnh 1 lưu trước, cảnh 2 lưu sau, ...), tên file tuỳ ý -> tool tự sắp
# theo thời gian tạo file, giống cơ chế INPUT_IMAGES_DIR. Số file audio phải
# khớp chính xác số cảnh trong kịch bản. Hỗ trợ .mp3/.wav/.m4a.
LOCAL_AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input_audio")
 
# ============ ẢNH ĐẦU VÀO (người dùng tự tạo) ============
# Bạn tự tạo ảnh cho từng cảnh và LƯU LẦN LƯỢT ĐÚNG THỨ TỰ CẢNH vào thư mục này
# (tên file gốc tuỳ ý). modules/image_sync.py sẽ tự động đổi tên theo thời gian
# tạo file thành scene_001.<ext>, scene_002.<ext>, ... trước khi dựng video.
INPUT_IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input_images")

# ============ VIDEO DỰNG SẴN (thay ảnh tĩnh cho MỘT SỐ cảnh) ============
# Đặt file video (.mp4/.mov/.mkv) vào thư mục này. Trong kịch bản, dòng
# VIDEO: <tên_file> (xem modules/script_parser.py) chỉ định cảnh đó dùng
# video này thay vì ảnh tĩnh + Ken Burns. Tên file trong VIDEO: được ghép
# với thư mục này để ra đường dẫn đầy đủ -- xem modules/image_sync.py
# (_resolve_video_paths). Giọng đọc TTS narration LUÔN là audio chính của
# cảnh; audio GỐC của video (nếu có) không còn bị tắt hoàn toàn nữa mà được
# TRỘN vào với âm lượng nhỏ hơn -- xem VIDEO_ORIGINAL_AUDIO_VOLUME ngay dưới.
INPUT_VIDEOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "input_videos")

# Âm lượng audio GỐC của video dựng sẵn (field VIDEO:) khi trộn (mix) cùng
# giọng đọc TTS narration. 0.0 = tắt hẳn (giữ hành vi cũ, chỉ có TTS).
# 1.0 = to ngang giọng đọc. Mặc định 0.3 (giữ chút tiếng động hiện trường,
# không lấn át lời thoại). Nếu video không có audio track, tự động bỏ qua,
# không cần chỉnh gì thêm.
VIDEO_ORIGINAL_AUDIO_VOLUME = float(os.getenv("VIDEO_ORIGINAL_AUDIO_VOLUME", "0.3"))

# Độ dài chuẩn (giây) của MỖI video dựng sẵn (field VIDEO:) mà bạn tự tạo để
# đưa vào input_videos/. video_compose.py dùng giá trị này làm mốc so sánh:
# nếu scene.duration (đo từ audio TTS thật) LỆCH quá SCENE_VIDEO_DURATION_
# WARN_THRESHOLD giây so với SCENE_VIDEO_DURATION, in cảnh báo ra console để
# bạn biết mà chỉnh lại narration/video (không chặn pipeline). Video KHÔNG
# còn bị loop nữa (mỗi video chỉ phát đúng 1 lần từ đầu) -- nếu scene.duration
# dài hơn SCENE_VIDEO_DURATION, phần dư sẽ là màn hình đứng yên ở frame cuối
# cùng của video (do ffmpeg tự giữ frame cuối khi hết input); nếu ngắn hơn,
# video bị cắt bớt cho khớp scene.duration.
SCENE_VIDEO_DURATION = float(os.getenv("SCENE_VIDEO_DURATION", "8.0"))
# Sai lệch tối đa (giây) giữa scene.duration (TTS) và SCENE_VIDEO_DURATION
# trước khi in cảnh báo. Mặc định 1.0 giây.
SCENE_VIDEO_DURATION_WARN_THRESHOLD = float(os.getenv("SCENE_VIDEO_DURATION_WARN_THRESHOLD", "1.0"))

# ============ HIỆU ỨNG KEN BURNS (pan/zoom trên ảnh tĩnh) ============
# EFFECT_SELECTION_MODE: "ai" (gọi GPT chọn hiệu ứng hợp lý theo nội dung cảnh,
# cần OPENAI_API_KEY) hoặc "heuristic" (chọn theo từ khoá, miễn phí, không cần API).
EFFECT_SELECTION_MODE = os.getenv("EFFECT_SELECTION_MODE", "heuristic")

# Tỉ lệ "phóng to dự phòng" so với khung hình đích, tạo không gian dư để pan/zoom
# mà không lộ viền đen. 1.15 = ảnh nền được phóng to thêm 15%.
KEN_BURNS_ZOOM_RATIO = float(os.getenv("KEN_BURNS_ZOOM_RATIO", "1.15"))

# ============ CHUYỂN CẢNH ============
# Thời gian chuyển cảnh giữa 2 cảnh liên tiếp (giây). Đặt 0 để cắt cứng, không hoà tan.
TRANSITION_DURATION = 0.6

# Khoảng lặng (giây) được CHÈN THẬT vào cuối audio mỗi cảnh (trừ cảnh cuối cùng),
# để 2 câu thoại liền nhau không bị dính sát/dồn dập. Vì đây là silence thật
# (không phải chỉ fade), scene.duration đo được sau bước TTS đã bao gồm khoảng
# lặng này -> subtitle_gen.py và video_compose.py tự động nhất quán theo,
# không cần sửa logic riêng ở 2 module đó.
SCENE_AUDIO_GAP = float(os.getenv("SCENE_AUDIO_GAP", "0.95"))

# ============ WHISPER (dùng để lấy timestamp thật cho phụ đề, modules/subtitle_gen.py) ============
# WHISPER_MODEL_SIZE: "tiny"/"base"/"small"/"medium"/"large-v3". "small" cân
# bằng tốc độ/độ chính xác, chạy tốt trên CPU lẫn GPU 12GB VRAM.
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
# WHISPER_DEVICE: "cpu" hoặc "cuda" (GPU NVIDIA).
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
# WHISPER_COMPUTE_TYPE: "int8" (nhanh, ít RAM/VRAM, dùng cho CPU hoặc GPU yếu)
# hoặc "float16" (chính xác hơn, cần GPU hỗ trợ).
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
# WHISPER_LANGUAGE: mã ngôn ngữ ISO-639-1 của giọng đọc TTS (vd "en" cho tiếng
# Anh, "vi" cho tiếng Việt). PHẢI khớp với ngôn ngữ thật của narration/giọng TTS
# (config.EDGE_TTS_VOICE...) -- đặt sai ngôn ngữ khiến whisper vừa CHẬM hơn
# nhiều (decoder phải vật lộn ép âm thanh vào ngôn ngữ sai) vừa cho timestamp
# kém chính xác hơn. Mặc định "en" vì kịch bản/giọng TTS hiện tại của pipeline
# (prehistoric-humans-script-SKILL-US.md, EDGE_TTS_VOICE mặc định
# en-US-AndrewNeural) đều là tiếng Anh.
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")

# TRANSITION_STYLE: "crossfade" (2 cảnh hoà tan chồng lên nhau, mượt & liền mạch)
# hoặc "fade_black" (mỗi cảnh fade ra/vào qua nền đen, dứt khoát hơn).
TRANSITION_STYLE = os.getenv("TRANSITION_STYLE", "crossfade")

# Tốc độ đọc trung bình để ước lượng thời lượng nếu cần (từ/giây), dùng cho fallback
WORDS_PER_SECOND = 2.5

# ============ ĐƯỜNG DẪN ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# ============ CÔNG BỐ AI-GENERATED / ALTERED CONTENT ============
# Đặt True nếu ẢNH GỐC (do bạn tự cung cấp) được tạo ra bằng AI (Midjourney,
# DALL-E, Google AI Studio, ComfyUI...). Hiệu ứng Ken Burns (pan/zoom) tự nó
# KHÔNG phải AI -> chỉ cần công bố "Altered content"/AI-generated nếu bản thân
# ẢNH là do AI tạo ra, không phải vì có dùng hiệu ứng pan/zoom.
IMAGES_ARE_AI_GENERATED = os.getenv("IMAGES_ARE_AI_GENERATED", "false").lower() == "true"

# ============ THÊM VÀO config.py — ĐẶT SAU PHẦN "THÔNG SỐ VIDEO" HIỆN CÓ ============
# (giữ nguyên VIDEO_WIDTH/VIDEO_HEIGHT/VIDEO_FPS đã có, chỉ thêm khối dưới đây)

# ============ ENCODER (CPU/GPU) — dùng cho cả render Ken Burns lẫn encode cuối ============
# VIDEO_CODEC: "h264_nvenc" (mặc định, dùng GPU NVIDIA qua NVENC, nhanh hơn
# nhiều lần so với CPU) hoặc "libx264" (CPU, dùng khi máy không có GPU NVIDIA
# hoặc ffmpeg không build kèm nvenc).
VIDEO_ENCODER = os.getenv("VIDEO_ENCODER", "h264_nvenc")

# --- Dùng khi VIDEO_ENCODER = "h264_nvenc" (GPU NVIDIA) ---
# VIDEO_NVENC_PRESET: p1 (nhanh nhất/nén kém nhất) .. p7 (chậm nhất/nén tốt nhất).
VIDEO_NVENC_PRESET = os.getenv("VIDEO_NVENC_PRESET", "p5")
# VIDEO_CQ: chất lượng NVENC, số càng THẤP càng nét (file càng nặng). 18 là mức khá cao.
VIDEO_CQ = int(os.getenv("VIDEO_CQ", "18"))

# --- Dùng khi VIDEO_ENCODER = "libx264" (CPU, fallback khi máy không có GPU NVIDIA) ---
VIDEO_PRESET = os.getenv("VIDEO_PRESET", "medium")
VIDEO_CRF = int(os.getenv("VIDEO_CRF", "18"))

# ============ CHIA BATCH KHI GHÉP VIDEO (modules/video_compose.py) ============
# Với kịch bản nhiều cảnh (vd 100-150+), gộp TOÀN BỘ video vào 1 lệnh ffmpeg
# duy nhất có thể vượt giới hạn độ dài dòng lệnh của Windows (lỗi "WinError 206:
# filename or extension is too long"). Từ [2026-07-15], video_compose.py tự
# động chia kịch bản thành nhiều "batch" tối đa VIDEO_COMPOSE_BATCH_SIZE cảnh/
# batch, render riêng từng batch rồi nối bằng concat demuxer (stream copy,
# không encode lại lần 2, không mất chất lượng). Ranh giới GIỮA các batch là
# CẮT CỨNG (không hoà tan/crossfade); bên TRONG mỗi batch vẫn hoà tan như cũ.
# Giảm số này (vd 15-20) nếu vẫn gặp lỗi "filename or extension is too long"
# với kịch bản có nhiều cảnh dùng VIDEO: (input nặng hơn cảnh dùng ảnh).
VIDEO_COMPOSE_BATCH_SIZE = int(os.getenv("VIDEO_COMPOSE_BATCH_SIZE", "25"))

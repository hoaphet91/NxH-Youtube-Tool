# Pipeline Sinh Video Tự Động Từ Kịch Bản (Ken Burns)

Tool Python chạy local, biến 1 file kịch bản text + ảnh tĩnh do bạn tự chuẩn bị
thành video hoàn chỉnh (giọng đọc AI + ảnh được dựng thành video bằng hiệu ứng
"Ken Burns" pan/zoom + phụ đề), kèm rà soát tự động theo checklist tuân thủ
YouTube.

**GPU không bắt buộc.** Mặc định `config.py` dùng GPU NVIDIA (`h264_nvenc`) để
encode nhanh hơn, nhưng có fallback CPU đầy đủ (`VIDEO_ENCODER=libx264` trong
`.env`) cho máy không có GPU NVIDIA. **Không cần ComfyUI/Wan2.1** dù chọn
encoder nào — đây là bản rút gọn từ pipeline animate-bằng-AI cũ, video được
dựng bằng kỹ thuật dựng phim truyền thống (camera ảo pan/zoom trên ảnh tĩnh),
không phải AI tạo chuyển động.

**Pipeline KHÔNG tự sinh ảnh AI.** Bạn tự tạo ảnh cho từng cảnh (vẽ tay,
Midjourney, Google AI Studio, chụp ảnh...) rồi lưu vào thư mục `input_images/`.

## Cài đặt

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Không cần cài ImageMagick — phụ đề được render bằng Pillow.

## Cấu hình API keys

```bash
cp .env.example .env
```

Mở `.env` và điền:
- `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` (nếu dùng ElevenLabs cho TTS)
- `OPENAI_API_KEY` (nếu dùng OpenAI TTS, hoặc `EFFECT_SELECTION_MODE=ai`)
- `FREESOUND_API_KEY` (tuỳ chọn, nếu kịch bản có dùng field `MUSIC:` để thêm
  nhạc nền — xem mục "Nhạc nền" bên dưới; lấy key miễn phí tại
  https://freesound.org/apiv2/apply/)

Trong `config.py` (hoặc qua biến môi trường trong `.env`), chọn provider TTS:
```python
TTS_PROVIDER = "elevenlabs"   # hoặc "openai"
```

## Chuẩn bị ảnh đầu vào (BẮT BUỘC, tự làm thủ công)

Pipeline không tự sinh ảnh. Tự tạo 1 ảnh tĩnh cho mỗi cảnh, đặt vào thư mục
`input_images/`.

**Cơ chế đặt tên ảnh: TỰ ĐỘNG theo thời gian tạo file.** Bạn KHÔNG cần tự đặt
tên file theo quy tắc `scene_001.png` — chỉ cần **lưu ảnh vào thư mục theo
đúng thứ tự cảnh** (ảnh cảnh 1 lưu trước, ảnh cảnh 2 lưu sau, ...), tên file
gốc tuỳ ý. Khi chạy pipeline, `modules/image_sync.py` sẽ:

1. Quét toàn bộ ảnh (.png/.jpg/.jpeg) trong `input_images/`
2. Sắp xếp theo thời gian tạo file (creation time)
3. Đối chiếu số ảnh với số cảnh trong kịch bản — báo lỗi ngay nếu lệch
4. Tự động đổi tên lần lượt thành `scene_001.<ext>`, `scene_002.<ext>`, ...
   và gán trực tiếp cho từng cảnh để dựng video

⚠️ **Lưu ý quan trọng:**
- Đây là ĐỔI TÊN THẬT trên ổ đĩa (không phải copy). Backup trước nếu muốn giữ tên gốc.
- Số lượng ảnh phải khớp CHÍNH XÁC số cảnh trong kịch bản.
- Trên Linux không có "creation time" thật, module dùng thời gian sửa đổi gần
  nhất (mtime) làm proxy — vẫn đúng thứ tự nếu bạn lưu ảnh tuần tự.

## Hiệu ứng Ken Burns (pan/zoom)

Mỗi cảnh được tự động gán 1 hiệu ứng camera ảo trong số **21 hiệu ứng**:

- **7 cơ bản**: `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `pan_up`, `pan_down`, `static`
- **8 kết hợp zoom + pan chéo** (hợp cảnh cao trào/kể chuyện): `zoom_in_pan_left`,
  `zoom_in_pan_right`, `zoom_in_pan_up`, `zoom_in_pan_down`, `zoom_out_pan_left`,
  `zoom_out_pan_right`, `zoom_out_pan_up`, `zoom_out_pan_down`
- **4 pan chéo góc-tới-góc** (hợp cảnh toàn cảnh rộng, cảm giác drone):
  `pan_diagonal_tl_br`, `pan_diagonal_tr_bl`, `pan_diagonal_bl_tr`, `pan_diagonal_br_tl`
- **2 "breathe"** (zoom vào rồi ra hoặc ngược lại trong cùng 1 cảnh, hợp
  khoảnh khắc cảm xúc lắng đọng): `zoom_in_out`, `zoom_out_in`

Chọn cách gán hiệu ứng qua `EFFECT_SELECTION_MODE` trong `.env`:
- `heuristic` (mặc định, miễn phí): chọn theo từ khoá trong narration + gợi ý `MOTION:`
- `ai`: gọi GPT (`OPENAI_API_KEY`) đọc nội dung cảnh và chọn hiệu ứng hợp lý hơn

Tuỳ chỉnh độ "dư không gian" cho pan/zoom qua `KEN_BURNS_ZOOM_RATIO` (mặc định `1.15`).

## Chạy thử

```bash
python main.py --script example_script.txt --title "Sapa buổi sáng sương mù"
```

Kết quả nằm trong thư mục `output/`:
- `final_video.mp4` — video hoàn chỉnh
- `subtitles.srt` — file phụ đề
- `report_<timestamp>.txt` — báo cáo policy check tự động

## Viết kịch bản đầu vào

2 định dạng được hỗ trợ:

**Cách 1 — đơn giản** (mỗi đoạn cách nhau dòng trống = 1 cảnh):
```
Lời thoại cảnh 1.

Lời thoại cảnh 2.
```

**Cách 2 — có cấu trúc** (khuyến nghị, hỗ trợ gợi ý hiệu ứng camera):
```
[SCENE]
NARRATION: Lời thoại của cảnh 1.
MOTION: pan sang trái, nhấn mạnh không gian rộng

[SCENE]
NARRATION: Lời thoại của cảnh 2.
```

Dòng `MOTION:` (tuỳ chọn) giờ là GỢI Ý chọn hiệu ứng Ken Burns cho
`effect_selector.py`, không còn là mô tả chuyển động nhân vật như bản Wan2.1 cũ.

Ảnh cho mỗi cảnh KHÔNG khai báo trong kịch bản — lưu trực tiếp vào
`input_images/` theo đúng thứ tự cảnh (xem phần trên).

### Field `VIDEO:` — dùng video dựng sẵn thay ảnh tĩnh cho một số cảnh

Nếu bạn đã có sẵn 1 đoạn video tự dựng cho 1 cảnh cụ thể (thay vì ảnh tĩnh +
Ken Burns), khai báo tên file (đặt trong `input_videos/`) qua dòng `VIDEO:`:

```
[SCENE]
NARRATION: Lời thoại của cảnh này.
VIDEO: canh_bien.mp4
```

- Một cảnh chỉ dùng 1 trong 2 field `IMAGE:`/`VIDEO:` (không dùng cả 2).
- Cảnh dùng `VIDEO:` KHÔNG cần ảnh trong `input_images/` — `image_sync.py` tự
  loại trừ cảnh này khỏi bước đối chiếu số ảnh/số cảnh.
- Giọng đọc TTS narration LUÔN là audio CHÍNH của cảnh. Audio gốc của video
  (nếu có) không bị tắt hoàn toàn mà được TRỘN vào với âm lượng nhỏ hơn theo
  `config.VIDEO_ORIGINAL_AUDIO_VOLUME` (mặc định 0.3; đặt 0 để tắt hẳn).
- Video không bị cắt/loop để cố khớp audio làm cơ chế chính — nên viết
  narration của cảnh đó dài tương đương ĐỘ DÀI VIDEO THẬT (khuyến nghị 6-8
  giây đọc) để hình và giọng đọc khớp nhau tự nhiên. Video ngắn/dài hơn vẫn
  tự động lặp lại hoặc bị cắt bớt cho khớp, nhưng đây chỉ là safety net.

### Field `MUSIC:` — nhạc nền tự động (Freesound.org)

Khai báo sound ID Freesound.org để thêm nhạc nền cho cảnh đó trở đi, tới khi
đổi/tắt:

```
[SCENE]
NARRATION: Lời thoại của cảnh này.
MUSIC: 125773
```

- Cảnh không khai báo `MUSIC:` TỰ KẾ THỪA sound ID của cảnh liền trước (không
  cần lặp lại ở mọi cảnh). Ghi `MUSIC: none` để tắt nhạc nền từ cảnh đó trở đi.
- Cần `config.MUSIC_ENABLED=true` (mặc định) + `FREESOUND_API_KEY` trong
  `.env`. Thiếu key hoặc lỗi tải nhạc KHÔNG chặn pipeline — cảnh đó chỉ đơn
  giản là không có nhạc nền.
- Âm lượng nhạc nền so với giọng đọc chỉnh qua `config.MUSIC_VOLUME` (mặc
  định 0.12, thấp để không lấn giọng đọc).

## Về công bố AI-generated / Altered content

Vì hiệu ứng Ken Burns (pan/zoom) là kỹ thuật dựng phim TRUYỀN THỐNG (không phải
AI), việc có cần bật "Altered content" khi đăng YouTube hay không giờ CHỈ phụ
thuộc vào việc ẢNH GỐC bạn cung cấp có phải do AI tạo ra hay không:

```python
IMAGES_ARE_AI_GENERATED = "false"  # đặt "true" trong .env nếu ảnh do AI tạo (Midjourney, DALL-E...)
```

## Về policy check tự động

Module `policy_check.py` chỉ là lớp lọc **heuristic** (dò từ khoá + vài quy tắc
đơn giản). Nó **không thay thế** việc bạn tự xem lại video, đặc biệt các mục
sau mà máy khó tự đánh giá chính xác:
- Bản quyền nhạc nền/asset (nếu bạn có thêm nhạc ngoài audio TTS)
- Bản quyền/nguồn gốc ảnh gốc bạn tự cung cấp
- Nudity/ngữ cảnh nhạy cảm trong ảnh
- Nội dung thumbnail (tool này chưa tạo thumbnail)
- Rủi ro "Inauthentic Content" — cần bạn tự đánh giá liệu video có đủ khác biệt
  thực chất so với các video trước trong kênh hay không, đây là rủi ro số 1.

## Cấu trúc thư mục

```
youtube_pipeline/
├── config.py              # cấu hình chung
├── main.py                 # CLI orchestrator, chạy pipeline 8 bước
├── example_script.txt      # kịch bản mẫu
├── list_elevenlabs_voices.py  # tiện ích liệt kê voice ElevenLabs khả dụng
├── input_images/            # BẠN tự lưu ảnh cho từng cảnh vào đây (tên tuỳ ý)
├── input_videos/             # video dựng sẵn cho cảnh dùng field VIDEO: (giữ tên file)
├── music_cache/               # cache nhạc nền đã tải theo sound ID (tự tạo)
├── .env.example
├── requirements.txt
├── modules/
│   ├── script_parser.py    # 1. tách kịch bản -> scenes
│   ├── tts_engine.py       # 2. TTS
│   ├── music_engine.py     # 2.5. tải/cache nhạc nền theo field MUSIC: (Freesound.org)
│   ├── image_sync.py       # 3. tự động đổi tên ảnh theo thời gian tạo -> scene_XXX
│   ├── effect_selector.py  # (gọi bởi video_compose) chọn 1 trong 21 hiệu ứng Ken Burns
│   ├── subtitle_gen.py     # 4. tạo .srt (word-level timestamp thật qua faster-whisper)
│   ├── video_compose.py    # 5. dựng video Ken Burns + video dựng sẵn + audio + nhạc nền + phụ đề
│   ├── policy_check.py     # 6. rà soát tự động
│   └── export.py           # 7. xuất báo cáo
└── output/                  # video + srt + report sẽ nằm ở đây
```

## Mở rộng gợi ý

- Sinh thumbnail tự động: dùng 1 khung hình đẹp từ video đã dựng, hoặc tự
  chụp/chọn ảnh riêng tỉ lệ 16:9, rồi tự kiểm theo checklist YouTube.
- Nếu muốn quay lại chế độ animate ảnh bằng AI (Wan2.1/ComfyUI) hoặc tự sinh
  ảnh AI (DALL-E/Gemini/ComfyUI SDXL), tham khảo phiên bản project trước đó.

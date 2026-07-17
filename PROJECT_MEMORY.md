# PROJECT MEMORY — Pipeline Sinh Video Tự Động Từ Kịch Bản (bản Ken Burns)

> File này là bản tóm tắt kiến trúc + quyết định thiết kế của dự án, dùng để AI đọc
> nhanh trong các phiên làm việc sau thay vì phải đọc lại toàn bộ source code.
> Cập nhật file này mỗi khi kiến trúc/luồng dữ liệu thay đổi (xem mục 10, QUY TẮC BẮT BUỘC).

## 0. Đây là gì, quan hệ với project cũ
Đây là bản **fork/rewrite** từ project pipeline animate-bằng-AI cũ (dùng Wan2.1
I2V qua ComfyUI). Project cũ không còn phù hợp nhu cầu (cần GPU mạnh, cài
ComfyUI phức tạp). Bản này quay lại cách làm "kiểu cũ hơn nữa": ghép ảnh tĩnh
thành video bằng hiệu ứng **Ken Burns** (pan/zoom camera ảo) — kỹ thuật dựng
phim truyền thống, không cần GPU/AI animate.

Cơ chế "người dùng tự tạo ảnh + tool tự đổi tên theo thời gian tạo" (đã làm ở
project trước) **được giữ nguyên và mang sang đây** (`modules/image_sync.py`).

## 1. Mục đích dự án
Tool Python chạy local, biến 1 file kịch bản (.txt) + ảnh tĩnh (người dùng tự
chuẩn bị, không cần đặt tên đặc biệt) thành 1 video hoàn chỉnh: giọng đọc AI
(TTS) + ảnh được dựng thành video bằng hiệu ứng Ken Burns + nhạc nền (tuỳ
chọn, Freesound.org) + phụ đề (.srt), kèm báo cáo rà soát tuân thủ chính sách
YouTube (heuristic).

**Không cần GPU (có fallback `libx264` chạy CPU qua `config.VIDEO_ENCODER`,
xem mục 5) — không cần ComfyUI/Wan2.1.**

## 2. Pipeline 8 bước (main.py orchestrate)
1. `script_parser.py` → tách kịch bản thành list `Scene`
2. `tts_engine.py` → sinh audio .mp3 cho từng scene (ElevenLabs hoặc OpenAI TTS),
   sau đó CHÈN THẬT khoảng lặng `config.SCENE_AUDIO_GAP` (mặc định 0.95s) vào
   cuối audio mọi cảnh TRỪ cảnh cuối cùng (dùng ffmpeg `apad`), rồi đo lại
   `scene.duration` theo file đã pad — xem mục 11, nhật ký [2026-07-11]
2.5. `music_engine.py` → nếu cảnh có khai báo `MUSIC:` (sound ID Freesound.org,
   kế thừa sang các cảnh sau tới khi đổi/tắt — xem `_apply_music_inheritance`
   trong `script_parser.py`), tải/cache file preview mp3 theo sound ID và gán
   vào `scene.music_path`. Bật/tắt qua `config.MUSIC_ENABLED`; thiếu
   `config.FREESOUND_API_KEY` hoặc lỗi tải → cảnh đó KHÔNG có nhạc nền,
   KHÔNG chặn pipeline. `video_compose.py` mix nhạc nền này vào audio cuối
   cùng ở âm lượng `config.MUSIC_VOLUME` — xem mục 6, nhật ký bổ sung ở mục 11.
3. `image_sync.py` → quét `input_images/`, sắp xếp theo **thời gian tạo file**
   (creation time; Linux dùng mtime làm proxy), đối chiếu số ảnh với số cảnh
   (lệch → raise lỗi), đổi tên thật (`os.rename` qua bước trung gian
   `__tmp_sync_*`) thành `scene_001.<ext>`... và **gán trực tiếp** vào
   `scene.image_path`. CHỈ áp dụng cho cảnh KHÔNG có `scene.video_path`
   (cảnh dùng field `VIDEO:` trong kịch bản) — module này cũng resolve luôn
   tên file trong `VIDEO:` thành đường dẫn đầy đủ (`config.INPUT_VIDEOS_DIR`)
   — xem mục 11, nhật ký [2026-07-11] "Video dựng sẵn thay ảnh tĩnh"
4. `subtitle_gen.py` → tạo .srt dựa trên WORD-LEVEL TIMESTAMP THẬT lấy từ
   faster-whisper (chạy local trên chính audio đã tạo), fallback về ước lượng
   theo tỉ lệ số từ nếu whisper lỗi (thiếu package, model tải lỗi, audio hỏng)
   — xem mục 11, nhật ký [2026-07-11]
5. `video_compose.py` → gọi `effect_selector.py` chọn hiệu ứng Ken Burns cho từng
   cảnh (đủ **21 hiệu ứng**, xem mục 4 + nhật ký [2026-07-13]). TOÀN BỘ việc
   sinh Ken Burns + ghép crossfade + burn phụ đề giờ chạy bằng ffmpeg
   (subprocess), KHÔNG còn moviepy/Pillow-per-frame nào (xem mục 4 + nhật ký
   2026-07-09 "bỏ hẳn moviepy"). Chế độ mặc định "crossfade": HÌNH ẢNH hoà
   tan thật (filter `xfade`), AUDIO nối liền tuần tự KHÔNG chồng lên nhau
   (filter `concat`+`afade`, xem mục 4 + nhật ký 2026-07-08). Phụ đề burn
   bằng filter `subtitles` (libass) → final_video.mp4. Cảnh có `scene.video_path`
   (field `VIDEO:` trong kịch bản) DÙNG VIDEO DỰNG SẴN thay ảnh tĩnh — KHÔNG áp
   Ken Burns, chỉ scale/crop kiểu "cover"; audio gốc của video (nếu có) KHÔNG
   bị tắt hoàn toàn mà được TRỘN (mix) vào cùng giọng đọc TTS với âm lượng nhỏ
   hơn theo `config.VIDEO_ORIGINAL_AUDIO_VOLUME` (giọng đọc TTS narration
   LUÔN là audio CHÍNH của cảnh) — xem mục 11, nhật ký [2026-07-11] "Video
   dựng sẵn thay ảnh tĩnh". Nếu có cảnh dùng `MUSIC:`, nhạc nền (đã tải ở bước
   2.5) cũng được mix vào ở bước này — track nhạc nền hoàn toàn tách biệt với
   logic narration/crossfade phía trên.
6. `policy_check.py` → rà soát heuristic (từ khoá) theo checklist YouTube
7. `export.py` → xuất report_<timestamp>.txt + in đường dẫn output cuối

Chạy: `python main.py --script example_script.txt --title "..."`

## 3. Cấu trúc Scene (script_parser.py)
```python
@dataclass
class Scene:
    index: int
    narration: str
    motion_prompt: str = ""   # dòng MOTION: trong kịch bản -> giờ là GỢI Ý hiệu
                               # ứng Ken Burns cho effect_selector (KHÔNG còn là
                               # mô tả chuyển động nhân vật Wan2.1 như trước)
    image_path: str = ""      # đường dẫn ảnh tĩnh, gán bởi image_sync.py
    video_path: str = ""      # dòng VIDEO: trong kịch bản (tên file, resolve
                               # thành đường dẫn đầy đủ bởi image_sync.py) --
                               # NẾU có giá trị, video_compose.py DÙNG VIDEO
                               # NÀY THAY ảnh tĩnh cho cảnh đó (không Ken Burns).
                               # Xem nhật ký [2026-07-11] "Video dựng sẵn thay
                               # ảnh tĩnh".
    effect: str = ""          # hiệu ứng Ken Burns được chọn, gán bởi effect_selector.py
                               # (bị bỏ qua nếu scene.video_path có giá trị)
    audio_path: str = ""
    duration: float = 0.0
    ad_markers: list[str] = field(default_factory=list)  # ***SPONSOR_BREAK***/***MIDROLL_BREAK*** tách khỏi
                               # narration (xem _extract_ad_markers, nhật ký [2026-07-12])
    music_id: str = ""        # sound ID Freesound.org (dòng MUSIC:, kế thừa từ cảnh trước nếu
                               # không khai báo lại -- xem _apply_music_inheritance)
    music_path: str = ""      # đường dẫn file nhạc nền đã tải, gán bởi modules/music_engine.py
                               # (rỗng nếu không có/lỗi tải -- xem mục 6)
```
Đã BỎ field `raw_video_path` cũ (không còn clip animate trung gian nữa) --
LƯU Ý: field `video_path` MỚI (thêm 2026-07-11) có TÊN GIỐNG nhưng Ý NGHĨA
HOÀN TOÀN KHÁC field `raw_video_path` đã bỏ trước đây. `raw_video_path` (cũ,
đã xoá) từng là clip animate TRUNG GIAN do Wan2.1/ComfyUI sinh ra tự động cho
MỌI cảnh. `video_path` (mới) là video NGƯỜI DÙNG TỰ CUNG CẤP cho MỘT SỐ cảnh
cụ thể, dùng THAY HẲN ảnh tĩnh + Ken Burns cho cảnh đó — không liên quan gì
đến kiến trúc animate-bằng-AI đã bị loại bỏ.

Định dạng kịch bản: 2 kiểu như cũ (đoạn cách dòng trống = 1 cảnh; hoặc
`[SCENE]`/`NARRATION:`/`MOTION:` có cấu trúc). Field `IMAGE:` ĐÃ ĐƯỢC DÙNG LẠI
trong thực tế bởi skill viết kịch bản (`tao-kich-ban-nguoi-tien-su-SKILL.md`)
để nhúng prompt tạo ảnh AI cho từng cảnh — `script_parser.py` nhận diện field
này CHỈ để làm ranh giới regex (kết thúc `MOTION:`), KHÔNG parse nội dung
thành field riêng của `Scene` (ghi chú "Không còn field IMAGE:" ở bản trước
đã lỗi thời, sửa lại ở đây). Field `VIDEO:` (mới, 2026-07-11) ĐƯỢC parse
thành `scene.video_path` — dùng cho cảnh có sẵn video dựng riêng, thay thế
`IMAGE:` ở cảnh đó (không dùng cả 2 field cùng lúc cho 1 cảnh).

## 4. Cơ chế Ken Burns (video_compose.py) — CHI TIẾT KỸ THUẬT QUAN TRỌNG
- `_prepare_padded_image()`: resize ảnh gốc kiểu "cover" (phủ kín khung hình,
  center-crop phần dư theo tỉ lệ khung hình đích), rồi phóng to thêm
  `KEN_BURNS_ZOOM_RATIO` (mặc định 1.15 = +15%) để có "dư" không gian pan/zoom
  mà KHÔNG BAO GIỜ lộ viền đen ở bất kỳ thời điểm nào trong clip.
- `_crop_filter_for_effect()`: build filter ffmpeg `crop=...,scale=...` theo
  biến `t`, hỗ trợ ĐỦ **21 hiệu ứng** (KHÔNG PHẢI 7 như các bản ghi chú cũ ở
  file này/README — xem nhật ký [2026-07-13] "Bổ sung 14 hiệu ứng Ken Burns
  còn thiếu"): 7 cơ bản (`zoom_in`/`zoom_out`/`pan_left`/`pan_right`/`pan_up`/
  `pan_down`/`static`) + 8 kết hợp zoom+pan chéo (`zoom_in_pan_left`...) + 4
  pan chéo góc-tới-góc (`pan_diagonal_tl_br`...) + 2 "breathe" (`zoom_in_out`,
  `zoom_out_in` — dùng tiến trình tam giác `1-abs(2p-1)` thay vì tuyến tính
  `p`, để zoom vào-rồi-ra hoặc ngược lại trong cùng 1 cảnh). Toàn bộ đều dùng
  chung 1 nguyên lý: crop window luôn nằm trong biên ảnh padded, không bao
  giờ lộ viền đen (đã verify bằng số cho cả 21 hiệu ứng tại t=0/giữa/cuối).
- Vì frame được sinh trực tiếp theo `t` bất kỳ trong khoảng `[0, duration]`,
  KHÔNG cần bước "fit video vào duration" (freeze-extend/cắt bớt) như bản
  Wan2.1 cũ — thời lượng luôn khớp chính xác audio ngay từ đầu.
- `effect_selector.py::AVAILABLE_EFFECTS` chứa đủ 21 tên hiệu ứng này (trước
  [2026-07-13] chỉ có 7 tên, nên chế độ `EFFECT_SELECTION_MODE=ai` không bao
  giờ chọn được 14 hiệu ứng còn lại dù `video_compose.py` khi đó cũng chưa
  implement chúng — cả 2 phía nay đã đồng bộ).
- Đã test logic sinh frame cho cả 7 hiệu ứng gốc (script test nhanh bằng ảnh giả
  800x600 -> luôn ra đúng shape 1920x1080 tại t=0/giữa/cuối). CHƯA test thực tế
  end-to-end với ảnh thật + audio thật + ghi file video (cần moviepy/ffmpeg
  đầy đủ, môi trường sandbox không có mạng để cài srt/moviepy lúc viết code này).
- CHUYỂN CẢNH (mặc định "crossfade", xem nhật ký 2026-07-08): hình ảnh và audio
  KHÔNG còn dùng chung 1 timeline dịch chuyển như bản đầu. Hình ảnh mỗi cảnh có
  thêm `pre_roll`/`post_roll` (mỗi bên `transition/2`, đóng băng khung hình đầu/
  cuối) làm vùng crossfade thị giác; audio mỗi cảnh giữ nguyên đúng thời lượng
  thật, nối liền bằng `concatenate_audioclips`, không dịch/chồng. Vì vậy tổng
  thời lượng video/audio cuối cùng = tổng thời lượng audio thật (không bị co
  ngắn theo số lần transition nữa).

## 5. Config quan trọng (config.py)
- `TTS_PROVIDER`: "elevenlabs" | "openai"
- `TTS_ENABLED`: bool (đọc từ `.env`, mặc định `true`). Đặt `false` để KHÔNG
  gọi API TTS thật -> dùng audio có sẵn trong `LOCAL_AUDIO_DIR` (mặc định
  `input_audio/`) để test, tiết kiệm chi phí/token (xem nhật ký 2026-07-08).
- `INPUT_IMAGES_DIR`: thư mục ảnh tĩnh đầu vào
- `INPUT_VIDEOS_DIR`: thư mục video dựng sẵn (mặc định `input_videos/`), dùng
  cho cảnh có field `VIDEO:` trong kịch bản — xem nhật ký [2026-07-11] "Video
  dựng sẵn thay ảnh tĩnh".
- `EFFECT_SELECTION_MODE`: "heuristic" (mặc định, free) | "ai" (cần OPENAI_API_KEY)
- `KEN_BURNS_ZOOM_RATIO`: default 1.15
- `TRANSITION_DURATION` + `TRANSITION_STYLE` ("crossfade" | "fade_black")
- `SCENE_AUDIO_GAP`: default **0.95** (giây) — khoảng lặng THẬT chèn vào cuối
  audio mỗi cảnh (trừ cảnh cuối) để tránh 2 câu thoại liền cảnh dính sát nhau.
  Đặt 0 để tắt hoàn toàn (giữ hành vi cũ). Xem nhật ký [2026-07-11] (giá trị
  ban đầu 0.35 đã được tăng lên 0.95 sau phản hồi thực tế; xem nhật ký
  [2026-07-13] "Đồng bộ hoá tài liệu").
- `MUSIC_ENABLED`/`FREESOUND_API_KEY`/`MUSIC_VOLUME`/`MUSIC_CACHE_DIR`: cấu
  hình nhạc nền cho `modules/music_engine.py` (xem mục 6). `MUSIC_ENABLED`
  mặc định `true`; thiếu `FREESOUND_API_KEY` hoặc lỗi tải nhạc không chặn
  pipeline, chỉ khiến cảnh đó không có nhạc nền. `MUSIC_VOLUME` mặc định 0.12
  (thấp để không lấn giọng đọc).
- `VIDEO_ORIGINAL_AUDIO_VOLUME`: default 0.3 — âm lượng audio GỐC của video
  dựng sẵn (field `VIDEO:`) khi TRỘN (mix) cùng giọng đọc TTS. Đặt 0 để tắt
  hẳn audio gốc (KHÔNG phải mặc định — bản ghi chú cũ ở mục 2/11 nói audio
  gốc "luôn bị tắt" đã lỗi thời, xem nhật ký [2026-07-13]).
- `SCENE_VIDEO_DURATION`: default **8.0** (giây) — độ dài chuẩn của MỖI video
  dựng sẵn (field `VIDEO:`) mà người dùng tự tạo. Từ nhật ký [2026-07-14],
  video KHÔNG còn bị loop nữa (đã bỏ `-stream_loop -1`) — mỗi video chỉ phát
  ĐÚNG 1 LẦN, dùng filter `tpad` (stop_mode=clone) để giữ nguyên (đứng yên)
  frame cuối nếu `scene.duration` (đo từ audio TTS thật) dài hơn video, hoặc
  cắt bớt nếu ngắn hơn. `SCENE_VIDEO_DURATION_WARN_THRESHOLD` (default 1.0
  giây) là ngưỡng sai lệch trước khi `video_compose.py` in cảnh báo ra console
  (không chặn pipeline) nhắc người dùng chỉnh lại narration cho khớp.
- `WHISPER_MODEL_SIZE`/`WHISPER_DEVICE`/`WHISPER_COMPUTE_TYPE`: cấu hình
  faster-whisper dùng trong `subtitle_gen.py` để lấy timestamp thật cho phụ đề.
  Mặc định "small"/"cpu"/"int8". Xem nhật ký [2026-07-11].
- `VIDEO_WIDTH/HEIGHT/FPS`: 1920x1080@30
- `IMAGES_ARE_AI_GENERATED`: bool (đọc từ .env dạng string "true"/"false") — THAY
  THẾ `IMAGES_ARE_PHOTOREALISTIC` cũ. Quyết định có cần bật "Altered content"
  khi đăng YouTube hay không. Ken Burns KHÔNG phải AI nên logic công bố giờ
  CHỈ phụ thuộc ảnh gốc có phải AI-generated hay không, không phải vì có dùng
  hiệu ứng pan/zoom.
- API keys đọc từ `.env`: `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `OPENAI_API_KEY`,
  `FREESOUND_API_KEY`
- ĐÃ XOÁ toàn bộ config Wan2.1/ComfyUI (`COMFYUI_URL`, `WAN21_*`)
- `VIDEO_ENCODER`: "h264_nvenc" (mặc định, GPU NVIDIA) | "libx264" (CPU, fallback
  khi máy không có GPU NVIDIA hoặc ffmpeg không build kèm nvenc). Khi
  `h264_nvenc`: dùng thêm `VIDEO_NVENC_PRESET` (mặc định "p5") + `VIDEO_CQ`
  (mặc định 18). Khi `libx264`: dùng `VIDEO_PRESET` (mặc định "medium") +
  `VIDEO_CRF` (mặc định 18). Thay thế hoàn toàn `VIDEO_CODEC`/`VIDEO_QUALITY`/
  `VIDEO_ENCODE_PARAMS` cũ (xem nhật ký 2026-07-09 "bỏ hẳn moviepy").

## 6. Modules trong project (tất cả đều ĐANG DÙNG, không còn module legacy)
- `main.py`, `config.py`
- `modules/script_parser.py`, `modules/tts_engine.py`, `modules/music_engine.py`,
  `modules/image_sync.py`, `modules/effect_selector.py`, `modules/subtitle_gen.py`,
  `modules/video_compose.py`, `modules/policy_check.py`, `modules/export.py`
- `list_elevenlabs_voices.py` (tiện ích độc lập, không đổi)

`modules/music_engine.py` (bước 2.5/8, xem mục 2): tải nhạc nền theo sound ID
Freesound.org (`scene.music_id`, parse ở `script_parser.py`), cache theo
sound_id trong `config.MUSIC_CACHE_DIR`, gán `scene.music_path` để
`video_compose.py` mix vào audio cuối cùng. Module này đã tồn tại và hoạt
động trong project TỪ LÂU nhưng bị bỏ sót khỏi danh sách module + pipeline
steps ở các bản trước của file này — xem nhật ký [2026-07-13] "Đồng bộ hoá
tài liệu" để biết lý do bổ sung hồi tố.

**KHÔNG mang sang project này**: `image_gen.py` (sinh ảnh AI qua DALL-E/Gemini/
ComfyUI-SDXL/Krea2/Midjourney) — vì user tự cung cấp ảnh, module này không cần
thiết trong scope hiện tại. `image_to_video.py` (Wan2.1 I2V qua ComfyUI) — đã bị
loại bỏ hoàn toàn, thay bằng Ken Burns trong `video_compose.py`.

## 7. Các quyết định thiết kế đáng chú ý
- `effect_selector.py`: bản gốc (project cũ) có bug tham chiếu `scene.image_prompt`
  — field này KHÔNG tồn tại trong `Scene` hiện tại. Đã sửa: dùng
  `scene.narration + scene.motion_prompt` làm nguồn văn bản chọn hiệu ứng.
- Phụ đề: Pillow (ImageDraw + TrueType font), không cần ImageMagick.
- Policy check: rủi ro lớn nhất vẫn là "Inauthentic Content" (pipeline tự động
  hoá theo khuôn mẫu cố định).
- Toàn bộ code + comment + docstring viết bằng tiếng Việt.

## 8. Việc cần làm thủ công trước khi chạy
- Tạo `.env` từ `.env.example`, điền API key
- Tự tạo ảnh tĩnh cho mỗi cảnh, LƯU LẦN LƯỢT ĐÚNG THỨ TỰ CẢNH vào `input_images/`
  (tên file tuỳ ý — không cần `scene_001.png` nữa)
- `pip install -r requirements.txt` (không cần GPU/ComfyUI nữa — điểm khác biệt
  lớn nhất so với project cũ)
- Tự kiểm tra thủ công: bản quyền nhạc nền, thumbnail, bản quyền ảnh gốc, rủi
  ro Inauthentic Content

## 9. Gợi ý câu hỏi cần hỏi user khi tiếp tục dự án
- Đang muốn sửa/thêm tính năng ở bước nào trong 7 bước?
- Đã test chạy thực tế end-to-end (ảnh thật + audio thật + xuất video) chưa?
  Nếu có lỗi, lỗi nằm ở bước nào?
- Có cần thêm hiệu ứng Ken Burns mới ngoài 21 hiệu ứng hiện có không?
- Có cần tính năng mix nhạc nền (chưa làm, chỉ mới gợi ý trong README) không?

## 10. QUY TẮC BẮT BUỘC — Cập nhật file memory này
Mỗi khi chỉnh sửa code, thêm/xoá file quan trọng, hoặc thay đổi luồng dữ liệu/kiến
trúc, **PHẢI cập nhật lại file `PROJECT_MEMORY.md` này**:
- Việc gì đã làm (đã sửa file nào, thay đổi logic gì, đã thêm module mới nào)
- Việc gì đang dở/còn cần làm tiếp (TODO, bug chưa fix, tính năng chưa hoàn thiện)
- Có thay đổi nào làm phần mô tả cũ trong file này bị lỗi thời không → sửa luôn
  phần tương ứng ở mục 2-8, đừng chỉ thêm cuối file gây trùng lặp/mâu thuẫn.

Format entry mới trong mục 11:
```
### [YYYY-MM-DD] Tóm tắt ngắn gọn thay đổi
- Đã làm: ...
- File liên quan: ...
- Còn cần làm / lưu ý cho lần sau: ...
```

## 11. Nhật ký thay đổi

### [2026-07-08] Thêm tuỳ chọn TẮT/BẬT gọi API TTS thật (test bằng audio có sẵn)
- Đã làm: Thêm `config.TTS_ENABLED` (đọc từ `.env`, mặc định `true`) và
  `config.LOCAL_AUDIO_DIR` (mặc định `input_audio/` cạnh `config.py`). Khi
  `TTS_ENABLED=false`, `tts_engine.generate_audio_for_scenes()` KHÔNG gọi API
  ElevenLabs/OpenAI nữa mà gọi `_sync_local_audio_for_scenes()`: quét
  `LOCAL_AUDIO_DIR` (.mp3/.wav/.m4a), sắp theo thời gian tạo file (logic giống
  hệt `image_sync.py`), đối chiếu số file với số cảnh (lệch -> raise lỗi), rồi
  COPY (không rename, giữ nguyên file gốc để tái dùng nhiều lần test) vào
  `work_dir/audio/scene_XXX.<ext>` và gán `scene.audio_path` + `scene.duration`
  (đo bằng `mediainfo`, cùng cơ chế TTS thật). `main.py._check_env_or_die()`
  cập nhật: bỏ qua kiểm tra ELEVENLABS/OPENAI key khi `TTS_ENABLED=false`, thay
  bằng kiểm tra `LOCAL_AUDIO_DIR` có tồn tại không.
- File liên quan: `config.py` (thêm `TTS_ENABLED`, `LOCAL_AUDIO_DIR`),
  `modules/tts_engine.py` (thêm `_get_creation_time`, `_sync_local_audio_for_scenes`,
  sửa `generate_audio_for_scenes`), `main.py` (sửa `_check_env_or_die`, cập
  nhật docstring bước 2).
- Còn cần làm / lưu ý cho lần sau:
  - Cần thêm dòng `TTS_ENABLED=false` (hoặc `true`) vào `.env.example` nếu
    muốn người dùng mới thấy tuỳ chọn này ngay từ đầu (file `.env.example`
    không có trong scope chỉnh sửa lần này, cần tự thêm tay).
  - Thư mục `input_audio/` cần được tạo và bỏ audio test vào TRƯỚC khi chạy
    với `TTS_ENABLED=false`, số file phải khớp chính xác số cảnh trong kịch
    bản (giống quy tắc `input_images/`).
  - Vì audio test có thể không phải giọng đọc tiếng Việt/khớp nội dung thật,
    `subtitle_gen.py` vẫn tách phụ đề dựa theo NARRATION text + thời lượng
    audio thật đo được -> phụ đề vẫn đúng thời gian dù nội dung audio test
    không khớp lời thoại, phù hợp mục đích test luồng dựng video/hiệu ứng.

### [2026-07-08] Sửa bug audio chồng lên nhau khi chuyển cảnh (crossfade)
- Đã làm: `_compose_crossfade` cũ trong `video_compose.py` dịch audio của cảnh
  sau sớm hơn `transition` giây rồi audio_fadein/fadeout chồng lên audio cảnh
  trước -> 2 giọng đọc phát chồng nhau, nghe giật/mất tự nhiên. Viết lại thành
  `_compose_crossfade_synced`: HÌNH ẢNH vẫn hoà tan (crossfade) mượt bằng cách
  thêm pre_roll/post_roll (khung hình đóng băng ở rìa mỗi cảnh, mỗi bên
  `transition/2`) làm vùng overlap chỉ cho hình; AUDIO nối liền tuần tự bằng
  `concatenate_audioclips` (chỉ fade 0.03s để tránh tiếng click, không phải
  crossfade thật) -> không còn chồng giọng đọc. Do đó tổng thời lượng
  video/audio giờ LUÔN bằng đúng tổng thời lượng audio thật (không còn bị co
  ngắn theo `(n-1)*transition` như bản cũ). Đồng bộ lại `subtitle_gen.py`:
  bỏ tham số `transition`, mốc phụ đề = tổng dồn thời lượng audio thật, không
  trừ transition nữa (khớp với timeline audio/hình mới). `compose_video()`
  trong `video_compose.py` cũng sửa 1 bug phụ: biến `clips` chỉ được gán ở
  nhánh `else` (fade_black/không transition) nhưng bước cleanup cuối hàm luôn
  gọi `c.close()` trên nó -> NameError ở nhánh crossfade (nhánh mặc định).
  Đã khởi tạo `clips = []` mặc định trước if/else để tránh lỗi này.
- File liên quan: `modules/video_compose.py` (thêm `_build_scene_video_clip`,
  `_compose_crossfade_synced`, sửa `compose_video`), `modules/subtitle_gen.py`
  (đổi signature `generate_srt(scenes, work_dir)`, bỏ tham số `transition`),
  `main.py` (sửa lời gọi `generate_srt`).
- Còn cần làm / lưu ý cho lần sau:
  - Chế độ `fade_black` (`TRANSITION_STYLE=fade_black`) vốn đã không bị lỗi
    chồng audio (dùng `concatenate_videoclips` tuần tự thật sự) nên GIỮ
    NGUYÊN logic cũ, không đổi.
  - Chưa test thực tế bằng ffmpeg/audio thật cho nhánh crossfade mới (mới sửa
    logic, môi trường viết code không có mạng để cài đủ dependency chạy thử).
    Lần chạy thật đầu tiên nên nghe kỹ đoạn chuyển cảnh xem còn tiếng click
    nhỏ ở mối nối audio hay không (nếu có, tăng `click_fade` trong
    `_compose_crossfade_synced` lên, ví dụ 0.05–0.08s).
  - `KEN_BURNS_ZOOM_RATIO` mặc định 1.15 vẫn đủ dùng cho pre_roll/post_roll
    đóng băng (vì đó chỉ là giữ nguyên khung hình đầu/cuối, không cần thêm
    không gian pan/zoom mới).

### [2026-07-08] Fork project: bỏ Wan2.1/ComfyUI, chuyển sang Ken Burns
- Đã làm: Viết lại toàn bộ project từ project Wan2.1 cũ. Xoá hoàn toàn phụ
  thuộc GPU/ComfyUI/Wan2.1. `video_compose.py` viết lại từ đầu để tự sinh video
  Ken Burns (pan/zoom) trực tiếp từ ảnh tĩnh, không qua bước "animate clip"
  trung gian. `effect_selector.py` được đưa từ trạng thái "module rời/không
  dùng" sang "module chính, được `video_compose.py` gọi trực tiếp", đồng thời
  sửa bug tham chiếu field `image_prompt` không tồn tại. `image_sync.py` được
  refactor nhận `scenes` trực tiếp (thay vì `num_scenes`) để gán luôn
  `scene.image_path` trong cùng 1 bước.
- File liên quan: TẤT CẢ file trong project này là mới/viết lại (main.py,
  config.py, modules/script_parser.py, modules/tts_engine.py,
  modules/image_sync.py, modules/effect_selector.py, modules/subtitle_gen.py,
  modules/video_compose.py, modules/policy_check.py, modules/export.py,
  README.md, requirements.txt, .env.example). Không mang sang: image_gen.py,
  image_to_video.py (loại bỏ khỏi scope).
- Còn cần làm / lưu ý cho lần sau:
  - CHƯA test end-to-end thực tế (ảnh thật + TTS thật + ffmpeg ghi file) — mới
    chỉ test logic sinh frame Ken Burns bằng ảnh giả (stub moviepy/srt do sandbox
    không có mạng để cài lúc viết code). Lần chạy thật đầu tiên nên theo dõi kỹ
    log ở bước [5/7] video_compose.
  - `requirements.txt` ghi `moviepy==1.0.3` — nếu môi trường thật cài bản khác,
    kiểm tra lại API `VideoClip`/`CompositeVideoClip` có đổi signature không.
  - Font phụ đề: `_load_font()` chỉ thử 3 đường dẫn cứng (Windows/Linux DejaVu).
    Nếu chạy trên macOS hoặc Linux distro khác không có các font đó, sẽ rơi về
    `ImageFont.load_default()` (font rất nhỏ/xấu) — có thể cần thêm đường dẫn
    font khác hoặc cho phép cấu hình qua config.
[2026-07-09] Chuyển Ken Burns từ Python/PIL sang ffmpeg (zoompan) + encode GPU NVENC


Đã làm: Viết lại modules/video_compose.py. XOÁ toàn bộ cách sinh frame Ken
Burns bằng Python (_prepare_padded_image, _make_ken_burns_frame_fn,
_build_scene_clip, _build_scene_video_clip cũ) — đây là bottleneck lớn
nhất của pipeline (đặc biệt zoom_in/zoom_out phải gọi Image.resize(LANCZOS)
gần như MỌI frame bằng CPU đơn luồng). Thay bằng hàm mới
_render_scene_clip_ffmpeg(): gọi ffmpeg (subprocess) dựng video Ken Burns
cho từng cảnh bằng filter zoompan (chạy code C tối ưu, không phải vòng lặp
Python) + tpad (start_mode/stop_mode=clone) để tạo freeze-frame
pre_roll/post_roll cho crossfade — về hành vi, tpad clone TƯƠNG ĐƯƠNG chính
xác cách clamp t cũ. Encode (cả clip từng cảnh lẫn video cuối) đổi từ
libx264 (CPU) sang h264_nvenc (GPU NVIDIA), cấu hình qua
config.VIDEO_CODEC/VIDEO_QUALITY/VIDEO_PRESET/VIDEO_ENCODE_PARAMS
(mới thêm vào config.py).
TOÀN BỘ logic crossfade (hoà tan hình, audio nối liền không chồng — xem mục
4 + nhật ký 2026-07-08) và logic burn phụ đề bằng Pillow GIỮ NGUYÊN 100%,
không đổi hành vi — chỉ đổi nguồn clip từng cảnh từ "VideoClip sinh bằng
Python" sang "file .mp4 do ffmpeg dựng sẵn" rồi nạp lại bằng
VideoFileClip.
File liên quan: modules/video_compose.py (viết lại phần Ken Burns + encode),
config.py (thêm VIDEO_CODEC, VIDEO_QUALITY, VIDEO_PRESET,
VIDEO_ENCODE_PARAMS).
Còn cần làm / lưu ý cho lần sau:

Cần ffmpeg build có h264_nvenc (đã xác nhận build gyan.dev full trên máy
dev có kèm). Nếu chạy trên máy khác không có GPU NVIDIA hoặc ffmpeg không
build kèm nvenc, đặt VIDEO_CODEC=libx264 trong .env để rơi về CPU an
toàn (chỉ chậm hơn, không lỗi).
_get_ffmpeg_exe() ưu tiên ffmpeg trong PATH hệ thống (bản có nvenc),
fallback về ffmpeg đi kèm imageio_ffmpeg (bản này KHÔNG có nvenc) nếu
không tìm thấy trong PATH — cần đảm bảo PATH đúng khi deploy sang máy khác.
CHƯA song song hoá việc render nhiều cảnh cùng lúc (vẫn tuần tự từng
cảnh) — vì GPU consumer (RTX 30xx) driver mặc định giới hạn ~3 phiên
NVENC đồng thời, nếu muốn parallelize cần kiểm tra giới hạn này trước
(dùng ThreadPoolExecutor với max_workers nhỏ, ví dụ 2-3) để tránh lỗi
"Out of NVENC sessions".
CHƯA test thực tế end-to-end trên máy có GPU (thay đổi này viết trong môi
trường sandbox không có GPU/mạng để chạy thử ffmpeg thật). Lần chạy đầu
tiên nên theo dõi kỹ log ffmpeg ở bước [5/7], đặc biệt nếu gặp lỗi liên
quan nvcuda.dll/driver/session limit.
Chất lượng mặc định tăng so với bản cũ: VIDEO_QUALITY=18 (trước là
-crf 20), VIDEO_PRESET nvenc mặc định p5 (cân bằng tốc độ/chất
lượng; có thể tăng lên p6/p7 nếu muốn nén tốt hơn và vẫn còn dư thời
gian).

### [2026-07-09] Bỏ hẳn moviepy khỏi video_compose.py — chuyển toàn bộ sang ffmpeg subprocess
- Đã làm: Bản 2026-07-09 trước đó (zoompan + NVENC) vẫn còn dùng `moviepy`
  (`CompositeVideoClip`, `VideoFileClip`, `concatenate_audioclips`) để ghép
  crossfade + burn phụ đề Pillow -> đây hoá ra vẫn là bottleneck chính còn lại
  (~2 it/s, vì `moviepy` giải mã/ghép frame bằng Python đơn luồng trước khi đưa
  ffmpeg encode, GPU không tăng tốc được đoạn này). Viết lại `video_compose.py`
  lần nữa, XOÁ TOÀN BỘ import/sử dụng `moviepy` và `numpy`:
  - Ken Burns: đổi từ filter `zoompan` sang filter `crop` (biểu thức theo biến
    `t`) + `scale`, công thức w(t)/h(t)/x(t)/y(t) dịch trực tiếp 1-1 từ logic
    `make_frame(t)` gốc (progress = t/duration) — dễ đối chiếu đúng/sai hơn
    zoompan, không cần ảnh supersample 2x nữa (dùng lại `_prepare_padded_image`
    cũ bằng PIL, chỉ chạy 1 lần/ảnh nên không phải bottleneck, lưu ra PNG cho
    ffmpeg đọc).
  - Ghép crossfade: đổi từ `CompositeVideoClip` sang filter `xfade` (chain
    nhiều xfade nếu >2 cảnh, offset tính luỹ kế). Vì mỗi clip vẫn có
    pre_roll/post_roll (đóng băng, mỗi bên `transition/2`, xem mục 4), phần
    thời lượng `xfade` "ăn mất" ở mỗi mối nối đúng bằng phần pre/post_roll đã
    cộng thêm -> tổng thời lượng cuối cùng vẫn CHÍNH XÁC bằng tổng
    `scene.duration` (bất biến quan trọng từ nhật ký 2026-07-08 được giữ
    nguyên, chỉ đổi cách triển khai).
  - Audio: đổi từ `concatenate_audioclips` sang filter `concat` (audio) +
    `afade` (click_fade 0.03s mỗi đầu clip) — logic giống hệt bản cũ.
  - Phụ đề: XOÁ TOÀN BỘ code Pillow (`_load_font`, `_wrap_text`,
    `_render_subtitle_frame`, `_build_subtitle_clip`) — thay bằng filter
    `subtitles=<path>.srt` của ffmpeg (dùng `libass`, đã có sẵn trong build
    ffmpeg gyan.dev full của người dùng). Đơn giản hơn nhiều, không cần tự vẽ
    bitmap từng dòng phụ đề nữa.
  - Chế độ `fade_black`: mỗi cảnh tự chứa audio riêng (render 1 lần bằng
    ffmpeg, có `fade`/`afade` ở 2 đầu nếu cần), ghép bằng `concat` DEMUXER
    (stream copy, không re-encode lần 2) thay vì `concatenate_videoclips`.
  - `config.py`: đổi `VIDEO_CODEC`/`VIDEO_QUALITY`/`VIDEO_PRESET`/
    `VIDEO_ENCODE_PARAMS` (dạng list tham số ffmpeg dùng chung crop+encode cũ)
    thành `VIDEO_ENCODER`/`VIDEO_NVENC_PRESET`/`VIDEO_CQ`/`VIDEO_PRESET`/
    `VIDEO_CRF` (tách rõ theo encoder, dùng trong `_video_encode_args()`).
  - `requirements.txt`: bỏ `moviepy` và `numpy` (không còn module nào trong
    project dùng 2 package này nữa).
- File liên quan: `modules/video_compose.py` (viết lại toàn bộ, không còn kế
  thừa gì từ bản zoompan trước đó ngoài ý tưởng dùng ffmpeg+NVENC),
  `config.py`, `requirements.txt`.
- Còn cần làm / lưu ý cho lần sau:
  - CHƯA test thực tế trên máy có GPU + ảnh/audio thật (viết trong sandbox
    không có ffmpeg/GPU để chạy thử). Rủi ro cao nhất nằm ở 2 chỗ: (1) filter
    `subtitles=` trên Windows rất dễ lỗi vì escape đường dẫn (đã escape dấu
    `:` và đổi `\` thành `/`, nhưng nên test kỹ với đường dẫn có dấu cách/ký
    tự tiếng Việt trong tên thư mục); (2) `subtitles=` cần `fontconfig` tìm
    được ít nhất 1 font hệ thống để render — nếu chữ phụ đề ra rỗng/lỗi font,
    cần thêm tham số `fontsdir=` trỏ tới 1 thư mục chứa file .ttf cụ thể
    (ví dụ `C:/Windows/Fonts`) trong `force_style`/filter thay vì dựa hoàn
    toàn vào fontconfig tự tìm.
  - ĐÃ SỬA ở nhật ký kế tiếp bên dưới (2026-07-09 "gộp 1-pass"): bản này ban
    đầu vẫn render từng cảnh ra file .mp4 riêng rồi xfade rồi mux phụ đề = 3
    lần encode nối tiếp, chính là nguyên nhân "vẫn còn chậm" người dùng báo lại
    ngay sau đó.

### [2026-07-09] Gộp toàn bộ thành 1 lệnh ffmpeg duy nhất/mode + sửa loạt lỗi nhỏ
- Lý do: Bản "bỏ hẳn moviepy" (nhật ký ngay phía trên) tuy đã bỏ moviepy nhưng
  vẫn gọi ffmpeg NHIỀU LẦN nối tiếp (render từng cảnh -> xfade -> mux phụ đề =
  3 lần transcode toàn bộ video), nên vẫn chậm và mất chất lượng do encode lại
  nhiều lần. Người dùng báo lại "vẫn chậm" -> viết lại lần nữa, gộp toàn bộ
  filter (crop từng cảnh + xfade/concat + audio concat/afade + burn phụ đề)
  vào ĐÚNG 1 `-filter_complex` DUY NHẤT, chỉ encode 1 LẦN.
- Đã làm:
  - Xoá các hàm render-từng-bước cũ (`_render_scene_clip`,
    `_render_scene_clip_with_audio`, `_concat_crossfade`, `_concat_audio`,
    `_concat_demuxer`, `_mux_with_subtitles`, `_burn_subtitles_only`), thay
    bằng đúng 2 hàm dựng 1 filter_complex hoàn chỉnh: `_compose_crossfade()`
    và `_compose_fade_black()`. Ảnh vẫn được chuẩn bị 1 lần bằng
    `_prepare_all_padded_images()` (PIL, không phải bottleneck) rồi feed thẳng
    N input ảnh (`-loop 1 -r fps -t <duration> -i padded.png`) + N input audio
    vào CÙNG 1 lệnh ffmpeg.
  - **Sửa bug NVENC**: thêm lại `-rc vbr -b:v 0` (bị thiếu ở bản trước) --
    thiếu 2 tham số này thì `-cq` có thể không kiểm soát đúng chất lượng vì
    NVENC rơi về rate-control mặc định.
  - **Sửa rủi ro lỗi "Input link parameters do not match"**: thêm
    `format=yuv420p` vào cuối MỌI filter crop/scale từng cảnh, đảm bảo tất cả
    nhánh video có cùng pixel format tuyệt đối trước khi vào `xfade`/`concat`.
  - **Sửa rủi ro lỗi/méo tiếng khi nối audio**: thêm
    `aformat=sample_rates=44100:channel_layouts=stereo` cho MỌI nhánh audio
    trước `afade`/`concat` -- quan trọng vì filter `concat` (audio) yêu cầu
    input cùng sample rate/channel layout; nếu không chuẩn hoá, dễ lỗi ngay khi
    `TTS_ENABLED=false` và người dùng tự bỏ audio test (.mp3/.wav/.m4a) có
    sample rate khác nhau vào `input_audio/`.
  - Sửa 1 lỗi cú pháp (dư dấu `:`) trong biểu thức `afade` viết tay ở bản
    trước.
  - Xử lý gọn trường hợp `n=1` (chỉ 1 cảnh): KHÔNG gọi `xfade`/`concat` nữa
    (dễ lỗi hoặc thừa với đúng 1 input), map thẳng nhãn `[v0]`/`[a0]` ra output.
  - Thêm cảnh báo mềm (in ra console, không chặn chạy) khi kịch bản có > 60
    cảnh, vì lệnh ffmpeg 1-pass có thể chạm giới hạn độ dài command-line trên
    Windows (~8191 ký tự).
  - Đã TỰ VERIFY bằng cách mock toàn bộ input/config, gọi trực tiếp
    `_compose_crossfade`/`_compose_fade_black`, in ra `filter_complex` sinh
    ra và đối chiếu tay: offset `xfade` 3 cảnh khớp chính xác, tổng thời
    lượng video cuối = đúng tổng `scene.duration` (bất biến quan trọng từ
    nhật ký 2026-07-08 vẫn được giữ), fallback `libx264` hoạt động, trường
    hợp `n=1` không sinh `xfade`/`concat` thừa. Chỉ verify được LOGIC build
    lệnh (không chạy ffmpeg thật vì sandbox không có ffmpeg/GPU).
- File liên quan: `modules/video_compose.py` (viết lại toàn bộ lần 2 trong
  cùng ngày, thay thế bản "1 lệnh cho mỗi bước" bằng "1 lệnh cho toàn bộ
  video").
- Còn cần làm / lưu ý cho lần sau:
  - VẪN CHƯA chạy thật trên máy có ffmpeg/GPU/ảnh/audio thật -- đây là ưu
    tiên #1 cho lần làm việc tiếp theo. Nếu ffmpeg báo lỗi filter_complex,
    in cả lệnh đầy đủ (đã có sẵn trong thông báo lỗi của `_run_ffmpeg`) để
    dễ soi.
  - Nếu kịch bản dài (nhiều cảnh, > 60) và gặp lỗi độ dài command-line trên
    Windows, hướng xử lý: hoặc chia video thành nhiều đoạn nhỏ rồi nối bằng
    concat demuxer (stream copy) ở bước cuối, hoặc chuyển sang truyền
    filter_complex qua file (`-filter_complex_script`) thay vì đối số dòng
    lệnh trực tiếp -- ffmpeg hỗ trợ đọc filter graph từ file, tránh giới hạn
    độ dài argv.
  - `force_style` của filter `subtitles` ĐÃ ĐƯỢC SỬA ở nhật ký [2026-07-11]
    (`MarginV` 60 -> 30, phụ đề trước đó bị đẩy lên quá cao gần nửa màn hình).
    Vẫn còn hard-code các giá trị khác (`FontSize=20`...) trong code — nếu
    muốn tuỳ chỉnh thêm theo yêu cầu người dùng, nên đưa vào `config.py`.

### [2026-07-11] Sửa 3 lỗi trải nghiệm xem: phụ đề cao, phụ đề lệch audio, audio dồn dập khi chuyển cảnh
- Lý do: Người dùng phản hồi video xuất ra có 3 vấn đề: (1) phụ đề bị đẩy lên
  cao gần nửa màn hình, (2) phụ đề không khớp thời điểm với audio thật (do
  cách cũ chỉ ước lượng theo tỉ lệ số từ, không đo timing thật), (3) lúc
  chuyển cảnh 2 audio dính sát nhau nghe dồn dập vì không có khoảng lặng thật
  giữa 2 câu thoại.
- Đã làm:
  - **Phụ đề cao**: `modules/video_compose.py::_subtitles_filter()` —
    `MarginV` 60 -> 30 (Alignment=2, căn giữa-dưới). Đã verify bằng cách trích
    1 frame thật từ video test, phụ đề nằm sát đáy khung hình.
  - **Phụ đề lệch audio**: viết lại toàn bộ `modules/subtitle_gen.py`. Thêm
    `faster-whisper` (chạy LOCAL, không qua API) để lấy WORD-LEVEL TIMESTAMP
    THẬT từ chính file `scene.audio_path` của mỗi cảnh, thay cho cách ước
    lượng cũ (chia đều theo tỉ lệ số từ trên tổng `scene.duration`). QUAN
    TRỌNG: whisper CHỈ dùng để lấy mốc thời gian — text hiển thị trên phụ đề
    vẫn lấy từ `scene.narration` GỐC (không dùng text whisper tự nhận diện),
    tránh sai chính tả/dấu tiếng Việt do whisper đoán nhầm. Vì số từ whisper
    nhận được và số từ trong narration gốc có thể lệch nhau (whisper gộp/tách
    từ khác), ánh xạ theo TỈ LỆ VỊ TRÍ (từ thứ k trong N từ narration -> mốc
    thời gian của từ ở vị trí k/N trong danh sách timestamp whisper), có ép
    buộc monotonic (mốc sau luôn >= mốc trước, không chồng lấn/lùi thời gian).
    FALLBACK 2 lớp: (a) nếu whisper không khởi tạo được (thiếu package/model
    tải lỗi) ngay từ đầu -> TOÀN BỘ video rơi về cách ước lượng cũ; (b) nếu
    whisper khởi tạo được nhưng lỗi ở MỘT audio cụ thể (file hỏng, không nhận
    được từ nào...) -> CHỈ riêng cảnh đó rơi về ước lượng cũ, các cảnh khác
    vẫn dùng timestamp thật. Cả 2 lớp fallback đều không làm dừng pipeline.
  - **Audio dồn dập khi chuyển cảnh**: thêm `config.SCENE_AUDIO_GAP` (mặc
    định 0.35s). Trong `modules/tts_engine.py`, hàm mới `_apply_scene_gaps()`
    được gọi ở CUỐI `generate_audio_for_scenes()` (áp dụng cho CẢ 2 nhánh:
    TTS thật và `TTS_ENABLED=false` dùng audio test local) — chèn THẬT một
    khoảng lặng vào cuối audio của MỌI cảnh TRỪ cảnh cuối cùng, bằng ffmpeg
    filter `apad` (hàm `_append_silence`), rồi ĐO LẠI `scene.duration` theo
    file đã pad. Vì gap nằm ngay BÊN TRONG `scene.duration` (đo bằng
    mediainfo sau khi pad), toàn bộ `subtitle_gen.py` và `video_compose.py`
    tự động nhất quán theo mà KHÔNG cần sửa logic riêng ở 2 module đó — bất
    biến "tổng thời lượng video = tổng scene.duration" (nhật ký 2026-07-08,
    2026-07-09) vẫn được giữ nguyên. Ở `video_compose.py`, chỉ tăng thêm
    `click_fade` (0.03s -> 0.08s) cho mượt hơn, không cần logic gap riêng.
  - Thêm config mới vào `config.py`: `SCENE_AUDIO_GAP` (mặc định 0.35, đặt 0
    để tắt hoàn toàn/giữ hành vi cũ), `WHISPER_MODEL_SIZE` (mặc định "small"),
    `WHISPER_DEVICE` (mặc định "cpu"), `WHISPER_COMPUTE_TYPE` (mặc định
    "int8").
  - Thêm `faster-whisper` vào `requirements.txt`.
- File liên quan: `modules/video_compose.py` (sửa `MarginV`, tăng
  `click_fade`), `modules/subtitle_gen.py` (viết lại toàn bộ), `modules/tts_engine.py`
  (thêm `_append_silence`, `_apply_scene_gaps`, gọi ở cuối
  `generate_audio_for_scenes`), `config.py` (thêm 4 biến mới), `requirements.txt`.
- Đã TỰ VERIFY bằng ffmpeg/Python THẬT (không chỉ đọc code), trong sandbox có
  ffmpeg + libass nhưng KHÔNG có mạng ra HuggingFace (nên whisper luôn rơi về
  nhánh fallback khi test — đã verify riêng cả 2 lớp fallback bằng cách mock):
  - `_append_silence`: test thật với ffmpeg trên cả 3 định dạng .mp3/.wav/.m4a,
    chênh lệch thời lượng đúng như gap cấu hình.
  - `_apply_scene_gaps`: test 3 cảnh, xác nhận CHỈ 2 cảnh đầu có gap, cảnh
    cuối KHÔNG có gap.
  - `_map_chunks_to_timestamps`: test với mock word_spans có khoảng ngừng bất
    thường, test lệch số từ whisper/narration (nhiều hơn và ít hơn), test
    word_spans rỗng (phải raise lỗi đúng), test câu 1 từ duy nhất — tất cả
    đều cho kết quả monotonic, không chồng lấn.
  - `generate_srt()` end-to-end: test fallback toàn cục (whisper không khởi
    tạo được), test fallback per-scene (1 cảnh lỗi, cảnh khác vẫn dùng
    whisper), file .srt sinh ra hợp lệ ở cả 2 trường hợp.
  - Chạy full pipeline thật (gap -> subtitle -> video_compose) bằng ffmpeg
    thật (`libx264`, vì sandbox không có GPU NVIDIA) với ảnh PNG giả + audio
    sine test: video xuất ra đúng 1920x1080@30fps, thời lượng khớp tổng
    `scene.duration` (chênh lệch 0.073s, do sai số mã hoá xfade/audio bình
    thường). Trích 1 frame thật để xác nhận trực quan vị trí phụ đề đã hạ
    xuống đúng, không còn cao gần nửa màn hình.
  - Test edge case n=1 (chỉ 1 cảnh): xác nhận KHÔNG có gap được thêm (đúng vì
    cảnh duy nhất cũng là cảnh cuối), pipeline chạy hết không lỗi.
- Còn cần làm / lưu ý cho lần sau:
  - CHƯA test được nhánh whisper THÀNH CÔNG thật (cần model tải về, cần mạng
    ra `huggingface.co` — sandbox lúc phát triển bị chặn domain này). Lần
    chạy đầu tiên trên máy thật của người dùng sẽ tự tải model `small`
    (~500MB) — cần đảm bảo có mạng, và nên theo dõi log `[SUBTITLE]` xem có
    rơi vào fallback ngoài ý muốn không (ví dụ do thiếu VRAM nếu đặt
    `WHISPER_DEVICE=cuda`).
  - `SCENE_AUDIO_GAP=0.35` là giá trị mặc định chọn tạm, CHƯA có phản hồi thực
    tế từ người dùng sau khi nghe thử — có thể cần tăng/giảm qua `.env` tuỳ
    cảm nhận thật.
  - `_append_silence` re-encode file audio 1 lần (ghi qua file tạm rồi
    `os.replace`) — với mp3 có tổn hao nhẹ (chấp nhận được vì chỉ 1 lần), với
    wav/m4a không đáng lo. Nếu về sau cần audio chất lượng cao tuyệt đối, có
    thể cân nhắc dùng lossless intermediate.
  - Video test dùng ảnh giả (PNG màu đơn sắc) + audio giả (sine tone), NÊN
    chạy lại toàn bộ 1 lần với ảnh/audio THẬT (giọng đọc tiếng Việt thật) để
    nghe/xem trực tiếp cảm nhận về gap 0.35s và độ khớp phụ đề khi whisper
    chạy thành công thật sự, không chỉ ở nhánh fallback.
  - CÂU HỎI CÒN MỞ (người dùng hỏi 2026-07-11): "chất lượng video đã đạt
    chuẩn YouTube chưa?" — trả lời: thông số kỹ thuật (H.264, yuv420p,
    1920x1080@30fps, AAC) ĐẠT chuẩn container/codec của YouTube. Nhưng
    "chuẩn YouTube" đầy đủ còn phụ thuộc nội dung/compliance (bản quyền ảnh/
    nhạc, thumbnail, rủi ro Inauthentic Content) mà `policy_check.py` tự nhận
    là CHƯA kiểm tra được — cần người dùng tự chạy `policy_check.py` trên
    video thật + tự soát thủ công theo báo cáo, KHÔNG có công cụ nào trong
    pipeline hiện tại tự động hoá được phần này.
### [2026-07-11] Thêm khả năng dùng VIDEO DỰNG SẴN thay ảnh tĩnh cho một số cảnh
- Lý do: Người dùng sẽ có sẵn một số video tự dựng muốn ghép xen kẽ vào pipeline
  thay vì luôn dùng ảnh tĩnh + Ken Burns cho mọi cảnh.
- Quyết định thiết kế (đã hỏi + xác nhận với người dùng trước khi code):
  - Video CHỈ thay thế ảnh tĩnh cho MỘT SỐ cảnh cụ thể (không phải toàn bộ,
    không phải intro/outro riêng biệt).
  - Chỉ định qua field mới `VIDEO:` trong kịch bản (giống pattern `MOTION:`/
    `IMAGE:` đã có), KHÔNG dùng thư mục trộn chung với ảnh.
  - Video KHÔNG bị cắt/loop để cố khớp audio làm cơ chế chính — thay vào đó
    ràng buộc đến từ PHÍA KỊCH BẢN: narration của cảnh dùng `VIDEO:` được viết
    sao cho tương đương 6-8 giây đọc (khớp gần đúng độ dài video thật). Cắt/
    loop bằng ffmpeg (`-stream_loop -1` + `-t`) chỉ là safety net phòng trường
    hợp lệch nhẹ, không phải cơ chế chính.
    **[ĐÃ THAY ĐỔI sau đó — xem nhật ký [2026-07-14] "Video dựng sẵn (VIDEO:)
    chuyển từ 'loop nếu ngắn hơn' sang 'độ dài cố định 8s, không loop'":**
    người dùng xác nhận MỌI video tự dựng đều cố định đúng 8 giây (không phải
    khoảng 6-8s) và muốn BỎ HẲN cơ chế loop (`-stream_loop -1`) — thay bằng
    `tpad` giữ nguyên frame cuối + cảnh báo console nếu lệch quá
    `config.SCENE_VIDEO_DURATION_WARN_THRESHOLD`. Đoạn quyết định gốc này giữ
    nguyên để phản ánh đúng lịch sử, không đại diện cho hành vi hiện tại.**
  - Video CHỈ lấy phần HÌNH, âm thanh gốc (nếu có) LUÔN bị tắt tiếng — giọng
    đọc của cảnh vẫn luôn là TTS narration như mọi cảnh khác.
    **[ĐÃ THAY ĐỔI sau đó — xem nhật ký [2026-07-13] "Đồng bộ hoá tài liệu":**
    quyết định "tắt hẳn" này đã được nới lỏng thành "trộn (mix) với âm lượng
    nhỏ hơn" qua `config.VIDEO_ORIGINAL_AUDIO_VOLUME`, nhưng thay đổi đó
    không được ghi nhật ký lúc thực hiện — mục này giữ nguyên để phản ánh
    đúng lịch sử, không đại diện cho hành vi hiện tại.**
- Đã làm:
  - **`modules/script_parser.py`**: thêm field `video_path: str = ""` vào
    `Scene`. Regex nhận diện field `VIDEO:` mới (giống cách nhận diện `MOTION:`/
    `IMAGE:` đã có), lưu TÊN FILE THÔ lấy từ kịch bản (chưa resolve path).
  - **`modules/image_sync.py`**: thêm hàm `_resolve_video_paths()` (gọi ở đầu
    `sync_images_to_scenes()`) — ghép tên file trong `scene.video_path` với
    `config.INPUT_VIDEOS_DIR` thành đường dẫn đầy đủ, raise `FileNotFoundError`
    NGAY nếu file không tồn tại (không đợi tới bước video_compose mới báo lỗi).
    Phần quét/đối chiếu/gán ẢNH hiện có được sửa để CHỈ áp dụng cho danh sách
    con các scene KHÔNG có `video_path` (`scenes_needing_image`) — số ảnh cần
    chuẩn bị chỉ cần khớp số cảnh KHÔNG dùng `VIDEO:`, không phải tổng số cảnh.
    Nếu MỌI cảnh đều dùng `VIDEO:`, bỏ qua hoàn toàn bước xử lý ảnh (không yêu
    cầu thư mục `input_images/` phải tồn tại).
  - **`modules/video_compose.py`**: viết thêm nhánh xử lý song song với nhánh
    ảnh Ken Burns đã có, KHÔNG đổi bất kỳ hành vi nào của nhánh ảnh cũ:
    - `_video_cover_filter()`: filter ffmpeg mới, chuẩn hoá video input bất kỳ
      (tỉ lệ khung hình/kích thước/fps khác nhau) về đúng `VIDEO_WIDTH x
      VIDEO_HEIGHT` kiểu "cover" (phủ kín, cắt bớt phần dư) — cùng triết lý
      với `_prepare_padded_image()` xử lý ảnh, nhưng KHÔNG áp Ken Burns (video
      tự có chuyển động sẵn). Luôn ép `fps` + `format=yuv420p` để tương thích
      `xfade`/`concat` chung với nhánh ảnh.
    - `_prepare_all_padded_images()`: đổi kiểu trả về từ `list` (index theo vị
      trí) sang `dict {scene.index: (padded_path, w, h)}`, CHỈ chứa entry cho
      cảnh KHÔNG có `video_path` (cảnh dùng video không cần bước "làm padded
      ảnh" này).
    - `_compose_crossfade()` và `_compose_fade_black()`: input mỗi cảnh giờ rẽ
      nhánh theo `scene.video_path` — có thì dùng `-stream_loop -1 -r <fps> -t
      <total_duration> -i <video_path>` (tự lặp nếu ngắn hơn, tự cắt nếu dài
      hơn), không thì dùng `-loop 1 ...` như cũ với ảnh padded (tra theo
      `scene.index` trong dict thay vì theo vị trí `i` như trước — sửa vì
      `padded_info` giờ có thể thiếu entry cho một số cảnh). Filter build cũng
      rẽ nhánh tương tự: `_video_cover_filter()` cho video, `_crop_filter_for_effect()`
      cho ảnh — cả 2 đều ra `format=yuv420p` nên `xfade`/`concat` phía sau xử
      lý đồng nhất, không cần biết nguồn gốc từng nhánh.
    - `compose_video()`: validate đầu vào rẽ nhánh — cảnh có `video_path` kiểm
      tra file tồn tại (báo lỗi rõ nếu thiếu), cảnh không có thì kiểm tra
      `image_path` như cũ; audio luôn bắt buộc ở cả 2 nhánh.
    - Bất biến quan trọng (mục 4, PROJECT_MEMORY) VẪN GIỮ NGUYÊN: pre_roll/
      post_roll cho crossfade hoạt động đúng với CẢ video (video cũng được
      loop+cắt theo đúng `total_duration = pre_roll + scene.duration +
      post_roll`, y hệt cách ảnh được loop).
  - **`config.py`**: thêm `INPUT_VIDEOS_DIR` (mặc định `input_videos/` cạnh
    `config.py`).
  - **`tao-kich-ban-nguoi-tien-su-SKILL.md`**: thêm mục "Field VIDEO: — dùng
    VIDEO DỰNG SẴN thay ảnh tĩnh cho MỘT SỐ cảnh" ngay sau phần hướng dẫn
    `IMAGE:`/PROMPT LÕI — quy định: chỉ ghi tên file (không ghi đường dẫn), một
    cảnh chỉ dùng 1 trong 2 field (`IMAGE:` hoặc `VIDEO:`), BẮT BUỘC narration
    của cảnh đó phải canh ~6-8 giây đọc, không cần `IMAGE:` nếu đã có `VIDEO:`,
    âm thanh gốc luôn bị tắt. Thêm ghi chú ở phần liệt kê 21 hiệu ứng Ken Burns:
    hiệu ứng CHỈ áp dụng cho cảnh dùng `IMAGE:`, cảnh dùng `VIDEO:` giữ nguyên
    chuyển động thật, không áp Ken Burns lên trên.
  - Sửa luôn 1 đoạn LỖI THỜI trong `PROJECT_MEMORY.md` mục 3 (Cấu trúc Scene):
    ghi chú cũ "Không còn field IMAGE: trong kịch bản" đã sai từ khi skill kịch
    bản (`tao-kich-ban-*-SKILL.md`) bắt đầu dùng lại `IMAGE:` để nhúng prompt
    tạo ảnh AI — nay sửa lại chính xác: `script_parser.py` vẫn nhận diện
    `IMAGE:` làm ranh giới regex nhưng không parse thành field riêng của
    `Scene`. Cũng ghi chú rõ field `video_path` MỚI (2026-07-11) có tên trùng
    nhưng Ý NGHĨA HOÀN TOÀN KHÁC field `raw_video_path` CŨ đã bị xoá khi fork
    bỏ Wan2.1 (nhật ký 2026-07-08) — tránh nhầm lẫn cho AI đọc lại sau này.
- File liên quan: `modules/script_parser.py`, `modules/image_sync.py`,
  `modules/video_compose.py`, `config.py`, `tao-kich-ban-nguoi-tien-su-SKILL.md`.
- Đã TỰ VERIFY bằng ffmpeg/Python THẬT (không chỉ đọc code):
  - `script_parser.py`: test parse với `VIDEO:` đứng sau `MOTION:`, đứng một
    mình không có `MOTION:`, và cảnh hoàn toàn không có field nào thêm — tất cả
    parse đúng, không ảnh hưởng cảnh dùng `IMAGE:`/`MOTION:` như cũ.
  - `image_sync.py`: test 3 cảnh (cảnh giữa dùng video) — xác nhận ảnh CHỈ gán
    đúng cho 2 cảnh còn lại theo đúng `scene.index`, cảnh dùng video không có
    `image_path`. Test trường hợp MỌI cảnh đều dùng video — xác nhận KHÔNG
    raise lỗi dù thư mục ảnh không tồn tại. Test file video không tồn tại —
    xác nhận raise `FileNotFoundError` rõ ràng ngay tại bước này.
  - `video_compose.py`: chạy FULL pipeline thật bằng ffmpeg (không mock) với 3
    cảnh (ảnh - video - ảnh xen kẽ), cả 2 chế độ `crossfade` và `fade_black`:
    - Trích frame thật tại 2 thời điểm khác nhau trong cảnh dùng video, xác
      nhận bằng mắt: vật thể chuyển động thật có đổi vị trí giữa 2 frame (khác
      hẳn ảnh tĩnh Ken Burns crop tĩnh tại chỗ).
    - Test riêng với video CÓ audio gốc (880Hz) khác hẳn audio TTS test
      (440Hz): trích audio track từ video output, chạy FFT phân tích tần số
      chủ đạo — kết quả CHỈ có 439.9Hz (đúng audio TTS), KHÔNG có dấu vết
      880Hz nào → xác nhận audio gốc của video bị tắt tiếng hoàn toàn, không
      lọt vào output.
    - Test edge case: file `VIDEO:` không tồn tại → raise lỗi đúng, rõ ràng.
- Còn cần làm / lưu ý cho lần sau:
  - CHƯA test với video THẬT có tỉ lệ khung hình khác biệt lớn (ví dụ video
    dọc 9:16 hoặc vuông 1:1) — `_video_cover_filter()` dùng logic "cover" giống
    hệt ảnh nên về lý thuyết xử lý đúng, nhưng nên xem thử bằng mắt lần chạy
    đầu với video thật của người dùng để chắc không bị crop mất chi tiết quan
    trọng ở giữa khung hình.
  - CHƯA test trường hợp video ngắn hơn NHIỀU so với `scene.duration` (ví dụ
    video chỉ 2s nhưng narration đọc mất 8s) — `-stream_loop -1` sẽ lặp lại
    nhiều lần, có thể thấy rõ điểm nối lặp (jump cut) nếu clip có chuyển động
    một chiều rõ rệt (ví dụ nhân vật đi từ trái sang phải rồi đột ngột về lại
    vị trí đầu). Vì đây được thiết kế là "safety net" chứ không phải cách dùng
    chính (người dùng nên tự canh video ~6-8s khớp narration), nhưng nên cảnh
    báo người dùng nếu thấy hiện tượng này khi xem video thật.
  - `select_effects_for_scenes()` trong `video_compose.py` vẫn được gọi cho
    TOÀN BỘ scenes kể cả cảnh dùng video (gán `scene.effect` dù giá trị này
    không được dùng tới với video) — vô hại nhưng hơi phí 1 lần gọi
    `effect_selector` không cần thiết, có thể tối ưu sau nếu cần.
  - Định dạng video hỗ trợ: bất kỳ định dạng nào ffmpeg đọc được qua
    `-stream_loop -1 -i <path>` (mp4/mov/mkv/webm...), KHÔNG có validate danh
    sách extension như `image_sync.py` làm với ảnh — nếu người dùng đưa file
    sai định dạng, lỗi sẽ chỉ xuất hiện khi ffmpeg thật sự chạy (thông báo lỗi
    của `_run_ffmpeg` sẽ hiện ra, nhưng kém rõ ràng hơn báo lỗi sớm ở
    `image_sync.py`).

### [2026-07-12] Sửa mâu thuẫn số học "Mật độ cảnh" trong SKILL.md người tiền sử (lên bản V1.1)
- Lý do: Review phát hiện lỗi toán học trong
  `tao-kich-ban-nguoi-tien-su-SKILL.md`: yêu cầu tối thiểu 55-70 cảnh cho
  video 25-30 phút (3.750-4.500 từ) không thể đạt được nếu tôn trọng trần 45
  từ/cảnh — cần tối thiểu ~86-103 cảnh mới đúng, và chính outline mẫu ở
  Phase 3 (bản gốc) đã ngầm định 48-75 từ/cảnh ở MỌI phần, tự mâu thuẫn với
  trần 45 từ/cảnh ngay trong ví dụ của skill (không chỉ ở trường hợp biên
  70 cảnh).
- Đã làm (CHỈ sửa `tao-kich-ban-nguoi-tien-su-SKILL.md`, không đổi module
  Python nào trong `modules/`):
  - **Mật độ cảnh**: thay mức tối thiểu cố định "55-70 cảnh" bằng bảng tra
    theo độ dài đã chọn ở Phase 1, dựa trên ngân sách ~40 từ/cảnh (dưới trần
    45 để có biên an toàn): 20 phút -> 75-80 cảnh, 25 phút -> 95-100 cảnh,
    30 phút -> 115-120 cảnh. Sửa đồng bộ ở mục "QUY TẮC MẬT ĐỘ CẢNH",
    checklist Phase 3, checklist Phase 5.
  - **Outline mẫu Phase 3**: tính lại số cảnh/phần theo đúng tỉ lệ thời
    lượng gốc của từng phần, cho trường hợp mặc định 25 phút (~97 cảnh);
    thêm ghi chú co giãn cho 20/30 phút ngay cuối template.
  - **Số cảnh `VIDEO:`**: nâng từ 3-5 lên 6-8 cảnh, KHÔNG co giãn theo độ
    dài (giới hạn khối lượng sản xuất video AI thủ công, không phải nhu cầu
    nhịp điệu) — sửa đồng bộ ở frontmatter, "Field VIDEO:" (rule 2 + rule 4
    phân bổ theo hồi), outline mẫu Phần 4/Phần 5, checklist Phase 3,
    checklist trước Phase 6, Phase 7 điểm 5.
  - **Ngân hàng giác quan**: thêm mục "NGÂN HÀNG GIÁC QUAN" vào template
    Phase 2, tổ chức THEO TỪNG câu chuyện/cụm cảnh thay vì 1 danh sách phẳng
    dùng chung cả kịch bản (tránh lặp lại, vi phạm Quy tắc 11, khi kịch bản
    giờ dài tới ~120 cảnh).
  - **Phase 7 export**: đổi bước 1 từ "tạo folder mới" (giả định luôn có
    file system) thành thích ứng theo môi trường — tạo file thật nếu có
    Code Execution, ngược lại xuất 2 khối Markdown code block kèm tên file
    ở đầu khối.
  - Bump "V1.0" -> "V1.1" ở H1 và mục "CÁC LỖI CẦN TRÁNH".
- File liên quan: `tao-kich-ban-nguoi-tien-su-SKILL.md`.
- Đã tự verify bằng grep toàn file sau khi sửa (`3-5`, `3 đến 5`, `55-70`,
  `(20-25 phút)`, `V1.0`) — không còn instance nào liên quan tới mật độ
  cảnh/số VIDEO: sót lại (2 kết quả còn lại của "3-5" là cụm "mỗi 3-5 phút"
  cho pattern reveal/pattern reset, khác hoàn toàn khái niệm số cảnh, không
  cần sửa).
- Còn cần làm / lưu ý cho lần sau:
  - CHƯA chạy thử skill V1.1 để viết 1 kịch bản thật (~95-120 cảnh) và xác
    nhận outline vẫn mạch lạc, không vụn/gượng ép — các con số mới mới chỉ
    tính trên giấy theo tỉ lệ.
  - Quy tắc "mỗi câu chuyện chia 4-8 cảnh" vẫn CHƯA khớp Phần 5 (1 câu
    chuyện cao trào cần ~20-23 cảnh) — tồn tại từ bản gốc (13-17 cảnh cũng
    đã vượt 4-8), không phải lỗi mới, nhưng nên ghi rõ luật này không áp
    dụng cho câu chuyện cao trào duy nhất nếu muốn dứt điểm.
  - Kịch bản ~95-120 cảnh sẽ THƯỜNG XUYÊN vượt
    `_MANY_SCENES_WARNING_THRESHOLD = 60` trong `video_compose.py` (hiện chỉ
    in cảnh báo, chưa xử lý thật, xem TODO nhật ký 2026-07-09 "Gộp toàn bộ
    thành 1 lệnh ffmpeg"). Nên ưu tiên implement chia nhỏ lệnh ffmpeg
    (`-filter_complex_script` đọc từ file, hoặc chia video rồi nối bằng
    concat demuxer) TRƯỚC KHI chạy kịch bản dày cảnh trên Windows (giới hạn
    dòng lệnh ~8191 ký tự).

### [2026-07-12] Hỗ trợ marker ***SPONSOR_BREAK***/***MIDROLL_BREAK*** từ skill prehistoric-humans-script-SKILL-US.md
- Lý do: Skill mới `prehistoric-humans-script-SKILL-US.md` (bản US, đơn ngữ
  Anh) chủ động chèn 2 marker `***SPONSOR_BREAK***`/`***MIDROLL_BREAK***`
  NGAY TRONG nội dung NARRATION (không phải field riêng, xem Rule 18d/18e
  của skill) để đánh dấu điểm chèn quảng cáo/sponsor khi edit video. Trước
  bản vá này, `script_parser.py` không nhận diện 2 marker này -> chúng lọt
  thẳng vào `scene.narration` -> bị TTS ĐỌC TO thành lời, là lỗi phát sinh
  nghiêm trọng khi dùng skill mới với pipeline hiện tại.
- Đã làm:
  - `modules/script_parser.py`: thêm field `ad_markers: list[str]` vào
    `Scene` (mặc định rỗng). Thêm hàm `_extract_ad_markers()` + regex
    `_AD_MARKER_RE` -- tách 2 marker ra khỏi narration TRƯỚC khi gán vào
    `Scene` (không còn lọt vào TTS), lưu lại đúng thứ tự xuất hiện vào
    `scene.ad_markers`. Áp dụng cho CẢ 2 nhánh parse (`[SCENE]` có cấu trúc
    VÀ nhánh đơn giản tách theo dòng trống). Kịch bản KHÔNG có marker này
    (mọi kịch bản cũ) -> `_extract_ad_markers` trả về nguyên văn, KHÔNG đổi
    hành vi cũ (early return khi không tìm thấy marker).
  - `modules/export.py`: thêm hàm `format_ad_breaks(scenes)` -- tính timecode
    ước tính (tổng dồn `scene.duration`, cùng cách `subtitle_gen.py` tính mốc
    phụ đề) cho từng marker tìm thấy, trả về chuỗi rỗng nếu kịch bản không
    có marker nào (không thêm mục thừa vào report cũ).
  - `main.py`: gọi `format_ad_breaks(scenes)` ngay sau khi có
    `policy_report`, nối thêm vào `report_text` (chỉ khi có marker) trước
    khi in ra và xuất file report ở bước [7/7] -- không cần file riêng,
    không đổi signature `export_report()`.
- File liên quan: `modules/script_parser.py`, `modules/export.py`, `main.py`.
- Đã TỰ VERIFY bằng Python thật (không chỉ đọc code):
  - `py_compile` cả 3 file -> không lỗi cú pháp.
  - Test `_extract_ad_markers()` độc lập: narration có marker giữa 2 câu ->
    marker tách sạch, câu trước/sau nối lại bằng 1 khoảng trắng, không còn
    ký tự `*` nào sót lại, `ad_markers` trả đúng thứ tự.
  - Test `parse_script()` full với kịch bản mẫu có cả `VIDEO:`/`IMAGE:` lẫn
    2 loại marker -> narration sạch 100%, `video_path` không bị ảnh hưởng,
    `ad_markers` gán đúng theo từng cảnh.
  - Test `format_ad_breaks()`: 3 cảnh mock (65s/70s/300s), marker ở cảnh 2/3
    -> timecode ra đúng 00:01:05 và 00:02:15 (= tổng dồn duration các cảnh
    trước đó, khớp cách tính mốc phụ đề). Không marker -> trả về chuỗi rỗng.
  - Test lại `test_script.txt` (kịch bản cũ, không có marker) bằng
    `parse_script()` thật -> 6 cảnh, mọi `ad_markers=[]`, không đổi hành vi.
- Còn cần làm / lưu ý cho lần sau:
  - CHƯA chạy end-to-end thật với 1 kịch bản do skill US sinh ra có marker
    thật qua TTS/ffmpeg thật (sandbox không có TTS/ffmpeg thật trong phiên
    vá lần này) -- nên nghe thử 1 lần để chắc chắn không còn sót âm thanh
    lạ quanh điểm marker (dù về lý thuyết code đã loại bỏ hoàn toàn).
  - `format_ad_breaks()` tính timecode dựa trên TỔNG DỒN `scene.duration`
    (giống mốc audio/phụ đề), dựa vào bất biến ở mục 4 (tổng thời lượng
    video cuối = tổng `scene.duration`) -- nếu sau này đổi bất biến đó thì
    phải sửa lại hàm này theo.
  - Pipeline vẫn KHÔNG tự động chèn quảng cáo vào video (ngoài scope) --
    chỉ báo cáo vị trí ước tính để người dùng tự chèn ở bước edit/YouTube
    Studio.

### [2026-07-13] Đồng bộ hoá tài liệu (PROJECT_MEMORY.md/README.md/skill) với source thật + bổ sung 14 hiệu ứng Ken Burns còn thiếu
- Lý do: Kiểm tra chéo skill (`prehistoric-humans-script-SKILL-US.md`),
  `PROJECT_MEMORY.md`, `README.md` với source code thật phát hiện nhiều điểm
  lệch pha: tài liệu quảng cáo tính năng chưa có thật trong code (21 hiệu ứng
  Ken Burns nhưng code chỉ có 7), tài liệu phủ nhận tính năng đã có thật
  (skill nói MUSIC: "chưa implement" dù `music_engine.py` đã chạy được từ
  lâu), và một số quyết định thiết kế đã đổi trong code nhưng không cập nhật
  nhật ký (audio gốc video: tắt hẳn -> mix; SCENE_AUDIO_GAP: 0.35 -> 0.95).
- Đã làm:
  - **Bổ sung 14 hiệu ứng Ken Burns còn thiếu** (thay vì bỏ bớt tuyên bố "21
    hiệu ứng" của skill xuống 7 — theo đúng yêu cầu "thêm hiệu ứng, không
    bỏ"): `modules/video_compose.py::_crop_filter_for_effect()` viết lại,
    GIỮ NGUYÊN 100% công thức của 7 hiệu ứng gốc (`zoom_in`/`zoom_out`/
    `pan_left`/`pan_right`/`pan_up`/`pan_down`/`static` — không đổi hành vi),
    thêm công thức cho 14 hiệu ứng còn lại:
    - 8 kết hợp zoom+pan chéo (`zoom_in_pan_left/right/up/down`,
      `zoom_out_pan_left/right/up/down`): dùng lại đúng công thức w(t)/h(t)
      của `zoom_in`/`zoom_out`, nhưng x(t)/y(t) pan theo hướng chỉ định dựa
      trên khoảng trống ĐỘNG còn lại tại thời điểm t (vì w/h thay đổi liên
      tục trong lúc zoom).
    - 4 pan chéo góc-tới-góc (`pan_diagonal_tl_br/tr_bl/bl_tr/br_tl`): kích
      thước khung giữ nguyên target (không zoom), chỉ di chuyển vị trí crop
      theo đường chéo tương ứng.
    - 2 hiệu ứng "breathe" (`zoom_in_out`, `zoom_out_in`): dùng lại đúng công
      thức w(t)/h(t) của `zoom_in`/`zoom_out`, nhưng thay tiến trình tuyến
      tính `p = t/duration` bằng tiến trình tam giác `tri_p = 1-abs(2p-1)`
      (0 -> 1 -> 0), tạo hiệu ứng zoom vào-rồi-ra hoặc ra-rồi-vào trong cùng
      1 cảnh.
    `modules/effect_selector.py::AVAILABLE_EFFECTS` mở rộng từ 7 lên đủ 21
    tên hiệu ứng (khớp với những gì `video_compose.py` giờ implement được),
    `_FALLBACK_CYCLE` mở rộng từ 6 lên 20 hiệu ứng (xen kẽ nhóm cơ bản/kết
    hợp/chéo/breathe) để chế độ `heuristic` khi không khớp từ khoá cũng xoay
    vòng qua đa dạng hiệu ứng hơn, không chỉ 6 hiệu ứng cơ bản như trước.
  - **Xoá cảnh báo lỗi thời "MUSIC: chưa implement"** trong
    `prehistoric-humans-script-SKILL-US.md` (mục "Field MUSIC:") — thay bằng
    xác nhận đúng: field này đã chạy được đầy đủ qua `script_parser.py`
    (`Scene.music_id`/`_apply_music_inheritance`), `modules/music_engine.py`
    (tải/cache theo sound ID), và `video_compose.py` (mix vào audio cuối).
    Bump version skill lên V1.3 kèm changelog giải thích.
  - **Sửa docstring `modules/script_parser.py`** (phần mô tả field `VIDEO:`):
    câu cũ nói audio gốc video "tự tắt tiếng gốc" đã sai — sửa thành mô tả
    đúng cơ chế TRỘN (mix) qua `config.VIDEO_ORIGINAL_AUDIO_VOLUME`.
  - **`PROJECT_MEMORY.md`** (chính file này):
    - Mục 1/2: đổi "Pipeline 7 bước" -> "Pipeline 8 bước", thêm bước 2.5
      (`music_engine.py`) đã bị bỏ sót từ trước; sửa câu "Không cần GPU"
      thành "Không cần GPU (có fallback CPU qua `VIDEO_ENCODER=libx264`)" vì
      mặc định thật của `config.py` là `h264_nvenc` (cần GPU NVIDIA).
    - Mục 2 bước 5: sửa "chỉ scale/crop kiểu 'cover' + tắt tiếng gốc" thành
      mô tả đúng cơ chế mix; thêm ghi chú 21 hiệu ứng.
    - Mục 3: bổ sung 3 field bị thiếu trong snippet `Scene` (`ad_markers`,
      `music_id`, `music_path` — đã tồn tại thật trong code từ nhật ký
      [2026-07-12] nhưng snippet tham chiếu ở mục 3 chưa từng được cập nhật).
    - Mục 4: viết lại phần mô tả cơ chế Ken Burns cho đúng 21 hiệu ứng (thay
      vì 7), xoá tham chiếu hàm `_make_ken_burns_frame_fn()` đã không còn tồn
      tại từ bản chuyển sang ffmpeg (nhật ký 2026-07-09), thay bằng đúng tên
      hàm hiện tại `_crop_filter_for_effect()`.
    - Mục 5: sửa `SCENE_AUDIO_GAP` default 0.35 -> 0.95 (khớp `config.py`
      thật và `webui/static/app.js`); thêm mục config nhạc nền
      (`MUSIC_ENABLED`/`FREESOUND_API_KEY`/`MUSIC_VOLUME`/`MUSIC_CACHE_DIR`)
      và `VIDEO_ORIGINAL_AUDIO_VOLUME` (cả 2 đều có từ lâu nhưng chưa từng
      được liệt kê ở mục này); thêm `FREESOUND_API_KEY` vào danh sách API keys.
    - Mục 6: thêm `modules/music_engine.py` vào danh sách module (bị bỏ sót
      hoàn toàn ở mọi bản trước dù module đã hoạt động từ nhật ký nào đó
      không xác định được chính xác — không tìm thấy entry nhật ký gốc ghi
      lại việc thêm module này).
    - Mục 9: sửa câu hỏi gợi ý "ngoài 7 hiệu ứng hiện có" -> "ngoài 21 hiệu
      ứng hiện có".
    - Thêm ghi chú "[ĐÃ THAY ĐỔI sau đó]" vào nhật ký [2026-07-11] "Video
      dựng sẵn thay ảnh tĩnh" ở đúng câu quyết định "âm thanh gốc LUÔN bị tắt
      tiếng" — KHÔNG xoá/sửa lại lịch sử gốc, chỉ đánh dấu rõ đây không còn
      là hành vi hiện tại, trỏ người đọc sang nhật ký này.
  - **`README.md`**: thêm mục nhạc nền (không còn là "gợi ý mở rộng chưa làm"
    — tính năng đã hoàn thiện), thêm mục field `VIDEO:` (dùng video dựng sẵn
    thay ảnh tĩnh, trước đây hoàn toàn không được nhắc tới), sửa tuyên bố
    tuyệt đối "Không cần GPU" thành "GPU không bắt buộc (mặc định dùng GPU
    NVIDIA để tăng tốc, có fallback CPU)", cập nhật cấu trúc thư mục kèm
    `music_engine.py`, thêm `FREESOUND_API_KEY` vào mục cấu hình API keys,
    sửa số hiệu ứng Ken Burns 7 -> 21.
- File liên quan: `modules/video_compose.py`, `modules/effect_selector.py`,
  `modules/script_parser.py`, `prehistoric-humans-script-SKILL-US.md`,
  `PROJECT_MEMORY.md` (chính file này), `README.md`.
- Đã TỰ VERIFY bằng Python thật (không chỉ đọc code):
  - `py_compile` cả `video_compose.py` và `effect_selector.py` -> không lỗi
    cú pháp sau khi sửa.
  - Trích riêng hàm `_crop_filter_for_effect()` (exec trực tiếp từ source,
    không phụ thuộc import `config`/PIL nặng) và gọi thử cho ĐỦ 21 hiệu ứng
    trong `AVAILABLE_EFFECTS` -> mọi hiệu ứng đều sinh ra filter hợp lệ
    (chứa `crop=` và `format=yuv420p`, không lỗi Python).
  - Viết lại bằng số học thuần Python (không qua ffmpeg thật, vì sandbox
    không có ffmpeg) công thức w(t)/h(t)/x(t)/y(t) của cả 21 hiệu ứng, test
    tại 5 mốc thời gian (t=0, t=pre_roll, t=giữa, t=cuối core, t=sau cuối) ->
    xác nhận bằng số: MỌI hiệu ứng đều giữ `target_w <= w <= padded_w`,
    `target_h <= h <= padded_h`, VÀ `0 <= x <= padded_w - w`,
    `0 <= y <= padded_h - h` tại mọi mốc test -> khẳng định KHÔNG BAO GIỜ lộ
    viền đen (đúng bất biến cốt lõi của cơ chế Ken Burns, mục 4).
- Còn cần làm / lưu ý cho lần sau:
  - CHƯA render thử video thật bằng ffmpeg với cả 14 hiệu ứng mới (sandbox
    không có ffmpeg trong phiên vá này) — mới verify được LOGIC sinh công
    thức (đúng số học, đúng biên), chưa xem bằng mắt video thật render ra có
    "đẹp"/mượt như mong đợi không, đặc biệt 2 hiệu ứng "breathe"
    (`zoom_in_out`/`zoom_out_in`) và 8 hiệu ứng kết hợp zoom+pan chéo — nên
    render thử 1 cảnh ngắn cho từng hiệu ứng mới trên máy có ffmpeg thật ở
    lần chạy tiếp theo trước khi dùng cho video thật.
  - `_HEURISTIC_KEYWORDS` trong `effect_selector.py` KHÔNG được mở rộng để
    match trực tiếp ra 14 hiệu ứng mới (vẫn chỉ map từ khoá -> 5 hiệu ứng cơ
    bản như cũ) — 14 hiệu ứng mới hiện chỉ xuất hiện qua `_FALLBACK_CYCLE`
    (khi không khớp từ khoá nào, hoặc khớp nhưng trùng hiệu ứng cảnh trước).
    Đây là lựa chọn có chủ đích để giữ thay đổi tối thiểu/surgical (theo
    CLAUDE.md mục 3), nhưng nếu muốn 14 hiệu ứng mới được chọn theo NỘI DUNG
    cảnh (không chỉ xoay vòng ngẫu nhiên) thì cần mở rộng `_HEURISTIC_KEYWORDS`
    ở lần sau.
  - Không tìm được nhật ký gốc nào ghi lại thời điểm `modules/music_engine.py`
    được thêm vào project hay thời điểm `VIDEO_ORIGINAL_AUDIO_VOLUME`/
    `SCENE_AUDIO_GAP` được đổi giá trị mặc định — 2 lỗ hổng nhật ký này chỉ
    được phát hiện qua đối chiếu chéo với `webui/static/app.js` (vốn đã khớp
    đúng giá trị hiện tại của `config.py`), không phải qua nhật ký nào. Nhắc
    nhở: MỌI thay đổi giá trị mặc định trong `config.py` cần có 1 dòng nhật
    ký kèm theo, kể cả thay đổi nhỏ như 1 con số default, để tránh lặp lại
    tình trạng lệch pha này.

### [2026-07-13] Sửa UnicodeEncodeError log tiếng Việt trên Windows (cp1252)
- Lý do: Người dùng chạy pipeline trên Windows (qua Web UI lẫn CLI trực tiếp)
  gặp crash ngay dòng log đầu tiên: `UnicodeEncodeError: 'charmap' codec can't
  encode character '\u1eae'...` khi `main.py` in `"=== BẮT ĐẦU PIPELINE:
  {title} ==="`. Nguyên nhân: console Windows mặc định dùng codepage `cp1252`
  (hoặc codepage theo ngôn ngữ hệ điều hành), codepage này KHÔNG mã hoá được
  nhiều ký tự tiếng Việt có dấu (như 'Ắ'), nên `print()` bất kỳ dòng log tiếng
  Việt nào cũng có thể crash — không phải lỗi logic của pipeline, mà lỗi môi
  trường encoding của Python/console.
- Đã làm:
  - **`main.py`**: thêm đoạn ép `sys.stdout`/`sys.stderr` dùng
    `reconfigure(encoding="utf-8", errors="replace")` ngay đầu file, TRƯỚC
    mọi `print()` khác trong toàn bộ pipeline (kể cả print từ các module con
    như `tts_engine.py`/`video_compose.py`, vì chúng dùng chung `sys.stdout`
    của tiến trình). Bọc try/except vì 1 số môi trường hiếm gặp có
    `sys.stdout` không phải `TextIOWrapper` (không hỗ trợ `reconfigure`) —
    khi đó im lặng bỏ qua, không chặn chương trình.
  - **`webui/app.py`**: thêm lớp phòng vệ thứ 2 — khi spawn subprocess
    `main.py` trong `_run_job()`, set thêm biến môi trường
    `PYTHONIOENCODING=utf-8` và `PYTHONUTF8=1` cho tiến trình con (qua tham
    số `env=` của `asyncio.create_subprocess_exec`), phòng trường hợp fix
    trong `main.py` vì lý do nào đó không áp dụng được trên máy người dùng.
    Không đổi cách đọc log ở phía Web UI (`line.decode("utf-8",
    errors="replace")` vẫn giữ nguyên, đã đúng từ trước).
- File liên quan: `main.py`, `webui/app.py`.
- Đã TỰ VERIFY bằng Python thật (không chỉ đọc code): mô phỏng 1
  `TextIOWrapper` với encoding `cp1252` (giống console Windows mặc định),
  xác nhận ghi ký tự 'Ắ' (U+1EAE) THẬT SỰ ném `UnicodeEncodeError` giống hệt
  traceback người dùng báo cáo; sau đó gọi `reconfigure(encoding="utf-8",
  errors="replace")` trên cùng stream, xác nhận ghi thành công, không còn
  crash. `py_compile` cả `main.py` và `app.py` sau khi sửa -> không lỗi cú pháp.
- Còn cần làm / lưu ý cho lần sau:
  - CHƯA test thật trên máy Windows của người dùng (sandbox không có Windows)
    — chỉ mô phỏng đúng cơ chế lỗi bằng Python thuần, không chạy `main.py`
    thật trên console Windows cp1252 thật. Nếu người dùng chạy lại vẫn còn
    lỗi tương tự, khả năng cao là 1 module con khác (vd `edge-tts` CLI, hoặc
    chính terminal/console app không đọc được UTF-8 khi hiển thị — khác với
    việc Python có encode được hay không) — cần xem kỹ traceback mới để phân
    biệt 2 loại lỗi này.
  - Sau fix, nếu chạy `main.py` trực tiếp trong `cmd.exe`/PowerShell cũ chưa
    bật UTF-8 console (`chcp 65001`), chữ tiếng Việt CÓ THỂ hiển thị sai ký tự
    (mojibake) thay vì bị lỗi bytes-level, nhưng KHÔNG còn crash chương trình
    — đây là đánh đổi chấp nhận được (ưu tiên "chạy được, hiển thị có thể xấu"
    hơn "crash giữa chừng"). Người dùng muốn hiển thị đẹp trong cmd.exe có thể
    tự chạy `chcp 65001` trước khi gọi `python main.py ...`.

### [2026-07-13] Vá lỗi nhiễu log "ConnectionResetError [WinError 10054]" trên Windows (asyncio Proactor)
- Lý do: Người dùng chạy Web UI trên Windows thấy console in traceback lặp
  lại nhiều lần: `Exception in callback _ProactorBasePipeTransport._call_
  connection_lost(None)` kèm `ConnectionResetError: [WinError 10054] An
  existing connection was forcibly closed by the remote host`. Đây là hành vi
  ĐÃ BIẾT của `asyncio` trên Windows: khi trình duyệt đóng tab/mất kết nối
  WebSocket đột ngột, hoặc 1 kết nối HTTP keep-alive bị phía client reset,
  `ProactorEventLoop` (event loop mặc định trên Windows) gọi
  `socket.shutdown()` trong lúc dọn dẹp transport trên 1 socket đã bị phía
  kia đóng trước -> ném `ConnectionResetError` ra ngoài callback nội bộ của
  event loop, bị in ra console như 1 lỗi chưa xử lý. KHÔNG phải lỗi logic
  của Web UI, KHÔNG ảnh hưởng job đang chạy hay các kết nối WebSocket khác --
  chỉ là nhiễu log.
- Đã làm: Thêm đoạn monkey-patch ở đầu `webui/app.py` (chỉ áp dụng khi
  `sys.platform == "win32"`, không ảnh hưởng máy Linux/macOS): bọc
  `_ProactorBasePipeTransport._call_connection_lost` gốc bằng try/except,
  nuốt riêng `ConnectionResetError` (các exception khác vẫn propagate bình
  thường, không che giấu lỗi thật). KHÔNG đổi sang `SelectorEventLoop` (dù đây
  cũng là 1 hướng fix phổ biến) vì `asyncio.create_subprocess_exec` (dùng để
  chạy `main.py` trong `_run_job()`) CHỈ được `asyncio` hỗ trợ trên
  `ProactorEventLoop` ở Windows — đổi loop sẽ làm gãy tính năng chạy pipeline.
- File liên quan: `webui/app.py`.
- Đã TỰ VERIFY: `py_compile` sau khi sửa -> không lỗi cú pháp. Vì
  `_ProactorBasePipeTransport` chỉ tồn tại trên Windows (sandbox phát triển
  là Linux), đã mô phỏng lại ĐÚNG cấu trúc patch (wrap 1 method ném
  `ConnectionResetError` bằng try/except tương tự) bằng 1 class giả lập ->
  xác nhận: gọi method đã patch KHÔNG ném exception ra ngoài nữa (trước đó
  chắc chắn sẽ ném, vì đã test riêng phần "chưa patch" trước).
- Còn cần làm / lưu ý cho lần sau:
  - CHƯA test thật trên Windows (sandbox không có Windows) -- chỉ verify được
    LOGIC patch đúng theo mô tả lỗi, chưa xác nhận bằng mắt là traceback thật
    trên máy người dùng biến mất hoàn toàn sau khi áp dụng.
  - Patch này CHỈ nuốt `ConnectionResetError` phát sinh từ đúng
    `_call_connection_lost` (nơi traceback người dùng báo cáo chỉ ra) -- nếu
    sau này xuất hiện `ConnectionResetError` ở method Proactor khác (ví dụ
    `_call_connection_made` hay tương tự), cần patch thêm method đó riêng,
    không tự động được che bởi patch này.
  - Nếu về sau nhiều lỗi nhiễu log kiểu Windows-Proactor khác xuất hiện, có
    thể cân nhắc gộp lại thành 1 custom `asyncio` exception handler
    (`loop.set_exception_handler(...)`) áp dụng chung cho mọi loại lỗi thay
    vì vá từng method riêng lẻ -- chưa làm ở bản này vì muốn giữ thay đổi tối
    thiểu/surgical (đúng phạm vi lỗi được báo cáo), theo CLAUDE.md mục 3.

### [2026-07-14] Video dựng sẵn (VIDEO:) chuyển từ "loop nếu ngắn hơn" sang "độ dài cố định 8s, không loop"
- Lý do: Người dùng cho biết TOÀN BỘ video tự dựng để đưa vào `input_videos/`
  đều có độ dài cố định 8 giây (không phải khoảng 6-8s như tài liệu cũ giả
  định). Vì video luôn cố định 8s, cơ chế loop cũ (`-stream_loop -1`, lặp lại
  từ đầu nếu ngắn hơn `scene.duration`) không còn cần thiết và có thể gây hiện
  tượng "jump cut" khó chịu nếu audio TTS dài hơn 8s (nhật ký [2026-07-11],
  mục "Còn cần làm" đã cảnh báo trước rủi ro này). Người dùng xác nhận muốn
  BỎ loop hẳn, chỉ cảnh báo (không chặn) nếu lệch quá nhiều, và muốn thời gian
  này CẤU HÌNH ĐƯỢC (không hard-code 8 rải rác trong code/skill).
- Đã làm:
  - **`config.py`**: thêm `SCENE_VIDEO_DURATION` (default 8.0, đọc từ `.env`)
    — độ dài chuẩn của mỗi video dựng sẵn. Thêm
    `SCENE_VIDEO_DURATION_WARN_THRESHOLD` (default 1.0 giây) — ngưỡng sai
    lệch giữa `scene.duration` (audio TTS thật) và `SCENE_VIDEO_DURATION`
    trước khi in cảnh báo.
  - **`modules/video_compose.py`**:
    - Bỏ `-stream_loop -1` khỏi CẢ 2 nơi input video (`_compose_crossfade` và
      `_compose_fade_black`) — video giờ chỉ được input đọc THẲNG 1 lần
      (không loop), `-t` chỉ dùng để cắt bớt nếu video dài hơn cần.
    - `_video_cover_filter()`: thêm tham số `pad_stop_duration`, thêm filter
      `tpad=stop_mode=clone:stop_duration=<pad_stop_duration>` vào cuối chain
      filter (trước `format=yuv420p`) — nếu video ngắn hơn thời lượng cần,
      `tpad` GIỮ NGUYÊN (đứng yên) frame CUỐI của video cho tới đủ độ dài,
      THAY VÌ lặp lại từ đầu như `-stream_loop -1` cũ. Cả 2 lời gọi hàm này
      (`_compose_crossfade` truyền `clip_durations[i]` tức `total_duration`
      bao gồm pre/post_roll; `_compose_fade_black` truyền thẳng
      `scene.duration`) đều được cập nhật.
    - `compose_video()`: thêm đoạn so sánh `scene.duration` (TTS) với
      `config.SCENE_VIDEO_DURATION` cho MỌI cảnh có `video_path`, in cảnh báo
      rõ ràng ra console (không raise lỗi, không chặn pipeline) nếu lệch quá
      `config.SCENE_VIDEO_DURATION_WARN_THRESHOLD` giây, kèm hướng dẫn (nên
      chỉnh lại narration cho khớp `SCENE_VIDEO_DURATION`).
    - Cập nhật docstring đầu file + đoạn "BẤT BIẾN QUAN TRỌNG" (mục 4) để mô
      tả đúng cơ chế mới (tpad thay vì loop) — bất biến "tổng thời lượng video
      cuối = tổng scene.duration" (nhật ký 2026-07-08/2026-07-09) VẪN GIỮ
      NGUYÊN, không đổi (chỉ đổi CÁCH video được pad tới đúng độ dài, không
      đổi độ dài cuối cùng).
  - **`prehistoric-humans-script-SKILL-US.md`**: bump lên V1.5. Đổi mọi chỗ
    ghi "narration ~6-8 giây (~15-22 từ)" cho cảnh `VIDEO:` thành "~8 giây
    (~20 từ)" cố định (mục "Field VIDEO:" điểm 2 + checklist + cross-check
    trước Phase 7 + điểm "No maximum on VIDEO: scene count"). Thêm điểm 6 mới
    trong "Count and placement" giải thích rõ: video được tạo ở độ dài cố định
    (mặc định 8s, `config.SCENE_VIDEO_DURATION`), KHÔNG loop, narration dài
    hơn -> giữ khung hình cuối; ngắn hơn -> cắt bớt. Thêm điểm 5 mới trong
    "Other technical rules": nếu người dùng dùng độ dài clip khác 8s, hỏi lại
    con số thật và tính narration theo ~2.5 từ/giây thay vì mặc định 20
    từ/8s.
- File liên quan: `config.py`, `modules/video_compose.py`,
  `prehistoric-humans-script-SKILL-US.md`, `PROJECT_MEMORY.md` (chính file
  này, mục 5).
- Đã TỰ VERIFY bằng ffmpeg/Python THẬT (không chỉ đọc code):
  - `py_compile` cả `config.py` và `video_compose.py` -> không lỗi cú pháp.
  - Test đơn vị `_video_cover_filter()`: xác nhận filter sinh ra chứa đúng
    `tpad=stop_mode=clone:stop_duration=<giá trị>` và `format=yuv420p`.
  - Test build lệnh đầy đủ `_compose_crossfade()` với mock 3 cảnh (2 cảnh
    dùng video, 1 cảnh dùng ảnh xen giữa) bằng cách patch `_run_ffmpeg` để
    bắt lại `cmd` thay vì chạy thật: xác nhận KHÔNG còn `-stream_loop` nào
    trong toàn bộ lệnh (chỉ nhạc nền mới còn dùng, không liên quan), xác nhận
    `tpad=stop_mode=clone` xuất hiện đúng 2 lần (khớp 2 cảnh video), xác nhận
    giá trị `stop_duration` truyền đúng bằng `total_duration` (đã cộng
    pre/post_roll) của từng cảnh.
  - Test THẬT bằng ffmpeg (có ffmpeg trong môi trường verify): dựng 1 video
    giả 3.2s (đỏ->xanh lá->xanh dương, mỗi màu ~1s) làm input, áp filter
    `tpad=stop_mode=clone:stop_duration=8.0` + `-t 8.0` — output đúng 8.0s,
    trích frame tại t=3.5s VÀ t=7.5s (cả 2 đều SAU khi video gốc đã hết ở
    t=3.2s) đều cho màu xanh dương (RGB `(0,0,254)`, đúng màu frame CUỐI của
    video gốc) -- xác nhận video ĐỨNG YÊN ở frame cuối, KHÔNG lặp lại về màu
    đỏ (frame đầu). Test thêm trường hợp video dài hơn total_duration (input
    3.2s, `-t 2.0` + `tpad stop_duration=2.0`) -> output đúng 2.0s, xác nhận
    bị cắt bớt đúng, không bị kéo dài thêm.
  - Grep toàn bộ `video_compose.py` sau khi sửa: chỉ còn đúng 1 chỗ
    `-stream_loop` (dùng cho nhạc nền trong `_build_music_track`, không liên
    quan tới video dựng sẵn, KHÔNG đổi -- nhạc nền vẫn cần loop bình thường
    vì độ dài đoạn nhạc gốc không liên quan gì tới độ dài cảnh).
  - Grep skill sau khi sửa: không còn instance nào ghi "6-8 giây"/"15-22 từ"
    cho narration `VIDEO:` (2 kết quả còn lại là "6-8 cap" ở changelog V1.1
    cũ — nói về SỐ LƯỢNG cảnh, không phải thời lượng — và "every 6-8 minutes"
    ở phần mid-roll break placement, hoàn toàn khác chủ đề, không cần sửa).
- Còn cần làm / lưu ý cho lần sau:
  - CHƯA test thật trên máy người dùng với video 8s thật (chỉ test bằng
    video giả 3 màu trong môi trường verify không có GPU NVIDIA/video thật).
    Lần chạy đầu tiên nên để ý log `[COMPOSE] CẢNH BÁO` — nếu xuất hiện
    thường xuyên nghĩa là TTS đang đọc lệch nhiều so với 8s, nên nghe thử các
    cảnh đó xem "khung hình đứng yên cuối clip" có bị lộ/khó chịu không.
  - `SCENE_VIDEO_DURATION_WARN_THRESHOLD=1.0` là giá trị chọn tạm (chưa có
    phản hồi thực tế) — nếu thấy cảnh báo bắn ra quá thường xuyên/quá hiếm so
    với cảm nhận thực tế khi nghe video, có thể chỉnh qua `.env`.
  - Skill mới (V1.5) có thêm điểm 5 trong "Other technical rules" cho phép
    linh hoạt nếu người dùng đổi độ dài video khác 8s sau này (ví dụ chuyển
    sang dùng tool tạo video 5s hoặc 10s) — NHƯNG bản thân AI viết kịch bản
    (Claude chạy skill) cần được NHẮC lại con số `config.SCENE_VIDEO_DURATION`
    hiện tại ở đầu mỗi phiên viết kịch bản mới, vì skill không tự đọc được
    `config.py`/`.env` của người dùng.

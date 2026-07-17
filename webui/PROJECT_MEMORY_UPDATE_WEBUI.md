### [2026-07-13] Thêm Web UI điều khiển pipeline từ xa (thư mục webui/ mới)
- Lý do: Cần điều khiển/chạy pipeline từ xa qua điện thoại thay vì phải ngồi
  máy tính gõ lệnh `python main.py ...`.
- Đã làm: Thêm thư mục MỚI HOÀN TOÀN `webui/` (KHÔNG sửa bất kỳ file nào
  trong `modules/`, `main.py`, `config.py` — pipeline gốc giữ nguyên 100%):
  - `webui/app.py`: backend FastAPI. Chạy pipeline bằng CÁCH GỌI SUBPROCESS
    `python -u main.py --script ... --title ... --output ...` (y hệt chạy
    tay), KHÔNG import trực tiếp các module Python của pipeline vào tiến
    trình web — giữ pipeline core hoàn toàn tách biệt, an toàn, dễ debug.
    Log stdout/stderr của subprocess được stream real-time qua WebSocket
    (`/ws/log`). Chỉ cho phép 1 job chạy tại 1 thời điểm (job thứ 2 bị từ
    chối với mã 409 khi job đầu chưa xong).
  - Quản lý input qua API upload: ảnh (`input_images/`) và audio test
    (`input_audio/`) BẮT BUỘC ghi tuần tự (không song song), cách nhau
    `asyncio.sleep(0.15)` giữa mỗi file để đảm bảo thời gian tạo file trên
    đĩa tăng dần đúng thứ tự — tương thích trực tiếp với cách
    `modules/image_sync.py::_get_creation_time` sắp xếp lại ảnh. Video dựng
    sẵn (`input_videos/`) giữ nguyên tên file gốc (đã strip path traversal
    qua `Path(filename).name`) vì kịch bản tham chiếu theo tên qua field
    `VIDEO:`.
  - Cấu hình: đọc/ghi trực tiếp file `.env` (giữ nguyên comment/format các
    dòng không liên quan, chỉ ghi đè đúng key được submit) — không cần
    restart server để áp dụng, vì mỗi lần chạy job là 1 subprocess mới sẽ tự
    `load_dotenv()` lại từ đầu (đúng cơ chế `config.py` gốc).
  - Đăng nhập bằng mật khẩu đơn (`WEBUI_PASSWORD`, lưu trong `.env`, đặt qua
    chính tab Cấu hình), cookie ký bằng `itsdangerous.TimestampSigner`. Nếu
    `WEBUI_PASSWORD` rỗng, bỏ qua xác thực hoàn toàn (chỉ an toàn trong LAN
    tin cậy — có cảnh báo rõ trong UI + README).
  - Frontend: `webui/static/{index.html,app.js,style.css,login.html}` —
    vanilla JS + CSS thuần (KHÔNG dùng CDN ngoài, để không phụ thuộc mạng
    Internet lúc dùng), 6 tab: Kịch bản / Ảnh & Video / Audio test / Cấu
    hình / Chạy / Kết quả.
  - Upload kịch bản `.md`: tự nhận diện + bóc nội dung ra khỏi khối Markdown
    code-fence (khớp định dạng Phase 7 Export của
    `prehistoric-humans-script-SKILL-US.md`), bỏ dòng tiêu đề dạng
    `--- ten-file.txt ---` nếu có.
  - `webui/requirements_web.txt`: dependency RIÊNG cho Web UI (fastapi,
    uvicorn, python-multipart, itsdangerous) — KHÔNG gộp vào
    `requirements.txt` gốc của pipeline.
- File liên quan: TOÀN BỘ file trong `webui/` là MỚI, không đụng tới file
  nào khác trong project gốc.
- Đã TỰ VERIFY bằng test thật (không chỉ đọc code), dùng
  `fastapi.testclient.TestClient` (giữ event loop bền vững qua
  `client.__enter__()` để `asyncio.create_task` chạy nền được giữa các
  request) + `main.py` giả lập (in log + tạo file output giả) + smoke test
  qua `uvicorn` thật/`curl` thật:
  - Luồng đăng nhập: chưa đặt mật khẩu → truy cập thẳng; đặt mật khẩu → chưa
    đăng nhập bị 401/redirect `/login`; sai mật khẩu → 401; đúng mật khẩu →
    set cookie, truy cập được; logout → 401 trở lại.
  - Upload ảnh giữ ĐÚNG THỨ TỰ gửi lên (test 3 ảnh tên alphabet ngược thứ tự
    mong muốn, xác nhận thứ tự lưu trên server theo đúng thứ tự UPLOAD chứ
    không phải thứ tự tên file).
  - Upload video chống path traversal (`../../evil.mp4` bị strip về
    `evil.mp4`, không thoát ra ngoài `input_videos/`).
  - Upload kịch bản `.md` dạng code-fence: bóc đúng nội dung, bỏ đúng dòng
    tiêu đề.
  - Chạy job thật qua subprocess: nhận đủ log, `status` chuyển đúng
    running → success, file output/srt xuất hiện đúng trong `output/`, tải
    file về đúng nội dung.
  - Job thứ 2 khi job đầu đang chạy → bị từ chối 409 (đúng thiết kế 1
    job/lúc).
  - WebSocket `/ws/log` nhận được log buffer cũ ngay khi kết nối.
  - Phát hiện + sửa 1 bug quan trọng TRƯỚC KHI giao: bản đầu dùng
    `time.sleep(0.15)` (đồng bộ) trong route `async def` khi upload nhiều
    ảnh → CHẶN CỨNG toàn bộ event loop vài giây, làm đứng WebSocket log của
    job khác đang chạy song song. Đã sửa sang `asyncio.sleep(0.15)`, chạy
    lại toàn bộ test suite xác nhận không phá hành vi cũ.
- Còn cần làm / lưu ý cho lần sau:
  - CHƯA test trên máy Windows thật của Hòa với ffmpeg/GPU/ComfyUI thật —
    chỉ test được bằng `main.py` giả lập trong sandbox Linux không có
    ffmpeg/GPU. Lần chạy đầu tiên nên thử 1 kịch bản ngắn (2-3 cảnh) trước
    khi chạy kịch bản dài thật.
  - Nút Huỷ (`/api/run/cancel`) chỉ gọi `process.terminate()` lên tiến trình
    `main.py` con — nếu `ffmpeg`/`edge-tts` cháu nó spawn ra đang chạy dở 1
    bước nặng, có thể cần thêm vài giây mới dừng hẳn, hoặc trong trường hợp
    xấu cần tự tắt thủ công qua Task Manager. Chưa implement kill theo cả
    process tree (cần `psutil` nếu muốn làm chặt hơn).
  - `WEBUI_PASSWORD` lưu dạng plain text trong `.env`, và toàn bộ API
    key/mật khẩu đi qua HTTP thường (không tự có HTTPS) — bắt buộc dùng kèm
    Tailscale/Cloudflare Tunnel khi truy cập ngoài mạng nhà, đã ghi rõ trong
    `README_WEBUI.md`, KHÔNG nên mở port router thẳng ra Internet.
  - Giới hạn ~8191 ký tự dòng lệnh Windows của `video_compose.py` (kịch bản
    dài >60 cảnh, xem nhật ký 2026-07-09/2026-07-12) KHÔNG liên quan gì tới
    Web UI (Web UI chỉ gọi `main.py` y hệt dòng lệnh) — rủi ro này vẫn tồn
    tại độc lập, chưa được giải quyết ở lớp nào.

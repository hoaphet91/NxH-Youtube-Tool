# Web UI — Điều khiển pipeline từ xa (qua điện thoại)

Lớp giao diện web bọc ngoài pipeline hiện có. **Không sửa bất kỳ file nào
trong `modules/` hay `main.py`** — Web UI chỉ gọi `python main.py --script
... --title ... --output ...` bằng subprocess, y hệt cách chạy tay, rồi
stream log thời gian thực về trình duyệt.

## 1. Cài đặt

Copy thư mục `webui/` này vào **đúng thư mục gốc project**, cạnh `main.py`
và `config.py` (`G:\AI Agent\youtube_pipeline\webui\`).

```bash
cd "G:\AI Agent\youtube_pipeline"
pip install -r webui\requirements_web.txt
```

(Không đụng vào `requirements.txt` gốc — file phụ thuộc mới nằm riêng ở
`webui/requirements_web.txt` để tách biệt hoàn toàn với pipeline.)

## 2. Chạy server

```bash
cd "G:\AI Agent\youtube_pipeline"
python -m uvicorn webui.app:app --host 0.0.0.0 --port 8000
```

Để trên máy tính (không phải điện thoại) vì cần GPU/ffmpeg/ComfyUI của máy đó.

## 3. Truy cập từ điện thoại

### Cùng mạng Wi-Fi nhà (đơn giản nhất)
1. Trên máy tính, chạy `ipconfig` (Windows) để lấy địa chỉ IPv4 (dạng
   `192.168.x.x`).
2. Trên điện thoại (cùng Wi-Fi), mở trình duyệt, vào:
   `http://192.168.x.x:8000`

### Truy cập từ xa, ngoài mạng nhà
Không nên mở port router trực tiếp ra Internet (không mã hoá, dễ bị dò quét).
Khuyến nghị 1 trong 2 cách sau (đều miễn phí):
- **Tailscale** (dễ nhất): cài Tailscale trên máy tính và điện thoại, đăng
  nhập cùng 1 tài khoản — điện thoại truy cập máy tính qua địa chỉ Tailscale
  riêng (`100.x.x.x`) như đang ở cùng mạng LAN, đã mã hoá WireGuard sẵn.
- **Cloudflare Tunnel**: `cloudflared tunnel --url http://localhost:8000`
  cho 1 địa chỉ HTTPS công khai tạm thời.

## 4. Bảo mật — ĐẶT MẬT KHẨU TRƯỚC KHI DÙNG TỪ XA

Vào tab **Cấu hình** → mục "Bảo mật Web UI" → đặt `WEBUI_PASSWORD` → Lưu.
Nếu để trống, **bất kỳ ai vào được địa chỉ này đều điều khiển được** (chỉ an
toàn khi chạy trong mạng nhà tin cậy, không public ra ngoài).

Lưu ý: mọi API key (ElevenLabs/OpenAI/Freesound) nhập ở tab Cấu hình được
ghi thẳng vào file `.env` như khi tự sửa tay — không mã hoá thêm. Chỉ nên
truy cập qua kênh đã mã hoá (Tailscale/Cloudflare Tunnel/HTTPS), trány dùng
qua HTTP thường trên mạng công cộng không tin cậy.

## 5. Các tab trong giao diện

| Tab | Chức năng |
|---|---|
| **Kịch bản** | Dán trực tiếp hoặc upload `.txt`/`.md`. Tự nhận diện và bóc script ra khỏi khối markdown code-fence nếu bạn upload thẳng file skill xuất ra (Phase 7). |
| **Ảnh & Video** | Upload ảnh cho từng cảnh (giữ đúng thứ tự — kéo-thả để sắp xếp lại, có xem trước thumbnail) và video dựng sẵn cho field `VIDEO:` (giữ nguyên tên file). |
| **Audio test** | Upload audio khi `TTS_ENABLED=false`, giữ đúng thứ tự cảnh. |
| **Cấu hình** | Toàn bộ biến trong `config.py`/`.env` qua form, chia nhóm rõ ràng. Lưu 1 lần cho tất cả. |
| **Chạy** | Nhập tiêu đề + tên file, bấm Bắt đầu. Log thời gian thực + thanh tiến trình theo 8 bước, có nút Huỷ. |
| **Kết quả** | Xem video ngay trên điện thoại (trình phát HTML5), tải video/phụ đề/báo cáo, lịch sử các lần chạy. |

## 6. Giới hạn cần biết

- **Chỉ chạy 1 video tại 1 thời điểm** — pipeline dùng nhiều CPU/GPU, chạy
  song song không an toàn tài nguyên. Bắt đầu job thứ 2 khi job đầu chưa
  xong sẽ bị từ chối (thông báo rõ ràng trên giao diện).
- **Nút Huỷ** gửi tín hiệu dừng `main.py`, nhưng nếu `ffmpeg` con đang chạy
  dở một bước nặng, có thể mất vài giây mới dừng hẳn hoàn toàn (đúng đặc thù
  vốn có của việc dừng 1 pipeline nhiều bước, không phải lỗi của Web UI).
- **Thứ tự ảnh/audio khi upload**: `modules/image_sync.py` sắp xếp theo
  *thời gian tạo file trên đĩa*. Web UI ghi file lần lượt (không song song),
  cách nhau 0.15 giây, để đảm bảo đúng thứ tự trên mọi hệ điều hành — không
  cần chỉnh gì thêm, chỉ cần chọn/kéo-thả đúng thứ tự trên giao diện trước
  khi bấm "Tải lên".
- Restart server (tắt/bật lại uvicorn) sẽ đăng xuất mọi phiên đang đăng nhập
  (cần nhập lại mật khẩu) — không ảnh hưởng tới file kịch bản/ảnh/cấu hình
  đã lưu, chỉ mất phiên đăng nhập.

## 7. Cập nhật PROJECT_MEMORY.md

Xem file `PROJECT_MEMORY_UPDATE_WEBUI.md` đi kèm — dán đoạn nhật ký đó vào
mục 11 của `PROJECT_MEMORY.md` thật trong project, theo đúng quy tắc bắt
buộc đã đặt ra trong file đó.

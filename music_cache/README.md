# Ghép nhạc nền 5 đoạn (Awe → Tension → Grief → Hope → Reflection)

## Chuẩn bị
1. Tạo 5 đoạn nhạc trên Google Flash/Lyria bằng 5 prompt tương ứng (Awe, Tension, Grief, Hope, Reflection) — mỗi prompt tạo riêng 1 lần.
2. Tải cả 5 file về, đặt vào **cùng thư mục** với `merge_music.sh`.
3. Đặt tên file đúng theo thứ tự, hoặc mở `merge_music.sh` sửa 5 dòng đầu (`FILE_1`...`FILE_5`) cho khớp tên file thật của bạn:
   ```
   1_awe.mp3
   2_tension.mp3
   3_grief.mp3
   4_hope.mp3
   5_reflection.mp3
   ```

## Chạy
```bash
bash merge_music.sh
```

Kết quả: `final_theme_music.mp3` — 1 track liền mạch, đã crossfade mượt giữa 5 đoạn, tổng khoảng 2.5 phút (5 đoạn × 30s − 4 lần crossfade × 0.75s).

## Nếu cần loop cho video dài hơn 2.5 phút
```bash
ffmpeg -stream_loop -1 -i final_theme_music.mp3 -t <SỐ_GIÂY_VIDEO> -c copy looped_output.mp3
```
Thay `<SỐ_GIÂY_VIDEO>` bằng độ dài video thực tế (ví dụ video 25 phút → `1500`).

## Tùy chỉnh trong script
- `CROSSFADE_SEC=0.75` — tăng lên 1.5–2 nếu vẫn nghe "cấn" ở mối nối.
- `FADE_TRIM_MS=30` — không cần chỉnh, chỉ là bước làm sạch mép file trước khi crossfade.

## Lưu ý
- Thứ tự ghép mặc định là Awe → Tension → Grief → Hope → Reflection, đúng vòng cung cảm xúc 1 "story beat" trong kịch bản. Nếu 1 tập có nhiều story (ví dụ 3 câu chuyện trong PART 2), có thể chạy script nhiều lần với các cặp mood khác nhau tùy theo outline Phase 3, rồi ghép các track đó lại tiếp khi dựng phim.
- Script không thay thế việc nghe lại bằng tai — sau khi ghép, luôn nghe thử 1 lượt để chắc chắn không còn điểm nào bị lệch nhịp trước khi đưa vào video chính thức.

Nếu máy bạn đã cài Git for Windows, sẽ có sẵn Git Bash:

Chuột phải vào thư mục chứa file → chọn "Git Bash Here"
Gõ: bash merge_music.sh

Nếu chưa cài, tải tại: https://git-scm.com/download/win (cài xong sẽ có bash dùng được)
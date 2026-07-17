#!/bin/bash
# ============================================================
# merge_music.sh
# Ghép 5 đoạn nhạc nền (Awe, Tension, Grief, Hope, Reflection)
# thành 1 track liền mạch bằng crossfade, dùng cho video
# prehistoric-humans series.
#
# YÊU CẦU: ffmpeg đã cài sẵn (kiểm tra bằng `ffmpeg -version`)
#
# CÁCH DÙNG:
#   1. Đặt 5 file mp3/wav vào cùng thư mục với script này,
#      đặt tên đúng theo biến bên dưới (hoặc sửa lại tên biến
#      cho khớp với file bạn tải về từ Google Flash/Lyria).
#   2. Chạy: bash merge_music.sh
#   3. Kết quả: final_theme_music.mp3 trong cùng thư mục.
#
# TÙY CHỈNH:
#   - CROSSFADE_SEC: độ dài crossfade giữa 2 đoạn (giây).
#     0.75s là mức an toàn, tăng lên 1.5-2s nếu vẫn nghe "cấn".
#   - FADE_TRIM: cắt bớt một chút đầu/cuối mỗi file trước khi
#     fade, phòng trường hợp file bị "click" ở mép do cắt cụt
#     (như file Before_the_Map.mp3 ban đầu bị cắt ở cuối).
# ============================================================

set -e  # dừng ngay nếu có lỗi

# ---- CẤU HÌNH: đổi tên file cho khớp với file bạn có ----
FILE_1="1_awe.mp3"
FILE_2="2_tension.mp3"
FILE_3="3_grief.mp3"
FILE_4="4_hope.mp3"
FILE_5="5_reflection.mp3"

OUTPUT="final_theme_music.mp3"

CROSSFADE_SEC=0.75      # độ dài crossfade giữa mỗi 2 đoạn
FADE_TRIM_MS=30         # cắt 30ms ở mép để loại bỏ click cứng trước khi fade

# ---- KIỂM TRA FILE TỒN TẠI ----
for f in "$FILE_1" "$FILE_2" "$FILE_3" "$FILE_4" "$FILE_5"; do
  if [ ! -f "$f" ]; then
    echo "❌ Không tìm thấy file: $f"
    echo "   Hãy đặt 5 file nhạc vào thư mục này và đổi tên đúng như trong script,"
    echo "   hoặc sửa biến FILE_1..FILE_5 ở đầu script cho khớp tên file thật của bạn."
    exit 1
  fi
done

echo "✅ Đã tìm thấy đủ 5 file. Bắt đầu ghép..."

# ---- BƯỚC 1: chuẩn hóa từng file (cùng sample rate, cùng codec,
#      trim mép cứng, fade nhẹ đầu/cuối để crossfade không bị click) ----
# QUAN TRỌNG: fade-out PHẢI tính theo ĐỘ DÀI THẬT của từng file (đọc bằng
# ffprobe), KHÔNG hard-code 1 mốc thời gian cố định (vd 29.4s) -- các file
# nhạc AI (Google Flash/Lyria...) có thể dài vài chục giây tới vài phút tùy
# lần tạo, hard-code sẽ fade-out SAI VỊ TRÍ (fade quá sớm rồi im lặng phần
# còn lại của file) nếu file dài hơn mốc hard-code đó.
mkdir -p _tmp_clean
i=1
for f in "$FILE_1" "$FILE_2" "$FILE_3" "$FILE_4" "$FILE_5"; do
  echo "  → Đang xử lý: $f"
  dur=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$f")
  fade_out_start=$(awk "BEGIN{printf \"%.3f\", $dur - 0.6}")
  ffmpeg -y -i "$f" \
    -af "afade=t=in:st=0:d=0.3,afade=t=out:st=${fade_out_start}:d=0.6" \
    -ar 44100 -ac 2 -c:a pcm_s16le \
    "_tmp_clean/clean_${i}.wav" -loglevel error
  i=$((i+1))
done

# ---- BƯỚC 2: ghép nối bằng acrossfade tuần tự (1→2→3→4→5) ----
echo "  → Đang crossfade nối các đoạn..."

ffmpeg -y \
  -i "_tmp_clean/clean_1.wav" \
  -i "_tmp_clean/clean_2.wav" \
  -i "_tmp_clean/clean_3.wav" \
  -i "_tmp_clean/clean_4.wav" \
  -i "_tmp_clean/clean_5.wav" \
  -filter_complex "\
    [0][1]acrossfade=d=${CROSSFADE_SEC}:c1=tri:c2=tri[a01]; \
    [a01][2]acrossfade=d=${CROSSFADE_SEC}:c1=tri:c2=tri[a012]; \
    [a012][3]acrossfade=d=${CROSSFADE_SEC}:c1=tri:c2=tri[a0123]; \
    [a0123][4]acrossfade=d=${CROSSFADE_SEC}:c1=tri:c2=tri[out]" \
  -map "[out]" -c:a libmp3lame -q:a 2 \
  "$OUTPUT" -loglevel error

rm -rf _tmp_clean

echo ""
echo "✅ HOÀN TẤT!"
echo "   File kết quả: $OUTPUT"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT" | \
  awk '{printf "   Tổng thời lượng: %.1f giây (~%.1f phút)\n", $1, $1/60}'
echo ""
echo "💡 Lưu ý: đây là 1 vòng nhạc nền (xem tổng thời lượng thật ở trên)."
echo "   Nếu video dài hơn, hãy loop lại toàn bộ file này bằng:"
echo "   ffmpeg -stream_loop -1 -i $OUTPUT -t <thời_lượng_video_giây> -c copy looped_output.mp3"

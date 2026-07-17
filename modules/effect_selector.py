"""
Module dùng trong bước 5 (video_compose.py gọi nội bộ): EFFECT SELECTOR
Tự động chọn 1 hiệu ứng chuyển động camera (biến thể Ken Burns: pan/zoom trên
ảnh tĩnh) phù hợp nhất cho từng cảnh, dựa trên nội dung narration + gợi ý
MOTION: (nếu có) trong kịch bản.

2 chế độ (config.EFFECT_SELECTION_MODE):
- "ai": gọi GPT (OpenAI) để AI đọc nội dung cảnh và chọn hiệu ứng hợp lý nhất.
  Cần OPENAI_API_KEY. Nếu gọi lỗi (mất mạng, hết quota...), tự động rơi về heuristic.
- "heuristic": chọn theo từ khoá đơn giản, miễn phí, không cần gọi API.

Cả 2 chế độ đều biết hiệu ứng của CẢNH LIỀN TRƯỚC (previous_effect) và cố tránh
chọn trùng ngay hiệu ứng đó, để video đỡ đơn điệu/lặp lại.

ĐỦ 21 HIỆU ỨNG (từ [2026-07-13], xem nhật ký PROJECT_MEMORY.md "Bổ sung 14
hiệu ứng Ken Burns còn thiếu"): 7 cơ bản (như bản gốc) + 8 kết hợp zoom+pan
chéo + 4 pan chéo góc-tới-góc + 2 hiệu ứng "breathe" (zoom vào-rồi-ra / ra-
rồi-vào trong cùng 1 cảnh). `video_compose.py::_crop_filter_for_effect()`
implement đủ công thức crop cho cả 21 hiệu ứng này.
"""
import sys

import config
from modules.cli_progress import write_progress
from modules.script_parser import Scene

AVAILABLE_EFFECTS = [
    # --- 7 cơ bản ---
    "zoom_in",   # phóng to dần — hợp cảnh cần nhấn mạnh cảm xúc, cận cảnh, cao trào
    "zoom_out",  # thu nhỏ dần — hợp cảnh mở đầu, tiết lộ dần toàn cảnh
    "pan_left",  # lia máy sang trái — hợp cảnh có chuyển động, panorama ngang
    "pan_right", # lia máy sang phải — tương tự pan_left nhưng ngược hướng, tránh lặp
    "pan_up",    # lia máy lên — hợp cảnh có chiều cao (núi, toà nhà, cây cối)
    "pan_down",  # lia máy xuống — hợp cảnh nhìn từ trên xuống, giới thiệu không gian
    "static",    # gần như đứng yên — hợp cảnh nhiều chữ/số liệu, cần người xem đọc kỹ

    # --- 8 kết hợp zoom + pan chéo (hợp cảnh cao trào/kể chuyện) ---
    "zoom_in_pan_left", "zoom_in_pan_right", "zoom_in_pan_up", "zoom_in_pan_down",
    "zoom_out_pan_left", "zoom_out_pan_right", "zoom_out_pan_up", "zoom_out_pan_down",

    # --- 4 pan chéo góc-tới-góc (hợp cảnh toàn cảnh rộng, cảm giác drone) ---
    "pan_diagonal_tl_br", "pan_diagonal_tr_bl", "pan_diagonal_bl_tr", "pan_diagonal_br_tl",

    # --- 2 "breathe" (zoom vào rồi ra hoặc ngược lại — hợp khoảnh khắc cảm xúc lắng đọng) ---
    "zoom_in_out", "zoom_out_in",
]

_HEURISTIC_KEYWORDS = {
    "zoom_out": ["toàn cảnh", "từ trên cao", "flycam", "panorama", "bao quát", "rộng lớn", "thung lũng"],
    "pan_up": ["núi", "toà nhà", "cao", "bầu trời", "toà tháp", "ngọn"],
    "pan_down": ["nhìn từ trên xuống", "bay qua", "trên cao nhìn xuống"],
    "pan_left": ["chuyển động", "đi bộ", "chạy", "đường phố", "dòng người", "xe cộ"],
    "static": ["biểu đồ", "số liệu", "văn bản", "danh sách", "thống kê", "infographic"],
}

# Chu trình xoay vòng dùng khi KHÔNG khớp từ khoá nào, luôn loại bỏ hiệu ứng
# vừa dùng ở cảnh trước để tránh lặp liên tiếp. Đã mở rộng để đi qua đủ cả 21
# hiệu ứng (không chỉ 6 hiệu ứng cơ bản như bản cũ) -- xen kẽ nhóm cơ bản/kết
# hợp/chéo/breathe để video đa dạng chuyển động hơn qua nhiều cảnh liên tiếp.
_FALLBACK_CYCLE = [
    "zoom_in", "pan_right", "zoom_out", "pan_left", "pan_up", "pan_down",
    "zoom_in_pan_right", "zoom_out_pan_left", "pan_diagonal_tl_br", "pan_diagonal_br_tl",
    "zoom_in_pan_up", "zoom_out_pan_down", "pan_diagonal_tr_bl", "pan_diagonal_bl_tr",
    "zoom_in_pan_left", "zoom_out_pan_right", "zoom_in_pan_down", "zoom_out_pan_up",
    "zoom_in_out", "zoom_out_in", "static",
]


def _scene_text(scene: Scene) -> str:
    """Gộp narration + gợi ý MOTION: (nếu có) làm nguồn văn bản để chọn hiệu ứng."""
    return f"{scene.narration} {scene.motion_prompt}".lower()


def _heuristic_select(scene: Scene, previous_effect: str | None = None) -> str:
    text = _scene_text(scene)

    matched = None
    for effect, keywords in _HEURISTIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            matched = effect
            break

    # Có khớp từ khoá và khác với cảnh trước -> dùng luôn (nội dung quyết định).
    if matched and matched != previous_effect:
        return matched

    # Không khớp gì, HOẶC khớp nhưng trùng hiệu ứng cảnh trước -> xoay vòng
    # qua danh sách rộng hơn, loại trừ hiệu ứng vừa dùng để tránh lặp liên tiếp.
    candidates = [e for e in _FALLBACK_CYCLE if e != previous_effect] or _FALLBACK_CYCLE
    return candidates[scene.index % len(candidates)]


def _ai_select(scene: Scene, previous_effect: str | None = None) -> str:
    from openai import OpenAI

    if not config.OPENAI_API_KEY:
        raise EnvironmentError("Thiếu OPENAI_API_KEY trong .env")

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    avoid_note = (
        f"Cảnh ngay trước đã dùng hiệu ứng '{previous_effect}' — TRÁNH chọn lại đúng "
        f"hiệu ứng này trừ khi nội dung cảnh này thực sự đòi hỏi y hệt, để video đỡ lặp lại nhàm chán.\n"
        if previous_effect else ""
    )
    prompt = (
        "Bạn là biên tập video chuyên nghiệp. Dựa vào lời thoại (và gợi ý chuyển động nếu có) "
        f"của một cảnh video dưới đây, hãy chọn ĐÚNG 1 hiệu ứng camera Ken Burns (pan/zoom trên "
        f"ảnh tĩnh) phù hợp nhất trong danh sách sau: {', '.join(AVAILABLE_EFFECTS)}.\n\n"
        f"{avoid_note}"
        f"Lời thoại: {scene.narration}\n"
        f"Gợi ý chuyển động (nếu có): {scene.motion_prompt or '(không có)'}\n\n"
        "Chỉ trả lời đúng 1 từ là tên hiệu ứng (ví dụ: zoom_in), không thêm giải thích, "
        "không thêm dấu câu."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0.3,
    )
    effect = resp.choices[0].message.content.strip().lower().strip(".")
    if effect not in AVAILABLE_EFFECTS:
        raise ValueError(f"AI trả về hiệu ứng không hợp lệ: '{effect}'")
    return effect


def _print_step_progress(done: int, total: int, label: str) -> None:
    write_progress("EFFECT", done, total, label)


def select_effects_for_scenes(scenes: list[Scene]) -> None:
    """Gán scene.effect cho từng scene trong danh sách (sửa trực tiếp object).
    Theo dõi hiệu ứng của cảnh liền trước để tránh 2 cảnh liên tiếp giống hệt nhau."""
    previous_effect: str | None = None
    for index, scene in enumerate(scenes, start=1):
        try:
            if config.EFFECT_SELECTION_MODE == "ai":
                scene.effect = _ai_select(scene, previous_effect)
            else:
                scene.effect = _heuristic_select(scene, previous_effect)
        except Exception as e:
            sys.stdout.write("\r")
            sys.stdout.flush()
            print(f"  [EFFECT] Cảnh {scene.index}: AI chọn lỗi ({e}) -> dùng heuristic dự phòng.")
            scene.effect = _heuristic_select(scene, previous_effect)

        _print_step_progress(index, len(scenes), f"cảnh {scene.index}: {scene.effect}")
        previous_effect = scene.effect
    sys.stdout.write("\r")
    sys.stdout.flush()

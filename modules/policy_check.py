"""
Module 6/7: POLICY CHECK
Rà soát tự động ở mức HEURISTIC (dựa trên từ khoá + thống kê) trước khi xuất
video, tham chiếu theo skill-kiem-tra-youtube-chi-tiet.md và
youtube-compliance-checklist.md trong project của bạn (nếu có).

QUAN TRỌNG: Đây KHÔNG phải rà soát pháp lý đầy đủ. Đây chỉ là lớp lọc tự động
để bắt các rủi ro rõ ràng và nhắc nhở các điểm cần con người xem lại thủ công
trước khi đăng (đặc biệt là bản quyền, nudity ngữ cảnh, và inauthentic content
vốn cần đánh giá bằng mắt/ngữ cảnh, máy khó tự phán đoán chính xác).
"""
from dataclasses import dataclass, field

from modules.script_parser import Scene
import config

# Từ khoá cảnh báo heuristic - KHÔNG đầy đủ, chỉ để bắt các trường hợp rõ ràng.
# Có match không có nghĩa là chắc chắn vi phạm, mà là cần con người xem lại.
_SENSITIVE_KEYWORDS = {
    "tự tử / tự hại": ["tự tử", "tự sát", "tự hại", "cách tự tử", "cách tự hại"],
    "chế tạo vũ khí/chất nổ/ma túy": ["cách chế tạo súng", "cách chế bom", "cách làm chất nổ", "cách nấu ma túy", "tổng hợp ma túy"],
    "y tế nguy hiểm": ["chữa ung thư bằng", "vắc-xin gây tự kỷ", "vắc xin gây tự kỷ", "thuốc chữa bách bệnh"],
    "lừa đảo/đầu tư": ["làm giàu nhanh", "đầu tư x2 x3", "lãi suất khủng", "nhân đôi tài sản"],
    "clickbait cực đoan": ["full video", "toàn bộ sự thật gây sốc", "cực sốc"],
}


@dataclass
class PolicyReport:
    copyright_status: str = "✅"
    honesty_status: str = "✅"
    sensitive_status: str = "✅"
    violence_status: str = "✅"
    regulated_goods_status: str = "🟡"  # mặc định vàng vì máy không tự xác minh được nguồn asset
    misinfo_status: str = "✅"
    thumbnail_status: str = "🟡"  # cần người kiểm tra thumbnail thủ công, tool này không tạo thumbnail
    advertiser_friendly_status: str = "🟢"
    ai_disclosure_needed: bool = False
    made_for_kids: str = "Cần rà soát thêm"
    notes: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)

    def overall_verdict(self) -> str:
        statuses = [
            self.copyright_status, self.honesty_status, self.sensitive_status,
            self.violence_status, self.misinfo_status,
        ]
        if "🔴" in statuses:
            return "KHÔNG ĐƯỢC ĐĂNG"
        if "🟡" in statuses or self.ai_disclosure_needed:
            return "SỬA TRƯỚC KHI ĐĂNG"
        return "ĐƯỢC ĐĂNG (sau khi người kiểm tra thủ công xác nhận thumbnail + bản quyền asset)"

    def render(self, video_title: str) -> str:
        lines = [f"KẾT QUẢ KIỂM TRA TỰ ĐỘNG: {video_title}", ""]
        lines.append(f"1. Bản quyền: [{self.copyright_status}]")
        lines.append(f"2. Trung thực (spam/lừa đảo/giả mạo/clickbait): [{self.honesty_status}]")
        lines.append(f"3. Nội dung nhạy cảm: [{self.sensitive_status}]")
        lines.append(f"4. Bạo lực & hành vi nguy hiểm: [{self.violence_status}]")
        lines.append(f"5. Hàng hoá bị kiểm soát: [{self.regulated_goods_status}]")
        lines.append(f"6. Sai lệch thông tin: [{self.misinfo_status}]")
        lines.append(f"7. Thumbnail: [{self.thumbnail_status}] (tool này không tạo thumbnail, cần tự kiểm)")
        lines.append(f"8. Advertiser-friendly (dự đoán): [{self.advertiser_friendly_status}]")
        lines.append(f"9. AI-generated disclosure: [{'Cần công bố' if self.ai_disclosure_needed else 'Không cần (theo cấu hình hiện tại)'}]")
        lines.append(f"10. Made for Kids: [{self.made_for_kids}]")
        lines.append("")
        lines.append(f"=> KẾT LUẬN: {self.overall_verdict()}")
        lines.append("")
        if self.notes:
            lines.append("GHI CHÚ:")
            for n in self.notes:
                lines.append(f"- {n}")
            lines.append("")
        if self.action_items:
            lines.append("DANH SÁCH HÀNH ĐỘNG CẦN SỬA:")
            for i, a in enumerate(self.action_items, start=1):
                lines.append(f"{i}. {a}")
        return "\n".join(lines)


def run_policy_check(scenes: list[Scene], video_title: str, total_duration: float) -> PolicyReport:
    report = PolicyReport()
    full_text = " ".join(s.narration.lower() for s in scenes) + " " + video_title.lower()

    for category, keywords in _SENSITIVE_KEYWORDS.items():
        for kw in keywords:
            if kw in full_text:
                report.sensitive_status = "🔴"
                report.action_items.append(
                    f"Phát hiện cụm từ nhạy cảm liên quan '{category}' (khớp '{kw}'). "
                    f"Xem lại kịch bản, đối chiếu mục 3/4/5/6 trong skill-kiem-tra-youtube-chi-tiet.md."
                )

    # QUAN TRỌNG: khác với bản Wan2.1 cũ (chuyển động do AI tạo -> luôn cần công
    # bố), bản này dùng hiệu ứng Ken Burns (pan/zoom) — một kỹ thuật dựng phim
    # TRUYỀN THỐNG, không phải AI. Nên việc có cần công bố "Altered content"/
    # AI-generated hay không giờ CHỈ phụ thuộc vào việc ẢNH GỐC có phải do AI
    # tạo ra hay không (config.IMAGES_ARE_AI_GENERATED), không phải vì có dùng
    # hiệu ứng pan/zoom.
    report.ai_disclosure_needed = bool(config.IMAGES_ARE_AI_GENERATED)
    if report.ai_disclosure_needed:
        report.action_items.append(
            "config.IMAGES_ARE_AI_GENERATED=True -> ảnh gốc do AI tạo -> BẬT toggle "
            "'Altered content' khi upload (Studio > Details > Show more > Altered content)."
        )
    else:
        report.notes.append(
            "config.IMAGES_ARE_AI_GENERATED=False -> giả định ảnh do bạn tự tạo/chụp/vẽ. "
            "Hiệu ứng Ken Burns (pan/zoom) là kỹ thuật dựng phim truyền thống, không phải AI "
            "-> thường KHÔNG cần bật 'Altered content'. Tự kiểm tra lại nếu ảnh thực ra có "
            "yếu tố AI mà bạn quên bật cấu hình này."
        )

    # Cảnh báo inauthentic/repetitious content — đây là rủi ro số 1 với pipeline tự động
    report.notes.append(
        "RỦI RO #1 THEO PROJECT CỦA BẠN: chính sách 'Inauthentic Content'. Vì video này "
        "được tạo hoàn toàn tự động theo khuôn mẫu cố định, hãy đảm bảo kịch bản của mỗi "
        "video có góc nhìn/thông tin/cấu trúc khác biệt thực chất so với các video trước, "
        "không chỉ đổi chủ đề bề mặt."
    )

    if total_duration < 60:
        report.notes.append(
            f"Video dài {total_duration:.0f}s (<60s): nếu đăng dạng Shorts, nhạc/audio dính "
            f"Content ID claim sẽ bị chặn NGAY LẬP TỨC — kiểm tra kỹ nguồn audio trước khi đăng."
        )

    report.notes.append(
        "Chưa tự động kiểm tra: nguồn gốc nhạc nền (nếu có), bản quyền ảnh gốc do bạn cung cấp, "
        "nội dung thumbnail. Những mục này cần bạn xác nhận thủ công."
    )

    return report

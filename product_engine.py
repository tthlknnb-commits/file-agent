from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductSpec:
    product_type: str
    title: str
    sections: tuple[str, ...]
    authority_sensitive: bool = False


PRODUCT_SPECS: dict[str, ProductSpec] = {
    "REPORT": ProductSpec("REPORT", "BÁO CÁO", ("TÌNH HÌNH", "KẾT QUẢ THỰC HIỆN", "ĐÁNH GIÁ", "TỒN TẠI, HẠN CHẾ", "NGUYÊN NHÂN", "NHIỆM VỤ, GIẢI PHÁP", "KIẾN NGHỊ, ĐỀ XUẤT")),
    "PLAN": ProductSpec("PLAN", "KẾ HOẠCH", ("MỤC ĐÍCH, YÊU CẦU", "NỘI DUNG, NHIỆM VỤ", "THỜI GIAN, ĐỊA ĐIỂM", "ĐỐI TƯỢNG, PHẠM VI", "KINH PHÍ", "TỔ CHỨC THỰC HIỆN")),
    "PROPOSAL": ProductSpec("PROPOSAL", "TỜ TRÌNH / ĐỀ XUẤT", ("SỰ CẦN THIẾT", "CĂN CỨ", "THỰC TRẠNG / VẤN ĐỀ", "NỘI DUNG ĐỀ XUẤT", "PHƯƠNG ÁN", "KIẾN NGHỊ"), True),
    "OFFICIAL_LETTER": ProductSpec("OFFICIAL_LETTER", "CÔNG VĂN", ("VẤN ĐỀ", "THÔNG TIN LIÊN QUAN", "YÊU CẦU / ĐỀ NGHỊ", "ĐỐI TƯỢNG THỰC HIỆN", "THỜI HẠN"), True),
    "DECISION": ProductSpec("DECISION", "QUYẾT ĐỊNH", ("CĂN CỨ", "QUYẾT ĐỊNH", "ĐIỀU KHOẢN THI HÀNH"), True),
    "NOTICE": ProductSpec("NOTICE", "THÔNG BÁO", ("NỘI DUNG", "ĐỐI TƯỢNG", "THỜI GIAN", "ĐỊA ĐIỂM", "YÊU CẦU", "ĐẦU MỐI"), True),
    "MINUTES": ProductSpec("MINUTES", "BIÊN BẢN", ("THỜI GIAN, ĐỊA ĐIỂM", "THÀNH PHẦN", "NỘI DUNG", "Ý KIẾN", "KẾT QUẢ / KẾT LUẬN", "TRÁCH NHIỆM")),
    "SPEECH": ProductSpec("SPEECH", "BÀI PHÁT BIỂU", ("KÍNH THƯA", "ĐẶT VẤN ĐỀ", "NỘI DUNG CHÍNH", "NHẬN ĐỊNH", "GIẢI PHÁP / ĐỀ XUẤT", "KẾT LUẬN")),
    "CONFERENCE": ProductSpec("CONFERENCE", "THAM LUẬN / HỘI NGHỊ", ("ĐẶT VẤN ĐỀ", "THỰC TRẠNG", "KẾT QUẢ / THỰC TIỄN", "VẤN ĐỀ", "PHÂN TÍCH", "GIẢI PHÁP", "KIẾN NGHỊ", "KẾT LUẬN")),
    "CRITIQUE": ProductSpec("CRITIQUE", "PHẢN BIỆN", ("LUẬN ĐIỂM", "CĂN CỨ", "DỮ LIỆU", "LOGIC", "ĐIỂM HỢP LÝ", "ĐIỂM CHƯA THUYẾT PHỤC", "KHOẢNG TRỐNG / RỦI RO", "ĐỀ XUẤT")),
    "OUTLINE": ProductSpec("OUTLINE", "ĐỀ CƯƠNG", ("MỤC TIÊU", "PHẠM VI", "ĐỐI TƯỢNG", "CẤU TRÚC", "NỘI DUNG TỪNG PHẦN", "DỮ LIỆU / CĂN CỨ CẦN CÓ", "KẾT QUẢ ĐẦU RA")),
    "TRAINING": ProductSpec("TRAINING", "TÀI LIỆU TẬP HUẤN", ("MỤC TIÊU HỌC TẬP", "KIẾN THỨC", "GIẢI THÍCH", "VÍ DỤ", "THỰC HÀNH", "KIỂM TRA", "TỔNG KẾT")),
    "ANALYSIS": ProductSpec("ANALYSIS", "PHÂN TÍCH", ("THỰC TẾ", "VẤN ĐỀ", "NGUYÊN NHÂN", "TÁC ĐỘNG", "PHƯƠNG ÁN", "ƯU / NHƯỢC ĐIỂM", "ĐỀ XUẤT")),
}


class ProductEngine:
    def identify(self, product_type: str) -> ProductSpec:
        return PRODUCT_SPECS[product_type]

    def validate(self, product_type: str) -> list[str]:
        if product_type not in PRODUCT_SPECS:
            return [f"UNKNOWN_PRODUCT:{product_type}"]
        return []

    def plan(self, product_type: str) -> list[str]:
        return list(self.identify(product_type).sections)

    def execute(self, product_type: str, request: str, evidence: list[dict]) -> str:
        spec = self.identify(product_type)
        lines = [spec.title, "", f"YÊU CẦU: {request}", ""]
        for index, section in enumerate(spec.sections, 1):
            lines.extend([f"{index}. {section}", "[NỘI DUNG TỪ NGUỒN ĐƯỢC XÁC NHẬN]", ""])
        if evidence:
            lines.extend(["NGUỒN THAM CHIẾU", ""])
            for item in evidence:
                lines.append(f"- {item.get('title') or item.get('uri')}")
        return "\n".join(lines).rstrip() + "\n"

    def integrate(self, content: str, product_type: str) -> str:
        return content if content.endswith("\n") else content + "\n"

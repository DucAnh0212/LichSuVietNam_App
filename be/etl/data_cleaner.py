import re
from bs4 import BeautifulSoup
from typing import Tuple, Optional

def clean_wiki_text(raw_text: str) -> str:
    """
    Làm sạch văn bản lấy từ Wikipedia:
    1. Xóa các thẻ chú thích dạng [1], [2], [a], [cần dẫn nguồn], [sửa | sửa mã nguồn]...
    2. Xóa khoảng trắng thừa, dòng trống liên tiếp.
    """
    if not raw_text:
        return ""
    
    # Nếu có dính thẻ HTML thì lọc lấy text thuần trước
    soup = BeautifulSoup(raw_text, "html.parser")
    # Xóa các thẻ rác của Wiki như bảng chú thích (sup.reference), nút sửa (span.mw-editsection)
    for tag in soup.find_all(["sup", "span"], class_=["reference", "mw-editsection"]):
        tag.decompose()
        
    text = soup.get_text(separator="\n")

    # Dùng Regex quét sạch các dấu ngoặc vuông chú thích còn sót lại: [1], [12], [cần dẫn nguồn]...
    text = re.sub(r"\[(\d+|[a-zA-Z]|cần dẫn nguồn|sửa.*?|chú thích.*?)\]", "", text, flags=re.IGNORECASE)
    
    # Dọn dẹp khoảng trắng thừa
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    
    return text.strip()

def parse_historical_date(date_str: str, default_year: Optional[int] = None) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Phân tích chuỗi thời gian lộn xộn của Wiki thành bộ 3 số nguyên: (nam, thang, ngay).
    Hỗ trợ cả năm Trước Công Nguyên (TCN / TrCN -> Số âm).
    """
    if not date_str:
        return (default_year, None, None)

    text = date_str.lower().strip()
    is_bce = any(keyword in text for keyword in ["tcn", "trcn", "trước công nguyên"])

    day, month, year = None, None, default_year

    # 1. Tìm Ngày (ví dụ: "ngày 19", "19 tháng 8", "30/4")
    day_match = re.search(r"(?:ngày\s*)?(\d{1,2})\s*(?:tháng|\/|-)", text)
    if day_match:
        d = int(day_match.group(1))
        if 1 <= d <= 31:
            day = d

    # 2. Tìm Tháng (ví dụ: "tháng 8", "30/4", "tháng 12 năm 1972")
    month_match = re.search(r"(?:tháng\s*|\/|-)(\d{1,2})(?:\s*năm|\/|-|\b)", text)
    if month_match:
        m = int(month_match.group(1))
        if 1 <= m <= 12:
            month = m

    # 3. Tìm Năm (ví dụ: "năm 938", "2879 tcn", "1945")
    # Ưu tiên tìm số có 3-4 chữ số, hoặc số đi sau chữ "năm"
    year_match = re.search(r"(?:năm\s*)?(\d{2,4})\s*(?:tcn|trcn)?\b", text)
    if year_match:
        # Lấy số cuối cùng nếu có dạng ngày/tháng/năm
        all_numbers = re.findall(r"\b(\d{1,4})\b", text)
        if all_numbers:
            candidate_year = int(all_numbers[-1])
            # Tránh nhầm tháng/ngày thành năm nếu chuỗi chỉ có "ngày 2 tháng 9"
            if candidate_year > 31 or "năm" in text or is_bce:
                year = -candidate_year if is_bce else candidate_year

    return (year, month, day)

def split_summary_and_detail(full_clean_text: str, max_summary_chars: int = 350) -> Tuple[str, str]:
    """
    Tách văn bản thành 2 phần:
    - noi_dung_tom_tat: Đoạn văn đầu tiên (giới hạn ký tự để hiển thị đẹp trên thẻ Card Timeline của Tín).
    - noi_dung_chi_tiet: Toàn bộ bài viết đầy đủ.
    """
    if not full_clean_text:
        return ("", "")
    
    paragraphs = [p.strip() for p in full_clean_text.split("\n\n") if len(p.strip()) > 30]
    if not paragraphs:
        return (full_clean_text[:max_summary_chars], full_clean_text)
    
    first_para = paragraphs[0]
    if len(first_para) > max_summary_chars:
        summary = first_para[:max_summary_chars].rsplit(" ", 1)[0] + "..."
    else:
        summary = first_para
        
    return (summary, full_clean_text)
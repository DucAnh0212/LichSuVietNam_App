import sys
import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

logging.basicConfig(level=logging.ERROR)
logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

from sqlalchemy.orm import sessionmaker
from database_config import engine, GiaiDoanLichSu, SuKien, LienKetSuKien, Media
from etl.data_cleaner import clean_wiki_text, split_summary_and_detail, parse_historical_date
from etl.cloud_helper import build_event_Image_id

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

WIKI_API_URL = "https://vi.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "VietnamHistoryInteractiveApp/3.0 (https://github.com/lichsuvn; contact@lichsuvn.edu.vn) Python-Requests"
}

CORE_SEED_EVENTS = [
    {"wiki_title": "Khởi nghĩa Hai Bà Trưng", "nam": 40, "thang": 3, "ngay": None},
    {"wiki_title": "Khởi nghĩa Bà Triệu", "nam": 248, "thang": None, "ngay": None},
    {"wiki_title": "Khởi nghĩa Lý Bí", "nam": 542, "thang": None, "ngay": None},
    {"wiki_title": "Khởi nghĩa Mai Thúc Loan", "nam": 713, "thang": None, "ngay": None},
    {"wiki_title": "Khởi nghĩa Phùng Hưng", "nam": 766, "thang": None, "ngay": None},
    {"wiki_title": "Trận Bạch Đằng (938)", "nam": 938, "thang": 11, "ngay": None},
    {"wiki_title": "Loạn 12 sứ quân", "nam": 966, "thang": None, "ngay": None},
    {"wiki_title": "Chiến tranh Tống–Việt (981)", "nam": 981, "thang": 3, "ngay": None},
    {"wiki_title": "Chiếu dời đô", "nam": 1010, "thang": 7, "ngay": None},
    {"wiki_title": "Chiến tranh Tống–Việt (1075–1077)", "nam": 1077, "thang": 3, "ngay": None},
    {"wiki_title": "Hội nghị Bình Than", "nam": 1282, "thang": 10, "ngay": None},
    {"wiki_title": "Hội nghị Diên Hồng", "nam": 1284, "thang": 12, "ngay": None},
    {"wiki_title": "Trận Chương Dương", "nam": 1285, "thang": 6, "ngay": None},
    {"wiki_title": "Trận Bạch Đằng (1288)", "nam": 1288, "thang": 4, "ngay": 9},
    {"wiki_title": "Chiến tranh Việt–Chiêm (1367–1396)", "nam": 1367, "thang": None, "ngay": None},
    {"wiki_title": "Chiến tranh Minh–Đại Ngu", "nam": 1406, "thang": 11, "ngay": None},
    {"wiki_title": "Khởi nghĩa Lam Sơn", "nam": 1418, "thang": 2, "ngay": 7},
    {"wiki_title": "Trận Tốt Động – Chúc Động", "nam": 1426, "thang": 11, "ngay": None},
    {"wiki_title": "Trận Chi Lăng – Xương Giang", "nam": 1427, "thang": 10, "ngay": None},
    {"wiki_title": "Hội thề Đông Quan", "nam": 1427, "thang": 12, "ngay": 10},
    {"wiki_title": "Chiến tranh Lê–Mạc", "nam": 1533, "thang": None, "ngay": None},
    {"wiki_title": "Trịnh–Nguyễn phân tranh", "nam": 1627, "thang": None, "ngay": None},
    {"wiki_title": "Phong trào Tây Sơn", "nam": 1771, "thang": None, "ngay": None},
    {"wiki_title": "Trận Rạch Gầm – Xoài Mút", "nam": 1785, "thang": 1, "ngay": 19},
    {"wiki_title": "Trận Ngọc Hồi – Đống Đa", "nam": 1789, "thang": 1, "ngay": 30},
    {"wiki_title": "Chiến dịch Đà Nẵng (1858–1860)", "nam": 1858, "thang": 9, "ngay": 1},
    {"wiki_title": "Phong trào Cần Vương", "nam": 1885, "thang": 7, "ngay": 13},
    {"wiki_title": "Khởi nghĩa Yên Thế", "nam": 1884, "thang": 3, "ngay": 16},
    {"wiki_title": "Phong trào Đông Du", "nam": 1905, "thang": None, "ngay": None},
    {"wiki_title": "Khởi nghĩa Yên Bái", "nam": 1930, "thang": 2, "ngay": 10},
    {"wiki_title": "Xô viết Nghệ Tĩnh", "nam": 1930, "thang": 9, "ngay": 12},
    {"wiki_title": "Cách mạng Tháng Tám", "nam": 1945, "thang": 8, "ngay": 19},
    {"wiki_title": "Tuyên ngôn độc lập (Việt Nam Dân chủ Cộng hòa)", "nam": 1945, "thang": 9, "ngay": 2},
    {"wiki_title": "Toàn quốc kháng chiến", "nam": 1946, "thang": 12, "ngay": 19},
    {"wiki_title": "Chiến dịch Việt Bắc Thu - Đông 1947", "nam": 1947, "thang": 10, "ngay": 7},
    {"wiki_title": "Chiến dịch Biên giới", "nam": 1950, "thang": 9, "ngay": 16},
    {"wiki_title": "Chiến dịch Hòa Bình", "nam": 1951, "thang": 11, "ngay": 14},
    {"wiki_title": "Chiến dịch Tây Bắc", "nam": 1952, "thang": 10, "ngay": 14},
    {"wiki_title": "Chiến dịch Điện Biên Phủ", "nam": 1954, "thang": 5, "ngay": 7},
    {"wiki_title": "Hiệp định Genève, 1954", "nam": 1954, "thang": 7, "ngay": 21},
    {"wiki_title": "Phong trào Đồng khởi", "nam": 1960, "thang": 1, "ngay": 17},
    {"wiki_title": "Trận Ấp Bắc", "nam": 1963, "thang": 1, "ngay": 2},
    {"wiki_title": "Chiến dịch Bình Giã", "nam": 1964, "thang": 12, "ngay": 2},
    {"wiki_title": "Trận Vạn Tường", "nam": 1965, "thang": 8, "ngay": 18},
    {"wiki_title": "Sự kiện Tết Mậu Thân", "nam": 1968, "thang": 1, "ngay": 30},
    {"wiki_title": "Trận Thành cổ Quảng Trị", "nam": 1972, "thang": 6, "ngay": 28},
    {"wiki_title": "Chiến dịch Điện Biên Phủ trên không", "nam": 1972, "thang": 12, "ngay": 18},
    {"wiki_title": "Hiệp định Paris 1973", "nam": 1973, "thang": 1, "ngay": 27},
    {"wiki_title": "Chiến dịch Đường 14 – Phước Long", "nam": 1975, "thang": 1, "ngay": 6},
    {"wiki_title": "Chiến dịch Tây Nguyên", "nam": 1975, "thang": 3, "ngay": 4},
    {"wiki_title": "Chiến dịch Huế – Đà Nẵng", "nam": 1975, "thang": 3, "ngay": 21},
    {"wiki_title": "Trận Xuân Lộc", "nam": 1975, "thang": 4, "ngay": 9},
    {"wiki_title": "Chiến dịch Hồ Chí Minh", "nam": 1975, "thang": 4, "ngay": 30},
    {"wiki_title": "Đổi Mới", "nam": 1986, "thang": 12, "ngay": 15}
]

ROOT_CATEGORIES = [
    "Thể loại:Trận đánh trong lịch sử Việt Nam",
    "Thể loại:Chiến dịch trong Chiến tranh Việt Nam",
    "Thể loại:Chiến dịch trong Chiến tranh Đông Dương",
    "Thể loại:Khởi nghĩa Việt Nam",
    "Thể loại:Chiến tranh liên quan tới Việt Nam",
    "Thể loại:Sự kiện lịch sử Việt Nam"
]

IGNORE_KEYWORDS = ["Bản mẫu:", "Thể loại:", "Danh sách", "Cổng thông tin:", "Wikipedia:", "Chủ đề:"]
BAD_IMAGE_KEYWORDS = [
    "flag_of", "medals", "icon", "padlock", "question_book", "commons-logo", 
    "stub", "ambox", "edit-ltr", "wikisource", "nuvola", "crystal_clear", 
    "symbol", "co_hieu", "quoc_ky", "map_pointer"
]

def crawl_category_recursive(category_title: str, depth: int = 2, visited_cats=None, collected_titles=None):
    if visited_cats is None:
        visited_cats = set()
    if collected_titles is None:
        collected_titles = set()
    if depth < 0 or category_title in visited_cats:
        return collected_titles

    visited_cats.add(category_title)
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category_title,
        "cmlimit": "max",
        "format": "json"
    }
    try:
        res = requests.get(WIKI_API_URL, params=params, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            members = res.json().get("query", {}).get("categorymembers", [])
            for m in members:
                ns = m.get("ns")
                title = m.get("title", "")
                if any(title.startswith(kw) for kw in IGNORE_KEYWORDS if kw != "Thể loại:"):
                    continue
                if ns == 0:
                    collected_titles.add(title)
                elif ns == 14 and depth > 0:
                    time.sleep(0.15)
                    crawl_category_recursive(title, depth - 1, visited_cats, collected_titles)
    except Exception as e:
        print(f"\n Lỗi quét thể loại '{category_title}': {e}")
    return collected_titles

def is_valid_content_image(img_tag) -> bool:
    src = (img_tag.get("src") or "").lower()
    if any(bad in src for bad in BAD_IMAGE_KEYWORDS):
        return False
    width = img_tag.get("width")
    height = img_tag.get("height")
    if width and width.isdigit() and int(width) < 180:
        return False
    if height and height.isdigit() and int(height) < 130:
        return False
    return True

def safe_download_image_bytes(wiki_url: str):
    if not wiki_url:
        return None
    if wiki_url.startswith("//"):
        wiki_url = "https:" + wiki_url

    candidates = []
    # Thử tăng độ phân giải lên 800px
    if re.search(r"/\d+px-", wiki_url):
        candidates.append(re.sub(r"/\d+px-", "/800px-", wiki_url))
        candidates.append(re.sub(r"/\d+px-", "/500px-", wiki_url))
    candidates.append(wiki_url)

    for url in candidates:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200 and len(res.content) > 1000:
                return res.content
        except Exception:
            continue
    return None

def upload_image_to_cloudinary_strict(img_bytes, public_id: str) -> str:
    if not img_bytes:
        return None
    try:
        response = cloudinary.uploader.upload(
            img_bytes,
            folder="lichsuvn_app/events",
            public_id=public_id,
            use_filename=False,
            unique_filename=False,
            overwrite=True,
            invalidate=True,
            timeout=15,
            resource_type="image",
            transformation=[
                {"width": 1200, "crop": "limit"},
                {"quality": "auto", "fetch_format": "auto"}
            ]
        )
        return response.get("secure_url")
    except Exception:
        return None

def fetch_wiki_article_rich(title: str):
    # 1. Lấy thông tin cơ bản và liên kết nhân quả
    q_params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "extracts|links",
        "explaintext": True,
        "pllimit": "max",
        "redirects": 1
    }
    res = requests.get(WIKI_API_URL, params=q_params, headers=HEADERS, timeout=15)
    res.raise_for_status()
    pages = res.json().get("query", {}).get("pages", {})
    
    page_info = None
    for pid, pinfo in pages.items():
        if pid != "-1":
            page_info = pinfo
            break
    if not page_info:
        return None

    actual_title = page_info.get("title", title)
    raw_extract = page_info.get("extract", "")
    links = [lk["title"] for lk in page_info.get("links", []) if lk.get("ns") == 0]

    # 2. Bóc tách HTML để lấy ngày tháng Infobox và các ảnh kèm vị trí ngữ cảnh
    p_params = {
        "action": "parse",
        "format": "json",
        "page": actual_title,
        "prop": "text",
        "redirects": 1
    }
    infobox_date_text = ""
    inline_images = []

    try:
        p_res = requests.get(WIKI_API_URL, params=p_params, headers=HEADERS, timeout=15)
        if p_res.status_code == 200:
            html_content = p_res.json().get("parse", {}).get("text", {}).get("*", "")
            if html_content:
                soup = BeautifulSoup(html_content, "html.parser")
                
                # Trích xuất dòng thời gian từ Infobox
                infobox = soup.find("table", class_=lambda c: c and "infobox" in c)
                if infobox:
                    for tr in infobox.find_all("tr"):
                        row_text = tr.get_text(" ", strip=True)
                        if any(k in row_text.lower() for k in ["thời gian", "ngày", "khởi sự"]):
                            infobox_date_text += " " + row_text

                # Quét tối đa 10 ảnh minh họa chất lượng cao trong bài
                figures = soup.find_all(["figure", "div"], class_=lambda c: c and ("thumb" in c or "mw-halign" in c))
                for fig in figures:
                    img_tag = fig.find("img")
                    if img_tag and is_valid_content_image(img_tag):
                        raw_src = img_tag.get("src")
                        caption_tag = fig.find(["figcaption", "div"], class_=lambda c: c and "caption" in c) or fig.find("figcaption")
                        caption_text = clean_wiki_text(caption_tag.get_text(" ", strip=True)) if caption_tag else ""
                        
                        # Đoạn văn bản neo (Anchor) ngay trước bức ảnh để xác định vị trí chèn chuẩn xác
                        prev_p = fig.find_previous("p")
                        anchor_text = ""
                        if prev_p:
                            p_clean = clean_wiki_text(prev_p.get_text(" ", strip=True))
                            if len(p_clean) >= 25:
                                anchor_text = p_clean[:50]

                        prev_heading = fig.find_previous(["h2", "h3"])
                        section_name = clean_wiki_text(prev_heading.get_text(" ", strip=True)) if prev_heading else ""

                        if raw_src:
                            inline_images.append({
                                "raw_src": raw_src,
                                "caption": caption_text,
                                "anchor_text": anchor_text,
                                "section": section_name
                            })
                        if len(inline_images) >= 10:  # Tối đa 10 ảnh / bài viết
                            break
    except Exception:
        pass

    return {
        "title": actual_title,
        "raw_text": raw_extract,
        "infobox_date_text": infobox_date_text,
        "inline_images": inline_images,
        "links": links
    }

def auto_detect_date(title: str, raw_text: str, infobox_date_text: str = ""):
    title_year_match = re.search(r"\b(\d{3,4})\b\s*(TCN|TrCN)?", title, re.IGNORECASE)
    default_year = None
    if title_year_match:
        y = int(title_year_match.group(1))
        is_bce = bool(title_year_match.group(2))
        if -2879 <= (-y if is_bce else y) <= 2026:
            default_year = -y if is_bce else y

    combined_search_text = f"{infobox_date_text} \n {raw_text[:1500]}"
    year, month, day = parse_historical_date(combined_search_text, default_year=default_year)

    if year is not None and (-2879 <= year <= 2026):
        return year, month, day
    return default_year, None, None

def find_era_id(year: int, eras_list):
    matching = [e for e in eras_list if e.nam_bat_dau <= year <= e.nam_ket_thuc]
    if matching:
        matching.sort(key=lambda x: x.nam_bat_dau, reverse=True)
        return matching[0].id
    return eras_list[0].id if eras_list else None

def inject_inline_images_into_detail(detail_text: str, uploaded_inline_list: list) -> str:
    if not uploaded_inline_list:
        return detail_text

    result_text = detail_text
    unplaced_tags = []

    for item in uploaded_inline_list:
        tag_str = f"\n\n[[IMAGE:{item['cloud_url']}|{item['caption']}]]\n\n"
        placed = False

        # Ưu tiên 1: Chèn ngay sau đoạn văn neo (Anchor Paragraph)
        anchor = item.get("anchor_text")
        if anchor and anchor in result_text:
            pos = result_text.find(anchor)
            next_newline = result_text.find("\n\n", pos)
            if next_newline != -1:
                result_text = result_text[:next_newline] + tag_str + result_text[next_newline:]
                placed = True
            else:
                result_text += tag_str
                placed = True

        # Ưu tiên 2: Chèn ngay bên dưới tiêu đề mục (Section Header)
        if not placed:
            sec = item.get("section", "").replace("=", "").strip()
            if sec and sec in result_text:
                pattern = re.compile(rf"(==+\s*{re.escape(sec)}\s*==+)")
                if pattern.search(result_text):
                    result_text = pattern.sub(rf"\1{tag_str}", result_text, count=1)
                    placed = True

        # Ưu tiên 3: Nếu không tìm thấy mốc nào, gom lại để chèn xen kẽ
        if not placed:
            unplaced_tags.append(tag_str)

    if unplaced_tags:
        paras = result_text.split("\n\n")
        insert_pos = min(2, len(paras))
        paras.insert(insert_pos, "".join(unplaced_tags).strip())
        result_text = "\n\n".join(paras)

    return result_text

def upsert_event_and_media(db, eras, wiki_data, year, month, day, title_to_event_obj, event_links_map):
    actual_title = wiki_data["title"]
    clean_text = clean_wiki_text(wiki_data["raw_text"])
    if len(clean_text) < 80:
        return

    summary, detail = split_summary_and_detail(clean_text)
    era_id = find_era_id(year, eras)

    existing_event = db.query(SuKien).filter(SuKien.ten_sukien == actual_title).first()
    if existing_event:
        existing_event.id_giai_doan = era_id
        existing_event.nam_dien_ra = year
        existing_event.thang_dien_ra = month if month is not None else existing_event.thang_dien_ra
        existing_event.ngay_dien_ra = day if day is not None else existing_event.ngay_dien_ra
        existing_event.noi_dung_tom_tat = summary
        event_obj = existing_event
    else:
        event_obj = SuKien(
            id_giai_doan=era_id,
            ten_sukien=actual_title,
            nam_dien_ra=year,
            thang_dien_ra=month,
            ngay_dien_ra=day,
            noi_dung_tom_tat=summary,
            noi_dung_chi_tiet=detail
        )
        db.add(event_obj)
        db.flush()

    # Dọn dẹp ảnh cũ để ghi đè danh sách ảnh chuẩn hóa mới
    db.query(Media).filter_by(id_sukien=event_obj.id, loai_media="IMAGE").delete()

    uploaded_inline = []
    # Đẩy toàn bộ tối đa 10 ảnh lên Cloudinary
    for idx_img, in_img in enumerate(wiki_data.get("inline_images", []), 1):
        img_bytes = safe_download_image_bytes(in_img["raw_src"])
        if not img_bytes:
            continue

        public_id = build_event_Image_id(
            event_id=event_obj.id,
            event_title=f"{actual_title}_img{idx_img}",
            event_year=year
        )

        cloud_url = upload_image_to_cloudinary_strict(img_bytes, public_id)
        if cloud_url:
            # Lưu đồng bộ vào bảng media kèm Chú thích vào cột tieu_de
            db.add(Media(
                id_sukien=event_obj.id,
                loai_media="IMAGE",
                url_link=cloud_url,
                tieu_de=in_img["caption"],
                is_thumbnail=False
            ))
            uploaded_inline.append({
                "cloud_url": cloud_url,
                "caption": in_img["caption"],
                "anchor_text": in_img["anchor_text"],
                "section": in_img["section"]
            })

    # Cập nhật chi tiết văn bản chứa các thẻ [[IMAGE:url|caption]] đúng vị trí
    event_obj.noi_dung_chi_tiet = inject_inline_images_into_detail(detail, uploaded_inline)

    title_to_event_obj[actual_title] = event_obj
    event_links_map[event_obj.id] = wiki_data["links"]
    db.commit()

def run_full_crawler():
    db = SessionLocal()
    try:
        eras = db.query(GiaiDoanLichSu).all()

        title_to_event_obj = {}
        event_links_map = {}
        processed_titles = set()

        # BƯỚC 1: Quét Hạt giống Cốt lõi
        total_seeds = len(CORE_SEED_EVENTS)
        for idx, item in enumerate(CORE_SEED_EVENTS, 1):
            w_title = item["wiki_title"]
            sys.stdout.write(f"\r [Bước 1/3 - Hạt giống] Đang xử lý: {idx}/{total_seeds} ({w_title[:30]:<30})")
            sys.stdout.flush()
            if w_title in processed_titles:
                continue
            try:
                wiki_data = fetch_wiki_article_rich(w_title)
                if wiki_data and wiki_data["raw_text"]:
                    y, m, d = auto_detect_date(wiki_data["title"], wiki_data["raw_text"], wiki_data["infobox_date_text"])
                    final_m = item["thang"] if item["thang"] is not None else m
                    final_d = item["ngay"] if item["ngay"] is not None else d

                    upsert_event_and_media(
                        db, eras, wiki_data,
                        item["nam"], final_m, final_d,
                        title_to_event_obj, event_links_map
                    )
                    processed_titles.add(w_title)
                    processed_titles.add(wiki_data["title"])
                time.sleep(0.15)
            except Exception as e:
                db.rollback()
                print(f"\n Lỗi tại hạt giống '{w_title}': {e}")

        # BƯỚC 2: Quét Cây Thể loại
        sys.stdout.write("\r [Bước 2/3 - Cây thể loại] Đang quét các nhánh sự kiện trên Wiki...                 ")
        sys.stdout.flush()
        discovered_titles = set()
        for root_cat in ROOT_CATEGORIES:
            crawl_category_recursive(root_cat, depth=2, collected_titles=discovered_titles)

        remaining_titles = [t for t in discovered_titles if t not in processed_titles]
        total_rem = len(remaining_titles)

        for idx, t in enumerate(remaining_titles, 1):
            sys.stdout.write(f"\r [Bước 2/3 - Sự kiện nhánh] Đang xử lý: {idx}/{total_rem} ({t[:30]:<30})")
            sys.stdout.flush()
            if t in processed_titles:
                continue
            try:
                wiki_data = fetch_wiki_article_rich(t)
                if not wiki_data or not wiki_data["raw_text"]:
                    continue

                actual_title = wiki_data["title"]
                if actual_title in processed_titles:
                    continue

                year, month, day = auto_detect_date(actual_title, wiki_data["raw_text"], wiki_data["infobox_date_text"])
                if year is None:
                    continue

                upsert_event_and_media(
                    db, eras, wiki_data,
                    year, month, day,
                    title_to_event_obj, event_links_map
                )
                processed_titles.add(t)
                processed_titles.add(actual_title)
                time.sleep(0.15)
            except Exception as e:
                db.rollback()
                print(f"\n Lỗi tại sự kiện nhánh '{t}': {e}")

        # BƯỚC 3: Nối mạng lưới Nhân - Quả
        sys.stdout.write("\r [Bước 3/3 - Liên kết] Đang ghép nối quan hệ Nhân - Quả...                           ")
        sys.stdout.flush()
        existing_links_set = {
            (r.id_sukien_goc, r.id_sukien_lien_quan)
            for r in db.query(LienKetSuKien.id_sukien_goc, LienKetSuKien.id_sukien_lien_quan).all()
        }

        new_links_batch = []
        for source_event in list(title_to_event_obj.values()):
            for target_title in event_links_map.get(source_event.id, []):
                target_event = title_to_event_obj.get(target_title)
                if not target_event or source_event.id == target_event.id:
                    continue

                pair = (source_event.id, target_event.id)
                if pair not in existing_links_set:
                    existing_links_set.add(pair)
                    if source_event.nam_dien_ra < target_event.nam_dien_ra:
                        loai = "TIEN_DE"
                    elif source_event.nam_dien_ra > target_event.nam_dien_ra:
                        loai = "KET_QUA"
                    else:
                        loai = "DONG_THOI"

                    new_links_batch.append(LienKetSuKien(
                        id_sukien_goc=source_event.id,
                        id_sukien_lien_quan=target_event.id,
                        loai_lien_ket=loai
                    ))

        if new_links_batch:
            db.bulk_save_objects(new_links_batch)
            db.commit()

        print(f"\n HOÀN TẤT TOÀN DIỆN! Đã xử lý {len(title_to_event_obj)} sự kiện kèm kho ảnh Cloudinary đa vị trí.")

    except Exception as e:
        db.rollback()
        print(f"\n Lỗi dừng hệ thống: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_full_crawler()
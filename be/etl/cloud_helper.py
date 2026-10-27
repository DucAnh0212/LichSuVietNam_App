import os
import re
import requests
import unicodedata
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

WIKI_HEADERS = {
    "User-Agent": "VietnamHistoryInteractiveApp/2.0 (https://github.com/lichsuvn; contact@lichsuvn.edu.vn) Python-Requests"
}

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

def slugify_vietnamese(text: str) -> str:
    if not text:
        return "su_kien"
    text = re.sub(r"[đĐ]", "d", text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return text[:60].rstrip("_")

def build_event_Image_id(event_id: int, event_title: str, event_year: int = None) -> str:
    slug = slugify_vietnamese(event_title)
    year_suffix = f"_{abs(event_year)}tcn" if (event_year and event_year < 0) else (f"_{event_year}" if event_year else "")
    if year_suffix and slug.endswith(str(abs(event_year))):
        year_suffix = ""
    return f"sk_{event_id:04d}_{slug}{year_suffix}"

def upload_wiki_image_to_cloud(wiki_image_url: str, event_id: int, event_title: str, event_year: int = None) -> str:
    if not wiki_image_url:
        return None
    if wiki_image_url.startswith("//"):
        wiki_image_url = "https:" + wiki_image_url

    clean_public_id = build_event_Image_id(event_id, event_title, event_year)

    try:
        # 1. Tự tải ảnh từ Wiki về RAM với User-Agent chuẩn 
        img_res = requests.get(wiki_image_url, headers=WIKI_HEADERS, timeout=10)
        img_res.raise_for_status()

        # 2. Đẩy luồng dữ liệu ảnh lên Cloudinary với timeout 15 giây 
        response = cloudinary.uploader.upload(
            img_res.content,
            folder="lichsuvn_app/events",
            public_id=clean_public_id,
            use_filename=False,
            unique_filename=False,
            overwrite=True,
            invalidate=True,
            timeout=15,
            resource_type="image",
            transformation=[
                {"width": 1000, "crop": "limit"},
                {"quality": "auto", "fetch_format": "auto"}
            ]
        )
        return response.get("secure_url")
    except Exception:
        # Nếu mạng chậm hoặc API Key Cloudinary chưa bật quyền create -> Dùng ngay link gốc Wiki
        return wiki_image_url

def extract_youtube_id(youtube_url_or_id: str) -> str:
    if not youtube_url_or_id:
        return None
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url_or_id)
    if match:
        return match.group(1)
    if len(youtube_url_or_id.strip()) == 11:
        return youtube_url_or_id.strip()
    return None
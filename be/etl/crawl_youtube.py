import sys
import os
import time
import html
import re
import logging
import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.ERROR)
logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

from sqlalchemy.orm import sessionmaker
from database_config import engine, SuKien, Media

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

# 1. BẢNG WHITELIST 20+ NGUỒN LỊCH SỬ UY TÍN
REPUTABLE_CHANNELS = [
    # Nhóm Đài truyền hình & Báo chí chính thống (Ưu tiên kiểm duyệt cao nhất)
    "vtv", "vtv1", "vtv7", "vtv24", "vtv đặc biệt", "vtv dac biet",
    "truyền hình quốc phòng việt nam", "qpvn",
    "truyền hình công an nhân dân", "antv",
    "truyền hình thông tấn", "vnews",
    "báo nhân dân", "truyền hình nhân dân",
    "đài phát thanh - truyền hình hà nội", "hanoi tv", "hanoitv",
    "đài truyền hình tp.hồ chí minh", "htv", "htv9", "htv7",
    
    # Nhóm Kênh biên khảo sa bàn, đồ họa & tư liệu lịch sử có thẩm định
    "việt sử toàn thư", "sử lược", "cdteam", "cdteam - sử lược",
    "đu đu đút", "ez sử", "dòng máu việt",
    "hùng ca sử việt", "bước chân lịch sử", "hồ sơ lịch sử",
    "bác cổ thông kim", "tóm tắt lịch sử", "sử ký việt",
    "kho báu lịch sử", "sử thi việt nam", "kênh tư liệu lịch sử"
]

# 2. BLACKLIST TỪ KHÓA LOẠI BỎ RÁC (Review phim, Spoil, Game, Parody, Shorts)
STRICT_BLACKLIST = [
    "review phim", "tóm tắt phim", "spoil phim", "giải mã phim", "hậu trường phim",
    "phim chiếu rạp", "trailer", "teaser", "full movie", "tập 1", "tập 2", "tập cuối",
    "phim truyện", "phim bộ", "trích đoạn phim", "hoạt hình chế",
    "reaction", "phản ứng", "nhạc chế", "rap về", "mv chính thức", "official mv",
    "gameplay", "mod game", "mô phỏng game", "total war", "hoi4",
    "shorts", "#shorts", "tiktok", "thuyết âm mưu", "bí ẩn rùng rợn"
]

def clean_event_keyword(title: str) -> str:
    clean = re.sub(r"\(.*?\)", "", title)
    clean = re.sub(r"\[.*?\]", "", clean)
    return clean.strip().lower()

def evaluate_video(item: dict, raw_event_title: str):
    raw_title = item["snippet"].get("title", "")
    clean_title = html.unescape(raw_title).strip()
    title_lower = clean_title.lower()
    channel_name = item["snippet"].get("channelTitle", "").strip()
    channel_lower = channel_name.lower()
    vid_id = item["id"].get("videoId")

    if not vid_id:
        return None, False

    # Lớp 1: Diệt từ khóa rác
    if any(bad in title_lower for bad in STRICT_BLACKLIST):
        return None, False

    clean_event = clean_event_keyword(raw_event_title)
    is_trusted = any(rep_ch in channel_lower for rep_ch in REPUTABLE_CHANNELS)

    # Lớp 2: Kiểm tra nguồn uy tín
    if is_trusted:
        event_words = [w for w in clean_event.split() if len(w) > 2]
        match_count = sum(1 for w in event_words if w in title_lower)
        # Khớp ít nhất 50% số từ hoặc chứa trọn vẹn cụm từ sự kiện
        if clean_event in title_lower or (event_words and match_count >= max(1, len(event_words) // 2)):
            return {
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "title": clean_title,
                "channel": channel_name
            }, True

    # Lớp 3: Nguồn ngoài Whitelist (Kiểm soát nghiêm ngặt)
    if clean_event in title_lower:
        return {
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "title": clean_title,
            "channel": channel_name
        }, False

    return None, False

def search_youtube_videos(query: str, raw_event_title: str, max_results: int = 3):
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "key_youtube_cua_ban":
        print("\n Chưa cấu hình YOUTUBE_API_KEY hợp lệ trong file .env!")
        return [], True

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 10,
        "order": "relevance",
        "regionCode": "VN",
        "relevanceLanguage": "vi",
        "videoEmbeddable": "true",
        "key": YOUTUBE_API_KEY
    }

    try:
        res = requests.get(YT_SEARCH_URL, params=params, timeout=12)
        
        if res.status_code in (403, 429):
            err_data = res.json().get("error", {})
            reasons = [e.get("reason") for e in err_data.get("errors", [])]
            if "quotaExceeded" in reasons or "rateLimitExceeded" in reasons:
                return [], True
            print(f"\n Lỗi quyền API ({res.status_code}): {err_data.get('message')}")
            return [], True

        if res.status_code == 200:
            items = res.json().get("items", [])
            trusted_list = []
            standard_list = []
            seen_ids = set()

            for item in items:
                vid_id = item["id"].get("videoId")
                if vid_id in seen_ids:
                    continue

                video_data, is_trusted = evaluate_video(item, raw_event_title)
                if video_data:
                    seen_ids.add(vid_id)
                    if is_trusted:
                        trusted_list.append(video_data)
                    else:
                        standard_list.append(video_data)

            # Ưu tiên gom video từ kênh uy tín trước
            selected = trusted_list[:max_results]
            if len(selected) < max_results:
                needed = max_results - len(selected)
                selected.extend(standard_list[:needed])

            return selected, False

    except Exception as e:
        print(f"\n Lỗi kết nối mạng: {e}")

    return [], False

def run_youtube_crawler(videos_per_event: int = 3):
    db = SessionLocal()
    try:
        all_events = db.query(SuKien).order_by(SuKien.id.asc()).all()
        if not all_events:
            print(" Bảng 'su_kien' đang trống! Hãy cào sự kiện trước.")
            return

        # -------------------------------------------------------------
        # CẢI TIẾN 1: Lấy cả ID đã có video VÀ ID đã xác nhận không có video
        # -------------------------------------------------------------
        checked_event_ids = {
            r.id_sukien for r in db.query(Media.id_sukien).filter(
                Media.loai_media.in_(["YOUTUBE_VIDEO", "NO_VIDEO"])
            ).all()
        }

        events_to_process = [ev for ev in all_events if ev.id not in checked_event_ids]
        total_todo = len(events_to_process)

        if total_todo == 0:
            print(f" Toàn bộ {len(all_events)} sự kiện đều đã được quét xong trong cơ sở dữ liệu.")
            return

        added_video_count = 0
        events_with_video_count = 0
        no_video_count = 0
        quota_ran_out = False

        print(f" Bắt đầu cào video YouTube cho {total_todo} sự kiện (Mục tiêu: {videos_per_event} video/sự kiện)...")

        for idx, ev in enumerate(events_to_process, 1):
            sys.stdout.write(f"\r Đang lọc video: {idx}/{total_todo} | Đã thêm: {added_video_count} video | ID:{ev.id:04d} ({ev.ten_sukien[:22]:<22})")
            sys.stdout.flush()

            clean_name = clean_event_keyword(ev.ten_sukien)
            year_str = f"năm {abs(ev.nam_dien_ra)} TCN" if (ev.nam_dien_ra and ev.nam_dien_ra < 0) else (f"năm {ev.nam_dien_ra}" if ev.nam_dien_ra else "")
            
            # Cú pháp tìm kiếm tối ưu cho tư liệu lịch sử
            search_query = f"Lịch sử Việt Nam {clean_name} {year_str} tư liệu".strip()

            video_list, is_quota_exceeded = search_youtube_videos(search_query, ev.ten_sukien, max_results=videos_per_event)

            if is_quota_exceeded:
                quota_ran_out = True
                break

            # Nếu truy vấn kèm chữ 'tư liệu' không có kết quả hợp chuẩn, thử lại 1 lần với tên mộc
            if not video_list:
                retry_query = f"Lịch sử {clean_name}".strip()
                video_list, is_quota_exceeded = search_youtube_videos(retry_query, ev.ten_sukien, max_results=videos_per_event)
                if is_quota_exceeded:
                    quota_ran_out = True
                    break
                
            if video_list:
                for v in video_list:
                    db.add(Media(
                        id_sukien=ev.id,
                        loai_media="YOUTUBE_VIDEO",
                        url_link=v["url"],
                        tieu_de=v["title"],
                        nguon_goc=v["channel"],
                        is_thumbnail=False
                    ))
                db.commit()
                added_video_count += len(video_list)
                events_with_video_count += 1
            else:
                db.add(Media(
                    id_sukien=ev.id,
                    loai_media="NO_VIDEO",
                    url_link="NONE",
                    tieu_de="Không tìm thấy video hợp chuẩn",
                    nguon_goc="SYSTEM",
                    is_thumbnail=False
                ))
                db.commit()
                no_video_count += 1

            time.sleep(0.15)

        print("\n" + "=" * 65)
        if quota_ran_out:
            print(" THÔNG BÁO: Đã chạm giới hạn Quota hàng ngày (10.000 units) của YouTube Data API v3.")
            print(f" Kết quả đợt này: Đã xử lý {events_with_video_count} sự kiện (thêm {added_video_count} video), đánh dấu bỏ qua {no_video_count} sự kiện không có tư liệu.")
            print(" Google sẽ tự động đặt lại Quota vào khoảng 14:00 - 15:00 hàng ngày (giờ VN).")
            print(" Lần chạy kế tiếp sẽ tự động bắt đầu từ các sự kiện còn thiếu mà không trùng lặp.")
        else:
            print(f" HOÀN TẤT: Đã quét hết danh sách. Thêm thành công {added_video_count} video!")
        print("=" * 65)

    except Exception as e:
        db.rollback()
        print(f"\n Lỗi ngoài ý muốn: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_youtube_crawler(videos_per_event=3)
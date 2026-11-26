import argparse
import sys
import os
import time
import html
import math
import re
import logging
from collections import Counter
import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.ERROR)
logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

from sqlalchemy.orm import sessionmaker
from database_config import engine, GiaiDoanLichSu, SuKien, Media

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

# 2. BLACKLIST TỪ KHÓA LOẠI BỎ RÁC (Review phim, Spoil, Game, Parody, Shorts, BĐS/Đường phố)
STRICT_BLACKLIST = [
    "review phim", "tóm tắt phim", "spoil phim", "giải mã phim", "hậu trường phim",
    "phim chiếu rạp", "trailer", "teaser", "full movie", "tập 1", "tập 2", "tập cuối",
    "phim truyện", "phim bộ", "trích đoạn phim", "hoạt hình chế",
    "reaction", "phản ứng", "nhạc chế", "rap về", "mv chính thức", "official mv",
    "gameplay", "mod game", "mô phỏng game", "total war", "hoi4",
    "shorts", "#shorts", "tiktok", "thuyết âm mưu", "bí ẩn rùng rợn",
    # Rác đời sống / giao thông / bất động sản trùng tên đường phố danh nhân
    "bđs", "bất động sản", "nhà đất", "đất nền", "chung cư", "mua bán nhà",
    "mở rộng đường", "đại phẫu đường", "giải phóng mặt bằng", "gpmb", "quy hoạch đường",
    "tắc đường", "ùn tắc", "kẹt xe", "ngập lụt", "tai nạn giao thông",
    "ẩm thực", "review quán", "ăn sập", "quán ngon", "đặc sản",
    "khách sạn", "homestay", "check in", "phố đi bộ",
    "bóng đá", "v-league", "u23", "highlights",
    "karaoke", "bolero", "remix", "cover", "livestream", "live stream",
    "xổ số", "chứng khoán", "giá vàng"
]

# Rác lịch sử nước ngoài (chỉ chặn khi không thuộc tên sự kiện/giai đoạn gốc)
FOREIGN_HISTORY_BLACKLIST = [
    "lịch sử trung quốc", "sử trung quốc", "trung hoa cổ đại",
    "tam quốc", "tam quốc diễn nghĩa", "đông chu", "xuân thu", "chiến quốc",
    "tần thủy hoàng", "hán sở", "từ hi thái hậu", "võ tắc thiên",
    "khổng minh", "gia cát lượng", "tào tháo", "lưu bị",
    "thế chiến", "chiến tranh thế giới", "ww1", "ww2", "hitler", "đức quốc xã",
    "la mã", "hy lạp", "ai cập", "ba tư", "napoleon", "cách mạng pháp",
    "chiến tranh triều tiên", "lịch sử nhật bản", "samurai", "shogun",
    "lịch sử châu âu", "lịch sử nước mỹ", "nội chiến mỹ",
    "nga - ukraine", "nga ukraine", "israel", "palestine"
]

# Từ cấu trúc chung không mang tính định danh duy nhất cho sự kiện
GENERIC_PREFIX_STOPWORDS = {
    "trận", "chiến", "dịch", "tranh", "khởi", "nghĩa", "phong", "trào",
    "hội", "nghị", "hiệp", "định", "sự", "kiện", "cuộc", "thời", "kỳ",
    "lần", "thứ", "năm", "của", "và", "các", "trong", "về"
}

# Tín hiệu ngữ cảnh lịch sử bắt buộc với kênh ngoài Whitelist
HISTORY_CONTEXT_SIGNALS = [
    "lịch sử", "sử việt", "sử ký", "sử lược", "tư liệu", "phim tài liệu", "tài liệu",
    "khởi nghĩa", "chiến dịch", "trận đánh", "chiến tranh", "kháng chiến", "cách mạng",
    "chiến thắng", "đại thắng", "triều đại", "danh tướng", "tướng quân", "anh hùng",
    "vua ", "hoàng đế", "nhà vua", "đại việt", "đại cồ việt", "âu lạc", "văn lang",
    "bắc thuộc", "tây sơn", "phong kiến", "thuộc địa", "tcn", "trcn",
    "giải phóng", "độc lập", "hiệp định", "hội nghị", "di tích", "đền thờ", "thần tích", "cổ sử",
    "chống pháp", "chống mỹ", "chống tống", "chống nguyên", "chống minh", "chống thanh", "chống hán"
]

STREET_NOISE_PREFIXES = (
    "đường", "phố", "ngõ", "hẻm", "quận", "phường", "tuyến đường", "cầu", "dự án", "chung cư"
)

_MONTH_WORD_TO_NUM = {
    "tháng một": "tháng 1", "tháng hai": "tháng 2", "tháng ba": "tháng 3",
    "tháng tư": "tháng 4", "tháng năm": "tháng 5", "tháng sáu": "tháng 6",
    "tháng bảy": "tháng 7", "tháng tám": "tháng 8", "tháng chín": "tháng 9",
    "tháng mười": "tháng 10", "tháng mười một": "tháng 11", "tháng mười hai": "tháng 12",
}

def clean_event_keyword(title: str) -> str:
    clean = re.sub(r"\(.*?\)", "", title)
    clean = re.sub(r"\[.*?\]", "", clean)
    return clean.strip().lower()

def _normalize_month_words(text: str) -> str:
    out = text.lower()
    for word, num in _MONTH_WORD_TO_NUM.items():
        out = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", num, out)
    return out

def _tokenize(text: str) -> list:
    return re.findall(r"[^\W_]+", _normalize_month_words(text), flags=re.UNICODE)

def _contains_phrase(text: str, phrase_tokens: list) -> bool:
    if not phrase_tokens:
        return False
    norm_text = _normalize_month_words(text)
    pattern = r"(?<!\w)" + r"[\s\-–—,:;|/]+".join(re.escape(t) for t in phrase_tokens) + r"(?!\w)"
    return re.search(pattern, norm_text) is not None

def evaluate_video_relevance(
    raw_title: str,
    channel_name: str,
    raw_event_title: str,
    event_year: int = None,
    era_name: str = None,
):
    """
    Đánh giá mức độ liên quan của video với sự kiện lịch sử Việt Nam.
    Trả về tuple: (is_valid: bool, is_trusted: bool, reason: str)
    """
    clean_title = html.unescape(raw_title or "").strip()
    title_lower = clean_title.lower()
    channel_lower = (channel_name or "").strip().lower()
    combined_lower = f"{title_lower} {channel_lower}"

    if not clean_title:
        return False, False, "empty_title"

    # Lớp 1A: Diệt từ khóa rác giải trí, game, BĐS, đường phố
    for bad in STRICT_BLACKLIST:
        if bad in combined_lower:
            return False, False, f"blacklist:{bad}"

    clean_event = clean_event_keyword(raw_event_title)
    event_context_lower = f"{raw_event_title or ''} {era_name or ''}".lower()

    # Lớp 1B: Diệt từ khóa lịch sử nước ngoài (trừ khi trùng ngữ cảnh sự kiện gốc)
    for foreign_kw in FOREIGN_HISTORY_BLACKLIST:
        if foreign_kw in title_lower and foreign_kw not in event_context_lower:
            return False, False, f"foreign_history:{foreign_kw}"

    all_event_tokens = [t for t in _tokenize(clean_event) if not (t.isdigit() and len(t) == 4)]
    core_tokens = [t for t in all_event_tokens if t not in GENERIC_PREFIX_STOPWORDS]
    if not core_tokens:
        core_tokens = all_event_tokens
    if not core_tokens:
        return False, False, "empty_event_tokens"

    # Lớp 1C: Chặn địa danh đường/phố/quận trùng tên danh nhân (VD: "đường Tam Trinh", "phố Hai Bà Trưng")
    core_phrase_regex = r"[\s\-–—]+".join(re.escape(t) for t in core_tokens)
    for prefix in STREET_NOISE_PREFIXES:
        if prefix not in clean_event:
            if re.search(rf"(?<!\w){re.escape(prefix)}\s+{core_phrase_regex}(?!\w)", _normalize_month_words(title_lower)):
                return False, False, f"street_noise:{prefix}"

    title_tokens = set(_tokenize(title_lower))
    is_trusted = any(rep_ch in channel_lower for rep_ch in REPUTABLE_CHANNELS)

    # Kiểm tra tín hiệu lịch sử (dùng cho nguồn ngoài whitelist & lọc tin tức năm hiện đại)
    has_history_signal = any(sig in combined_lower for sig in HISTORY_CONTEXT_SIGNALS)
    has_exact_year = bool(
        event_year is not None
        and abs(event_year) >= 100
        and re.search(rf"(?<!\d){abs(event_year)}(?!\d)", title_lower)
    )
    if has_exact_year:
        has_history_signal = True

    # Lớp 2: Kiểm tra khớp từ định danh cốt lõi (không dùng substring lỏng lẻo)
    has_full_event_phrase = _contains_phrase(title_lower, all_event_tokens)
    has_core_phrase = _contains_phrase(title_lower, core_tokens)
    matched_core = sum(1 for t in core_tokens if t in title_tokens)

    if len(core_tokens) == 1:
        # Tên chỉ còn 1 từ định danh (VD: "Hiệp định Paris 1973" -> ["paris"]): phải khớp cụm đầy đủ hoặc kèm năm/tiền tố gốc
        prefix_tokens = [t for t in all_event_tokens if t in GENERIC_PREFIX_STOPWORDS]
        core_match_ok = has_full_event_phrase or (
            matched_core == 1 and (has_exact_year or any(pt in title_tokens for pt in prefix_tokens))
        )
    elif len(core_tokens) == 2:
        # Tên ngắn 2 từ định danh (VD: "Tam Trinh", "Bạch Đằng", "Đổi Mới"): bắt buộc khớp trọn vẹn cả 2 từ
        core_match_ok = has_core_phrase or (matched_core == 2 and ("–" in clean_event or "-" in clean_event))
    elif len(core_tokens) == 3:
        min_needed = 2 if is_trusted else 3
        core_match_ok = has_core_phrase or matched_core >= min_needed
    else:
        ratio = 0.6 if is_trusted else 0.75
        min_needed = max(2, math.ceil(len(core_tokens) * ratio))
        core_match_ok = has_full_event_phrase or has_core_phrase or matched_core >= min_needed

    if not core_match_ok:
        return False, is_trusted, f"weak_match:{matched_core}/{len(core_tokens)}"

    # Lớp 3: Với nguồn ngoài Whitelist, bắt buộc phải có ngữ cảnh lịch sử/tư liệu
    if not is_trusted and not has_history_signal:
        return False, False, "missing_history_context"

    # Lớp 4: Chặn tin tức đời sống năm hiện đại (2020..2029) cho sự kiện trước năm 2000 nếu thiếu ngữ cảnh lịch sử
    if event_year is not None and event_year < 2000 and not has_history_signal:
        if re.search(r"(?<!\d)202[0-9](?!\d)", title_lower):
            return False, is_trusted, "modern_news_year"

    return True, is_trusted, "ok"

def evaluate_video(item: dict, raw_event_title: str, event_year: int = None, era_name: str = None):
    raw_title = item["snippet"].get("title", "")
    clean_title = html.unescape(raw_title).strip()
    channel_name = item["snippet"].get("channelTitle", "").strip()
    vid_id = item["id"].get("videoId")

    if not vid_id:
        return None, False

    is_valid, is_trusted, _ = evaluate_video_relevance(
        raw_title=clean_title,
        channel_name=channel_name,
        raw_event_title=raw_event_title,
        event_year=event_year,
        era_name=era_name,
    )
    if not is_valid:
        return None, False

    return {
        "url": f"https://www.youtube.com/watch?v={vid_id}",
        "title": clean_title,
        "channel": channel_name
    }, is_trusted

def search_youtube_videos(
    query: str,
    raw_event_title: str,
    max_results: int = 3,
    event_year: int = None,
    era_name: str = None,
):
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
            try:
                err_data = res.json().get("error", {})
            except ValueError:
                err_data = {}
            reasons = [e.get("reason") for e in err_data.get("errors", []) if isinstance(e, dict)]
            if "quotaExceeded" in reasons or "rateLimitExceeded" in reasons:
                return [], True
            print(f"\n Lỗi quyền API ({res.status_code}): {err_data.get('message') or res.text[:200]}")
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

                video_data, is_trusted = evaluate_video(
                    item,
                    raw_event_title,
                    event_year=event_year,
                    era_name=era_name,
                )
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
        era_map = {
            e.id: e.ten_giai_doan
            for e in db.query(GiaiDoanLichSu.id, GiaiDoanLichSu.ten_giai_doan).all()
        }
        all_events = (
            db.query(SuKien.id, SuKien.ten_sukien, SuKien.nam_dien_ra, SuKien.id_giai_doan)
            .order_by(SuKien.id.asc())
            .all()
        )
        if not all_events:
            print(" Bảng 'su_kien' đang trống! Hãy cào sự kiện trước.")
            return

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
            era_name = era_map.get(ev.id_giai_doan)
            year_str = f"năm {abs(ev.nam_dien_ra)} TCN" if (ev.nam_dien_ra and ev.nam_dien_ra < 0) else (f"năm {ev.nam_dien_ra}" if ev.nam_dien_ra else "")
            quoted_name = f'"{clean_name}"' if len(clean_name.split()) <= 3 else clean_name

            # Cú pháp tìm kiếm tối ưu cho tư liệu lịch sử (khóa cụm tên ngắn trong ngoặc kép)
            search_query = f"Lịch sử Việt Nam {quoted_name} {year_str} tư liệu".strip()

            video_list, is_quota_exceeded = search_youtube_videos(
                search_query,
                ev.ten_sukien,
                max_results=videos_per_event,
                event_year=ev.nam_dien_ra,
                era_name=era_name,
            )

            if is_quota_exceeded:
                quota_ran_out = True
                break

            # Nếu truy vấn kèm chữ 'tư liệu' không có kết quả hợp chuẩn, thử lại 1 lần với cụm sự kiện + lịch sử Việt Nam
            if not video_list:
                retry_query = f"{quoted_name} lịch sử Việt Nam".strip()
                video_list, is_quota_exceeded = search_youtube_videos(
                    retry_query,
                    ev.ten_sukien,
                    max_results=videos_per_event,
                    event_year=ev.nam_dien_ra,
                    era_name=era_name,
                )
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

def clean_irrelevant_videos(apply: bool = False, sample_limit: int = 40, event_id: int = None) -> int:
    """
    Quét toàn bộ bản ghi YOUTUBE_VIDEO trong bảng media (0 tốn quota API).
    - apply=False (--clean-dry-run): chỉ in báo cáo các video lệch chủ đề.
    - apply=True (--clean / --clean-only): xóa các video lệch chủ đề khỏi bảng media.
    """
    db = SessionLocal()
    try:
        query = (
            db.query(
                Media.id.label("media_id"),
                Media.id_sukien,
                Media.tieu_de,
                Media.nguon_goc,
                SuKien.ten_sukien,
                SuKien.nam_dien_ra,
                GiaiDoanLichSu.ten_giai_doan,
            )
            .join(SuKien, Media.id_sukien == SuKien.id)
            .outerjoin(GiaiDoanLichSu, SuKien.id_giai_doan == GiaiDoanLichSu.id)
            .filter(Media.loai_media == "YOUTUBE_VIDEO")
        )
        if event_id is not None:
            query = query.filter(Media.id_sukien == event_id)

        rows = query.order_by(Media.id_sukien.asc(), Media.id.asc()).all()
        kept_per_event = Counter()
        total_per_event = Counter()
        reason_counts = Counter()
        flagged = []

        for r in rows:
            total_per_event[r.id_sukien] += 1
            is_valid, _, reason = evaluate_video_relevance(
                raw_title=r.tieu_de or "",
                channel_name=r.nguon_goc or "",
                raw_event_title=r.ten_sukien or "",
                event_year=r.nam_dien_ra,
                era_name=r.ten_giai_doan,
            )
            if is_valid:
                kept_per_event[r.id_sukien] += 1
            else:
                reason_counts[reason] += 1
                flagged.append((r, reason))

        events_emptied = sum(1 for eid in total_per_event if kept_per_event[eid] == 0)
        print("=" * 72)
        print(f"DỌN VIDEO RÁC ({'XÓA THẬT' if apply else 'DRY-RUN - CHỈ XEM'})")
        print(f"Tổng đã quét: {len(rows)} | Hợp lệ: {len(rows) - len(flagged)} | Lệch chủ đề: {len(flagged)} | Sự kiện về 0 video: {events_emptied}")
        print("=" * 72)

        if reason_counts:
            for reason, count in reason_counts.most_common(10):
                print(f"  - {reason:<35}: {count}")

        if flagged and sample_limit != 0:
            show_n = len(flagged) if sample_limit < 0 else min(sample_limit, len(flagged))
            for r, reason in flagged[:show_n]:
                print(f"  [media#{r.media_id} | sk#{r.id_sukien}: {r.ten_sukien}] ({reason}) -> {r.tieu_de} [{r.nguon_goc}]")

        if apply and flagged:
            bad_ids = [r.media_id for r, _ in flagged]
            deleted = 0
            for i in range(0, len(bad_ids), 500):
                deleted += (
                    db.query(Media)
                    .filter(Media.id.in_(bad_ids[i:i + 500]))
                    .delete(synchronize_session=False)
                )
            db.commit()
            print(f"Đã xóa {deleted} video lệch chủ đề khỏi bảng 'media'.")
            return deleted
        return 0
    except Exception as e:
        db.rollback()
        print(f"Lỗi khi dọn video rác: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cào và lọc video tư liệu YouTube lịch sử Việt Nam")
    parser.add_argument("--clean-dry-run", action="store_true", help="Chỉ quét báo cáo video lệch chủ đề (0 quota, không xóa)")
    parser.add_argument("--clean-only", action="store_true", help="Xóa video lệch chủ đề trong DB (0 quota, không cào tiếp)")
    parser.add_argument("--clean", action="store_true", help="Xóa video lệch chủ đề trong DB rồi chạy cào bù ngay")
    parser.add_argument("--limit", type=int, default=40, help="Số dòng mẫu in ra khi dọn (-1 = tất cả)")
    parser.add_argument("--event-id", type=int, default=None, help="Chỉ quét dọn 1 sự kiện cụ thể theo ID")
    args = parser.parse_args()

    if args.clean_dry_run:
        clean_irrelevant_videos(apply=False, sample_limit=args.limit, event_id=args.event_id)
    elif args.clean_only:
        clean_irrelevant_videos(apply=True, sample_limit=args.limit, event_id=args.event_id)
    else:
        if args.clean:
            clean_irrelevant_videos(apply=True, sample_limit=args.limit, event_id=args.event_id)
        run_youtube_crawler(videos_per_event=3)
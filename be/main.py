import uuid
import re
import time
from collections import defaultdict
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.dialects.postgresql import insert

from database_config import (
    engine,
    GiaiDoanLichSu,
    SuKien,
    Media,
    LienKetSuKien,
    User,
    TienTrinhDoc
)
from auth_utils import hash_password, verify_password

# Khởi tạo phiên làm việc 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="Lịch Sử VN - Backend API",
    version="2.1",
    description="Hệ thống API hỗ trợ Timeline Pinch-to-Zoom 3 tầng, Offline-First Sync, Auth & Cá nhân hóa Tiến trình đọc"
)

# Cấu hình CORS cho phép Mobile App truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Bật nén GZip cho toàn bộ API (Đặc biệt hiệu quả cho gói Offline-Pack)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 2. Bộ nhớ đệm (In-Memory Cache) giảm tải tuyệt đối cho Supabase
_OVERVIEW_CACHE = {"data": None, "expires_at": 0}
_OFFLINE_PACK_CACHE = {"data": None, "expires_at": 0}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Hàm tự động tìm kiếm các sự kiện có liên quan xuất hiện trong nội dung của bài viết
def inject_inline_event_links(content: str, related_events_list: list) -> str:
    if not content or not related_events_list:
        return content

    # Tạo danh sách các mẫu cần tìm: (chuỗi_cần_tìm, id_sự_kiện_đích)
    patterns_to_link = []
    for rel in related_events_list:
        ev_id = rel["id"]
        ev_title = rel["ten_sukien"].strip()
        ev_year = rel["nam_dien_ra"]

        # 1. Ưu tiên khớp chính xác tên sự kiện trước 
        if len(ev_title) > 3:
            clean_title = re.sub(r"\s*\(\d+\)", "", ev_title).strip()
            patterns_to_link.append((re.escape(ev_title), ev_id))
            if clean_title != ev_title and len(clean_title) > 4:
                patterns_to_link.append((re.escape(clean_title), ev_id))

        # 2. Khớp cụm từ "năm XXXX" 
        if ev_year:
            patterns_to_link.append((rf"năm\s+{ev_year}\b", ev_id))

    # Sắp xếp ưu tiên chuỗi dài trước để tránh cắt nhầm chuỗi con
    patterns_to_link.sort(key=lambda x: len(x[0]), reverse=True)

    linked_ids_done = set()
    modified_content = content

    for pattern_str, target_id in patterns_to_link:
        # Mỗi sự kiện liên quan chỉ cần highlight lần xuất hiện đầu tiên để bài đọc không bị rối mắt
        if target_id in linked_ids_done:
            continue

        regex = re.compile(rf"(?<!>)\b({pattern_str})\b(?![^<]*</a>)", flags=re.IGNORECASE)
        if regex.search(modified_content):
            modified_content = regex.sub(
                rf'<a href="event://{target_id}">\1</a>',
                modified_content,
                count=1
            )
            linked_ids_done.add(target_id)

    return modified_content

# 1. PYDANTIC SCHEMAS
class GiaiDoanResponse(BaseModel):
    id: int
    ten_giai_doan: str
    nam_bat_dau: int
    nam_ket_thuc: int
    mo_ta: Optional[str] = None

    class Config:
        from_attributes = True

class SuKienResponse(BaseModel):
    id: int
    id_giai_doan: Optional[int] = None
    ten_sukien: str
    nam_dien_ra: int
    thang_dien_ra: Optional[int] = None
    ngay_dien_ra: Optional[int] = None
    noi_dung_tom_tat: Optional[str] = None

    class Config:
        from_attributes = True

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    ho_ten: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class ProgressUpdateRequest(BaseModel):
    id_user: uuid.UUID
    id_sukien: int
    toa_do_scroll: int
    phan_tram_hoan_thanh: float
    da_hoan_thanh: bool

# 2. CỤM API TIMELINE ĐA TẦNG (PINCH-TO-ZOOM & STREAM)
@app.get("/api/v1/timeline/overview", tags=["Timeline (Pinch-to-Zoom)"])
def get_timeline_overview(db: Session = Depends(get_db)):
    now = time.time()
    # Nếu dữ liệu đã có sẵn trong RAM và chưa hết hạn -> Trả về ngay lập tức (0ms DB load)
    if _OVERVIEW_CACHE["data"] is not None and now < _OVERVIEW_CACHE["expires_at"]:
        return _OVERVIEW_CACHE["data"]

    eras = db.query(GiaiDoanLichSu).order_by(GiaiDoanLichSu.nam_bat_dau.asc()).all()
    era_stats = (
        db.query(
            SuKien.id_giai_doan,
            func.count(SuKien.id).label("so_su_kien"),
            func.min(SuKien.nam_dien_ra).label("nam_dau_tien"),
            func.max(SuKien.nam_dien_ra).label("nam_cuoi_cung")
        )
        .group_by(SuKien.id_giai_doan)
        .all()
    )
    stats_map = {row.id_giai_doan: row for row in era_stats}

    result = [
        {
            "id": era.id,
            "ten_giai_doan": era.ten_giai_doan,
            "nam_bat_dau": era.nam_bat_dau,
            "nam_ket_thuc": era.nam_ket_thuc,
            "mo_ta": era.mo_ta,
            "so_su_kien": stats_map[era.id].so_su_kien if era.id in stats_map else 0,
            "first_event_year": stats_map[era.id].nam_dau_tien if era.id in stats_map else era.nam_bat_dau,
            "last_event_year": stats_map[era.id].nam_cuoi_cung if era.id in stats_map else era.nam_ket_thuc
        }
        for era in eras
    ]

    # Lưu vào RAM trong 10 phút
    _OVERVIEW_CACHE["data"] = result
    _OVERVIEW_CACHE["expires_at"] = now + 600
    return result


@app.get("/api/v1/timeline/stream", tags=["Timeline (Pinch-to-Zoom)"])
def stream_timeline_events(
    limit: int = Query(20, ge=5, le=100, description="Số sự kiện tải mỗi lượt (mặc định 20)"),
    anchor_era_id: Optional[int] = Query(None, description="ID giai đoạn khi người dùng đặt 2 ngón tay zoom"),
    anchor_year: Optional[int] = Query(None, description="Năm cụ thể khi nhảy điểm neo"),
    cursor_year: Optional[int] = Query(None, description="Năm của sự kiện ở mép màn hình dùng làm con trỏ"),
    cursor_id: Optional[int] = Query(None, description="ID của sự kiện ở mép màn hình dùng làm con trỏ"),
    direction: str = Query("down", pattern="^(down|up)$", description="'down': cuộn xuống tương lai | 'up': vuốt ngược về quá khứ"),
    db: Session = Depends(get_db)
):
    base_query = (
        db.query(
            SuKien.id,
            SuKien.id_giai_doan,
            GiaiDoanLichSu.ten_giai_doan,
            GiaiDoanLichSu.nam_bat_dau.label("era_start"),
            GiaiDoanLichSu.nam_ket_thuc.label("era_end"),
            SuKien.ten_sukien,
            SuKien.nam_dien_ra,
            SuKien.thang_dien_ra,
            SuKien.ngay_dien_ra,
            SuKien.noi_dung_tom_tat,
            Media.url_link.label("thumbnail_url")
        )
        .outerjoin(GiaiDoanLichSu, SuKien.id_giai_doan == GiaiDoanLichSu.id)
        .outerjoin(Media, (Media.id_sukien == SuKien.id) & (Media.is_thumbnail == True))
    )

    # KỊCH BẢN 1: Bắt đầu Zoom từ 1 Giai đoạn 
    if cursor_year is None or cursor_id is None:
        start_year = anchor_year
        anchor_era_info = None

        if anchor_era_id is not None:
            era_obj = db.query(GiaiDoanLichSu).filter(GiaiDoanLichSu.id == anchor_era_id).first()
            if not era_obj:
                raise HTTPException(status_code=404, detail="Không tìm thấy giai đoạn lịch sử này")
            
            anchor_era_info = {
                "id": era_obj.id,
                "ten_giai_doan": era_obj.ten_giai_doan,
                "nam_bat_dau": era_obj.nam_bat_dau,
                "nam_ket_thuc": era_obj.nam_ket_thuc
            }
            if start_year is None:
                # Tìm sự kiện đầu tiên của giai đoạn được chọn để ghim lên đỉnh màn hình
                first_ev_in_era = (
                    db.query(SuKien.nam_dien_ra, SuKien.id)
                    .filter(SuKien.id_giai_doan == anchor_era_id)
                    .order_by(
                        SuKien.nam_dien_ra.asc(),
                        SuKien.thang_dien_ra.asc().nulls_last(),
                        SuKien.ngay_dien_ra.asc().nulls_last(),
                        SuKien.id.asc()
                    )
                    .first()
                )
                start_year = first_ev_in_era.nam_dien_ra if first_ev_in_era else era_obj.nam_bat_dau

        if start_year is not None:
            query = base_query.filter(SuKien.nam_dien_ra >= start_year)
        else:
            query = base_query

        events = (
            query.order_by(
                SuKien.nam_dien_ra.asc(),
                SuKien.thang_dien_ra.asc().nulls_last(),
                SuKien.ngay_dien_ra.asc().nulls_last(),
                SuKien.id.asc()
            )
            .limit(limit)
            .all()
        )

    # KỊCH BẢN 2: Người dùng vuốt XUỐNG DƯỚI (tải tiếp tương lai)
    elif direction == "down":
        anchor_era_info = None
        events = (
            base_query.filter(
                or_(
                    SuKien.nam_dien_ra > cursor_year,
                    and_(SuKien.nam_dien_ra == cursor_year, SuKien.id > cursor_id)
                )
            )
            .order_by(
                SuKien.nam_dien_ra.asc(),
                SuKien.thang_dien_ra.asc().nulls_last(),
                SuKien.ngay_dien_ra.asc().nulls_last(),
                SuKien.id.asc()
            )
            .limit(limit)
            .all()
        )

    # KỊCH BẢN 3: Người dùng vuốt NGƯỢC LÊN TRÊN (xem các năm của giai đoạn trước đó)
    else:
        anchor_era_info = None
        events = (
            base_query.filter(
                or_(
                    SuKien.nam_dien_ra < cursor_year,
                    and_(SuKien.nam_dien_ra == cursor_year, SuKien.id < cursor_id)
                )
            )
            .order_by(
                SuKien.nam_dien_ra.desc(),
                SuKien.thang_dien_ra.desc().nulls_first(),
                SuKien.ngay_dien_ra.desc().nulls_first(),
                SuKien.id.desc()
            )
            .limit(limit)
            .all()
        )
        # Đảo ngược lại để giữ đúng chiều thời gian từ trên xuống dưới
        events = list(reversed(events))

    # Kiểm tra xem còn dữ liệu ở phía trên (quá khứ) và phía dưới (tương lai) không
    has_more_up = False
    has_more_down = False
    prev_cursor = None
    next_cursor = None

    if events:
        first_ev = events[0]
        last_ev = events[-1]
        prev_cursor = {"cursor_year": first_ev.nam_dien_ra, "cursor_id": first_ev.id}
        next_cursor = {"cursor_year": last_ev.nam_dien_ra, "cursor_id": last_ev.id}

        has_more_up = (
            db.query(SuKien.id)
            .filter(
                or_(
                    SuKien.nam_dien_ra < first_ev.nam_dien_ra,
                    and_(SuKien.nam_dien_ra == first_ev.nam_dien_ra, SuKien.id < first_ev.id)
                )
            )
            .first() is not None
        )
        has_more_down = (
            db.query(SuKien.id)
            .filter(
                or_(
                    SuKien.nam_dien_ra > last_ev.nam_dien_ra,
                    and_(SuKien.nam_dien_ra == last_ev.nam_dien_ra, SuKien.id > last_ev.id)
                )
            )
            .first() is not None
        )

    # Gom nhóm danh sách phẳng thành cả dạng Flat Items lẫn Year Groups để UI dễ dàng vẽ trục Năm
    year_groups_dict = defaultdict(list)
    flat_items = []

    for e in events:
        item_data = {
            "id": e.id,
            "id_giai_doan": e.id_giai_doan,
            "ten_giai_doan": e.ten_giai_doan,
            "ten_sukien": e.ten_sukien,
            "nam_dien_ra": e.nam_dien_ra,
            "thang_dien_ra": e.thang_dien_ra,
            "ngay_dien_ra": e.ngay_dien_ra,
            "noi_dung_tom_tat": e.noi_dung_tom_tat,
            "thumbnail_url": e.thumbnail_url
        }
        flat_items.append(item_data)
        year_groups_dict[e.nam_dien_ra].append(item_data)

    year_blocks = [
        {
            "nam": y,
            "id_giai_doan": ev_list[0]["id_giai_doan"],
            "ten_giai_doan": ev_list[0]["ten_giai_doan"],
            "has_month_detail": any(ev["thang_dien_ra"] is not None for ev in ev_list),
            "so_su_kien": len(ev_list),
            "events": ev_list
        }
        for y, ev_list in year_groups_dict.items()
    ]

    return {
        "anchor_era": anchor_era_info,
        "direction": direction,
        "count": len(flat_items),
        "has_more_up": has_more_up,
        "has_more_down": has_more_down,
        "prev_cursor": prev_cursor,
        "next_cursor": next_cursor,
        "year_blocks": year_blocks,  # Dùng để vẽ các cột mốc Năm nối tiếp dưới Giai đoạn
        "items": flat_items          # Dùng nếu Paging3 / RecyclerView quản lý theo phẳng
    }


@app.get("/api/v1/timeline/year-detail/{year}", tags=["Timeline (Pinch-to-Zoom)"])
def get_year_month_breakdown(year: int, db: Session = Depends(get_db)):
    events = (
        db.query(
            SuKien.id,
            SuKien.id_giai_doan,
            GiaiDoanLichSu.ten_giai_doan,
            SuKien.ten_sukien,
            SuKien.nam_dien_ra,
            SuKien.thang_dien_ra,
            SuKien.ngay_dien_ra,
            SuKien.noi_dung_tom_tat,
            Media.url_link.label("thumbnail_url")
        )
        .outerjoin(GiaiDoanLichSu, SuKien.id_giai_doan == GiaiDoanLichSu.id)
        .outerjoin(Media, (Media.id_sukien == SuKien.id) & (Media.is_thumbnail == True))
        .filter(SuKien.nam_dien_ra == year)
        .order_by(
            SuKien.thang_dien_ra.asc().nulls_last(),
            SuKien.ngay_dien_ra.asc().nulls_last(),
            SuKien.id.asc()
        )
        .all()
    )

    if not events:
        raise HTTPException(status_code=404, detail=f"Không có sự kiện nào trong năm {year}")

    has_month_data = any(e.thang_dien_ra is not None for e in events)
    months_dict = defaultdict(list)

    for e in events:
        m_key = e.thang_dien_ra if e.thang_dien_ra is not None else 0
        months_dict[m_key].append({
            "id": e.id,
            "ten_sukien": e.ten_sukien,
            "nam_dien_ra": e.nam_dien_ra,
            "thang_dien_ra": e.thang_dien_ra,
            "ngay_dien_ra": e.ngay_dien_ra,
            "noi_dung_tom_tat": e.noi_dung_tom_tat,
            "thumbnail_url": e.thumbnail_url
        })

    # Sắp xếp các tháng từ 1 -> 12, các sự kiện chưa rõ tháng (m_key = 0) xếp cuối
    sorted_month_keys = sorted(months_dict.keys(), key=lambda x: (x == 0, x))

    return {
        "year": year,
        "id_giai_doan": events[0].id_giai_doan,
        "ten_giai_doan": events[0].ten_giai_doan,
        "can_zoom_to_months": has_month_data,
        "zoom_state": "MONTH_BREAKDOWN" if has_month_data else "LOCKED_AT_YEAR",
        "total_events": len(events),
        "months": [
            {
                "thang": m if m != 0 else None,
                "label": f"Tháng {m}" if m != 0 else f"Diễn ra trong năm {year} (Chưa rõ tháng)",
                "events": months_dict[m]
            }
            for m in sorted_month_keys
        ]
    }

# 3. CHI TIẾT SỰ KIỆN, MEDIA, NHÂN QUẢ & TÌM KIẾM
@app.get("/api/v1/events/search", tags=["Events"])
def search_events(
    q: str = Query(..., min_length=1, description="Từ khóa tên sự kiện hoặc số năm"),
    limit: int = 20,
    db: Session = Depends(get_db)
):
    keyword = f"%{q.strip()}%"
    query = (
        db.query(
            SuKien.id,
            SuKien.id_giai_doan,
            GiaiDoanLichSu.ten_giai_doan,
            SuKien.ten_sukien,
            SuKien.nam_dien_ra,
            SuKien.thang_dien_ra,
            SuKien.ngay_dien_ra,
            SuKien.noi_dung_tom_tat,
            Media.url_link.label("thumbnail_url")
        )
        .outerjoin(GiaiDoanLichSu, SuKien.id_giai_doan == GiaiDoanLichSu.id)
        .outerjoin(Media, (Media.id_sukien == SuKien.id) & (Media.is_thumbnail == True))
    )

    if q.strip().lstrip("-").isdigit():
        year_val = int(q.strip())
        results = query.filter(SuKien.nam_dien_ra == year_val).limit(limit).all()
    else:
        results = (
            query.filter(
                or_(
                    SuKien.ten_sukien.ilike(keyword),
                    SuKien.noi_dung_tom_tat.ilike(keyword)
                )
            )
            .order_by(SuKien.nam_dien_ra.asc(), SuKien.id.asc())
            .limit(limit)
            .all()
        )

    return [
        {
            "id": r.id,
            "id_giai_doan": r.id_giai_doan,
            "ten_giai_doan": r.ten_giai_doan,
            "ten_sukien": r.ten_sukien,
            "nam_dien_ra": r.nam_dien_ra,
            "thang_dien_ra": r.thang_dien_ra,
            "ngay_dien_ra": r.ngay_dien_ra,
            "noi_dung_tom_tat": r.noi_dung_tom_tat,
            "thumbnail_url": r.thumbnail_url
        }
        for r in results
    ]


@app.get("/api/v1/events/{event_id}", tags=["Events"])
def get_event_detail(event_id: int, db: Session = Depends(get_db)):
    event = db.query(SuKien).filter(SuKien.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Không tìm thấy sự kiện")

    era = db.query(GiaiDoanLichSu).filter(GiaiDoanLichSu.id == event.id_giai_doan).first()
    medias = db.query(Media).filter(
        Media.id_sukien == event_id,
        Media.loai_media != "NO_VIDEO"
    ).all()

    related_rows = (
        db.query(
            LienKetSuKien.loai_lien_ket,
            SuKien.id,
            SuKien.ten_sukien,
            SuKien.nam_dien_ra
        )
        .join(SuKien, LienKetSuKien.id_sukien_lien_quan == SuKien.id)
        .filter(LienKetSuKien.id_sukien_goc == event_id)
        .order_by(SuKien.nam_dien_ra.asc())
        .all()
    )

    related_grouped = defaultdict(list)
    flat_related = []
    for rel in related_rows:
        rel_item = {
            "id": rel.id,
            "ten_sukien": rel.ten_sukien,
            "nam_dien_ra": rel.nam_dien_ra
        }
        related_grouped[rel.loai_lien_ket].append(rel_item)
        flat_related.append(rel_item)

    # Tạo phiên bản nội dung đã được nhúng sẵn thẻ highlight liên kết
    highlighted_content = inject_inline_event_links(event.noi_dung_chi_tiet, flat_related)

    return {
        "id": event.id,
        "ten_sukien": event.ten_sukien,
        "giai_doan": {
            "id": era.id if era else None,
            "ten_giai_doan": era.ten_giai_doan if era else None
        },
        "nam_dien_ra": event.nam_dien_ra,
        "thang_dien_ra": event.thang_dien_ra,
        "ngay_dien_ra": event.ngay_dien_ra,
        "noi_dung_tom_tat": event.noi_dung_tom_tat,
        "noi_dung_chi_tiet": event.noi_dung_chi_tiet,               
        "noi_dung_chi_tiet_linked": highlighted_content,            
        "media": [
            {
                "id": m.id,
                "loai_media": m.loai_media,
                "url_link": m.url_link,
                "tieu_de": m.tieu_de,
                "is_thumbnail": m.is_thumbnail,
                "nguon_goc": m.nguon_goc
            }
            for m in medias
        ],
        "lien_ket_su_kien": related_grouped
    }

# 4. ĐỒNG BỘ OFFLINE-FIRST CHO ROOM DATABASE (PHỤC VỤ TÙNG)
@app.get("/api/v1/sync/offline-pack", tags=["Offline Sync (Room DB)"])
def get_offline_sync_pack(
    since_year: Optional[int] = Query(None, description="Tùy chọn lọc từ một năm cụ thể nếu muốn tải từng phần"),
    db: Session = Depends(get_db)
):
    now = time.time()
    # Nếu tải toàn bộ (không lọc năm) và đã có trong RAM Cache -> trả về ngay lập tức
    if since_year is None and _OFFLINE_PACK_CACHE["data"] is not None and now < _OFFLINE_PACK_CACHE["expires_at"]:
        return _OFFLINE_PACK_CACHE["data"]

    eras = db.query(GiaiDoanLichSu).order_by(GiaiDoanLichSu.nam_bat_dau.asc()).all()

    ev_query = (
        db.query(
            SuKien.id,
            SuKien.id_giai_doan,
            SuKien.ten_sukien,
            SuKien.nam_dien_ra,
            SuKien.thang_dien_ra,
            SuKien.ngay_dien_ra,
            SuKien.noi_dung_tom_tat,
            SuKien.noi_dung_chi_tiet,
            Media.url_link.label("thumbnail_url")
        )
        .outerjoin(Media, (Media.id_sukien == SuKien.id) & (Media.is_thumbnail == True))
    )

    if since_year is not None:
        ev_query = ev_query.filter(SuKien.nam_dien_ra >= since_year)

    events = (
        ev_query.order_by(
            SuKien.nam_dien_ra.asc(),
            SuKien.thang_dien_ra.asc().nulls_last(),
            SuKien.ngay_dien_ra.asc().nulls_last(),
            SuKien.id.asc()
        )
        .all()
    )

    links = db.query(
        LienKetSuKien.id_sukien_goc,
        LienKetSuKien.id_sukien_lien_quan,
        LienKetSuKien.loai_lien_ket
    ).all()

    payload = {
        "synced_at": int(now),
        "total_eras": len(eras),
        "total_events": len(events),
        "eras": [
            {
                "id": era.id,
                "ten_giai_doan": era.ten_giai_doan,
                "nam_bat_dau": era.nam_bat_dau,
                "nam_ket_thuc": era.nam_ket_thuc,
                "mo_ta": era.mo_ta
            }
            for era in eras
        ],
        "events": [
            {
                "id": ev.id,
                "id_giai_doan": ev.id_giai_doan,
                "ten_sukien": ev.ten_sukien,
                "nam_dien_ra": ev.nam_dien_ra,
                "thang_dien_ra": ev.thang_dien_ra,
                "ngay_dien_ra": ev.ngay_dien_ra,
                "noi_dung_tom_tat": ev.noi_dung_tom_tat,
                "noi_dung_chi_tiet": ev.noi_dung_chi_tiet,
                "thumbnail_url": ev.thumbnail_url
            }
            for ev in events
        ],
        "links": [
            {
                "id_sukien_goc": lk.id_sukien_goc,
                "id_sukien_lien_quan": lk.id_sukien_lien_quan,
                "loai_lien_ket": lk.loai_lien_ket
            }
            for lk in links
        ]
    }

    if since_year is None:
        # Lưu vào RAM Cache trong 30 phút (1800 giây)
        _OFFLINE_PACK_CACHE["data"] = payload
        _OFFLINE_PACK_CACHE["expires_at"] = now + 1800

    return payload

# 5. XÁC THỰC NGƯỜI DÙNG & TIẾN TRÌNH ĐỌC
@app.post("/api/v1/auth/register", tags=["Auth"])
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter((User.username == req.username) | (User.email == req.email)).first():
        raise HTTPException(status_code=400, detail="Tên đăng nhập hoặc email đã tồn tại")

    new_user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        ho_ten=req.ho_ten,
        role="USER"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "message": "Đăng ký thành công",
        "user_id": str(new_user.id),
        "username": new_user.username,
        "ho_ten": new_user.ho_ten,
        "role": new_user.role
    }


@app.post("/api/v1/auth/login", tags=["Auth"])
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai tài khoản hoặc mật khẩu")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản này hiện đang bị khóa")

    return {
        "message": "Đăng nhập thành công",
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "ho_ten": user.ho_ten,
        "role": user.role
    }


@app.get("/api/v1/auth/session/{user_id}", tags=["Auth"])
def verify_saved_session(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc tài khoản đã bị khóa"
        )
    return {
        "valid": True,
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "ho_ten": user.ho_ten,
        "role": user.role
    }


@app.post("/api/v1/reading-progress", tags=["Reading Progress"])
def save_reading_progress(req: ProgressUpdateRequest, db: Session = Depends(get_db)):
    stmt = insert(TienTrinhDoc).values(
        id_user=req.id_user,
        id_sukien=req.id_sukien,
        toa_do_scroll=req.toa_do_scroll,
        phan_tram_hoan_thanh=req.phan_tram_hoan_thanh,
        da_hoan_thanh=req.da_hoan_thanh
    ).on_conflict_do_update(
        constraint="uq_user_sukien",
        set_={
            "toa_do_scroll": req.toa_do_scroll,
            "phan_tram_hoan_thanh": req.phan_tram_hoan_thanh,
            "da_hoan_thanh": req.da_hoan_thanh,
            "last_read_at": func.now()
        }
    )
    db.execute(stmt)
    db.commit()
    return {
        "message": "Cập nhật tiến trình đọc thành công",
        "id_user": str(req.id_user),
        "id_sukien": req.id_sukien,
        "da_hoan_thanh": req.da_hoan_thanh
    }


@app.get("/api/v1/reading-progress/{user_id}/summary", tags=["Reading Progress"])
def get_user_reading_summary(
    user_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50, description="Số bài vừa đọc gần đây muốn hiển thị"),
    db: Session = Depends(get_db)
):
    total_system_events = db.query(func.count(SuKien.id)).scalar() or 995

    completed_count = (
        db.query(func.count(TienTrinhDoc.id))
        .filter(TienTrinhDoc.id_user == user_id, TienTrinhDoc.da_hoan_thanh == True)
        .scalar() or 0
    )

    in_progress_count = (
        db.query(func.count(TienTrinhDoc.id))
        .filter(TienTrinhDoc.id_user == user_id, TienTrinhDoc.da_hoan_thanh == False)
        .scalar() or 0
    )

    recent_rows = (
        db.query(
            TienTrinhDoc.id_sukien,
            SuKien.ten_sukien,
            SuKien.nam_dien_ra,
            GiaiDoanLichSu.ten_giai_doan,
            TienTrinhDoc.toa_do_scroll,
            TienTrinhDoc.phan_tram_hoan_thanh,
            TienTrinhDoc.da_hoan_thanh,
            TienTrinhDoc.last_read_at,
            Media.url_link.label("thumbnail_url")
        )
        .join(SuKien, TienTrinhDoc.id_sukien == SuKien.id)
        .outerjoin(GiaiDoanLichSu, SuKien.id_giai_doan == GiaiDoanLichSu.id)
        .outerjoin(Media, (Media.id_sukien == SuKien.id) & (Media.is_thumbnail == True))
        .filter(TienTrinhDoc.id_user == user_id)
        .order_by(TienTrinhDoc.last_read_at.desc())
        .limit(limit)
        .all()
    )

    recent_list = [
        {
            "id_sukien": r.id_sukien,
            "ten_sukien": r.ten_sukien,
            "nam_dien_ra": r.nam_dien_ra,
            "ten_giai_doan": r.ten_giai_doan,
            "toa_do_scroll": r.toa_do_scroll,
            "phan_tram_hoan_thanh": r.phan_tram_hoan_thanh,
            "da_hoan_thanh": r.da_hoan_thanh,
            "quiz_unlocked": r.da_hoan_thanh,  # Cờ báo cho Tùng biết sự kiện này đã đủ điều kiện mở câu hỏi ôn tập chưa
            "last_read_at": r.last_read_at,
            "thumbnail_url": r.thumbnail_url
        }
        for r in recent_rows
    ]

    return {
        "user_id": str(user_id),
        "total_system_events": total_system_events,
        "completed_events": completed_count,
        "in_progress_events": in_progress_count,
        "completion_percentage": round((completed_count / total_system_events) * 100, 2) if total_system_events else 0.0,
        "last_active_event": recent_list[0] if recent_list else None,  # Sự kiện vừa đọc gần nhất để khôi phục nhanh
        "recent_history": recent_list
    }


@app.get("/api/v1/reading-progress/{user_id}/{event_id}", tags=["Reading Progress"])
def get_reading_progress(user_id: uuid.UUID, event_id: int, db: Session = Depends(get_db)):
    progress = (
        db.query(TienTrinhDoc)
        .filter(TienTrinhDoc.id_user == user_id, TienTrinhDoc.id_sukien == event_id)
        .first()
    )
    if not progress:
        return {
            "id_sukien": event_id,
            "toa_do_scroll": 0,
            "phan_tram_hoan_thanh": 0.0,
            "da_hoan_thanh": False,
            "quiz_unlocked": False
        }
    return {
        "id_sukien": progress.id_sukien,
        "toa_do_scroll": progress.toa_do_scroll,
        "phan_tram_hoan_thanh": progress.phan_tram_hoan_thanh,
        "da_hoan_thanh": progress.da_hoan_thanh,
        "quiz_unlocked": progress.da_hoan_thanh,
        "last_read_at": progress.last_read_at
    }
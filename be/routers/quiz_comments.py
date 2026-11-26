import sys
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from database_config import (
    engine,
    quiz_engine,
    User,
    CauHoiQuiz,
    CauHoiOnTap,
    KetQuaQuiz,
    BinhLuan,
)

# Giới hạn số nguyên 32-bit (INT4) của PostgreSQL để tránh DataError 500
PG_INT_MIN = -2_147_483_648
PG_INT_MAX = 2_147_483_647

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
QuizSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=quiz_engine)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_quiz_db():
    db = QuizSessionLocal()
    try:
        yield db
    finally:
        db.close()


class QuizResultCreateRequest(BaseModel):
    id_user: uuid.UUID
    id_sukien: Optional[int] = Field(None, ge=PG_INT_MIN, le=PG_INT_MAX)
    loai_quiz: str = Field("EVENT_QUIZ", max_length=30)
    diem_so: int = Field(..., ge=0, le=PG_INT_MAX)
    tong_so_cau: int = Field(..., ge=1, le=PG_INT_MAX)
    danh_gia: Optional[str] = Field(None, max_length=500)


class CommentCreateRequest(BaseModel):
    id_sukien: int = Field(..., ge=PG_INT_MIN, le=PG_INT_MAX)
    id_user: uuid.UUID
    noi_dung: str = Field(..., min_length=1, max_length=2000)
    ten_hien_thi: Optional[str] = Field(None, max_length=100)


def serialize_question(q) -> dict:
    """Chuẩn hóa dữ liệu câu hỏi trắc nghiệm từ bảng cau_hoi_quiz hoặc cau_hoi_on_tap."""
    return {
        "id": q.id,
        "id_sukien": q.id_sukien,
        "cau_hoi": q.cau_hoi,
        "dap_an_a": q.dap_an_a,
        "dap_an_b": q.dap_an_b,
        "dap_an_c": q.dap_an_c,
        "dap_an_d": q.dap_an_d,
        "dap_an_dung": q.dap_an_dung,
        "giai_thich": q.giai_thich,
    }


def serialize_quiz_result(r: KetQuaQuiz) -> dict:
    """Chuẩn hóa dữ liệu kết quả làm bài Quiz."""
    return {
        "id": r.id,
        "id_user": str(r.id_user),
        "id_sukien": r.id_sukien,
        "loai_quiz": r.loai_quiz,
        "diem_so": r.diem_so,
        "tong_so_cau": r.tong_so_cau,
        "phan_tram_dung": r.phan_tram_dung,
        "danh_gia": r.danh_gia,
        "completed_at": r.completed_at,
    }


def serialize_comment(c: BinhLuan) -> dict:
    """Chuẩn hóa dữ liệu bình luận cho màn hình diễn đàn."""
    return {
        "id": c.id,
        "id_sukien": c.id_sukien,
        "id_user": str(c.id_user),
        "ten_hien_thi": c.ten_hien_thi,
        "noi_dung": c.noi_dung,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def _apply_rate_limit(request: Request, scope: str, max_calls: int, window_sec: int):
    """Dùng chung bộ giới hạn tần suất theo IP từ main.py để tránh lặp trạng thái RAM."""
    main_mod = sys.modules.get("main") or sys.modules.get("__main__")
    checker = getattr(main_mod, "_check_rate_limit", None)
    if checker is not None:
        checker(request, scope, max_calls=max_calls, window_sec=window_sec)


# 6. API QUIZ LUYỆN TẬP SỰ KIỆN & CÂU HỎI ÔN TẬP TỔNG HỢP (ĐỌC TỪ DB TÙNG)

@router.get("/api/v1/quiz/event/{event_id}", tags=["Quiz (Luyện tập Sự kiện)"])
def get_event_quiz(
    event_id: int = Path(..., ge=PG_INT_MIN, le=PG_INT_MAX),
    db: Session = Depends(get_quiz_db),
):
    """Lấy câu hỏi Quiz dành riêng cho 1 sự kiện từ bảng cau_hoi_quiz."""
    questions = (
        db.query(CauHoiQuiz)
        .filter(CauHoiQuiz.id_sukien == event_id)
        .order_by(CauHoiQuiz.id.asc())
        .all()
    )
    return {
        "event_id": event_id,
        "total_questions": len(questions),
        "questions": [serialize_question(q) for q in questions],
    }


@router.get("/api/v1/cau-hoi-on-tap/all", tags=["Câu Hỏi Ôn Tập (Tổng hợp)"])
def get_all_questions(db: Session = Depends(get_quiz_db)):
    """Lấy toàn bộ danh sách câu hỏi ôn tập từ bảng cau_hoi_on_tap."""
    questions = db.query(CauHoiOnTap).order_by(CauHoiOnTap.id.asc()).all()
    return {
        "total_questions": len(questions),
        "questions": [serialize_question(q) for q in questions],
    }


@router.get("/api/v1/cau-hoi-on-tap/random", tags=["Câu Hỏi Ôn Tập (Tổng hợp)"])
def get_random_questions(
    limit: int = Query(10, ge=1, le=100, description="Số lượng câu hỏi ngẫu nhiên cần lấy"),
    db: Session = Depends(get_quiz_db),
):
    """Lấy ngẫu nhiên N câu hỏi ôn tập từ bảng cau_hoi_on_tap."""
    questions = db.query(CauHoiOnTap).order_by(func.random()).limit(limit).all()
    return {
        "total_questions": len(questions),
        "questions": [serialize_question(q) for q in questions],
    }


# 7. API KẾT QUẢ QUIZ & THEO DÕI TIẾN ĐỘ LÀM BÀI

@router.post("/api/v1/quiz/results", status_code=status.HTTP_201_CREATED, tags=["Quiz Results (Tiến độ Quiz)"])
def save_quiz_result(
    req: QuizResultCreateRequest,
    request: Request,
    quiz_db: Session = Depends(get_quiz_db),
):
    """Lưu kết quả làm bài Quiz/Ôn tập để theo dõi tiến độ học tập của người dùng."""
    _apply_rate_limit(request, "quiz_results_create", max_calls=30, window_sec=60)

    if req.tong_so_cau <= 0:
        raise HTTPException(status_code=400, detail="Tổng số câu phải lớn hơn 0")
    if req.diem_so < 0 or req.diem_so > req.tong_so_cau:
        raise HTTPException(status_code=400, detail="Điểm số không hợp lệ (phải nằm trong khoảng 0..tong_so_cau)")

    loai_quiz = req.loai_quiz.strip().upper()
    if loai_quiz not in ("EVENT_QUIZ", "ON_TAP"):
        raise HTTPException(status_code=400, detail="loai_quiz chỉ hỗ trợ 'EVENT_QUIZ' hoặc 'ON_TAP'")

    phan_tram = round((req.diem_so / req.tong_so_cau) * 100, 2)
    danh_gia = req.danh_gia.strip() if req.danh_gia else None
    if not danh_gia:
        if phan_tram >= 80:
            danh_gia = "Xuất sắc! Bạn đã nắm vững kiến thức lịch sử."
        elif phan_tram >= 50:
            danh_gia = "Khá tốt! Hãy ôn tập thêm để đạt điểm tối đa."
        else:
            danh_gia = "Cần ôn tập lại nội dung sự kiện này."

    new_result = KetQuaQuiz(
        id_user=req.id_user,
        id_sukien=req.id_sukien,
        loai_quiz=loai_quiz,
        diem_so=req.diem_so,
        tong_so_cau=req.tong_so_cau,
        phan_tram_dung=phan_tram,
        danh_gia=danh_gia,
    )
    quiz_db.add(new_result)
    try:
        quiz_db.commit()
    except IntegrityError:
        quiz_db.rollback()
        raise HTTPException(status_code=400, detail="Không thể lưu kết quả Quiz do lỗi ràng buộc dữ liệu")
    quiz_db.refresh(new_result)

    return {
        "message": "Lưu kết quả Quiz thành công",
        "result": serialize_quiz_result(new_result),
    }


@router.get("/api/v1/quiz/results/{user_id}", tags=["Quiz Results (Tiến độ Quiz)"])
def get_user_quiz_results(
    user_id: uuid.UUID,
    event_id: Optional[int] = Query(None, ge=PG_INT_MIN, le=PG_INT_MAX, description="Lọc lịch sử theo 1 sự kiện cụ thể"),
    limit: int = Query(20, ge=1, le=100, description="Số lần làm bài gần nhất"),
    quiz_db: Session = Depends(get_quiz_db),
):
    """Lấy thống kê tiến độ làm Quiz và lịch sử các lần làm bài của người dùng."""
    base_query = quiz_db.query(KetQuaQuiz).filter(KetQuaQuiz.id_user == user_id)
    if event_id is not None:
        base_query = base_query.filter(KetQuaQuiz.id_sukien == event_id)

    all_attempts = base_query.order_by(KetQuaQuiz.completed_at.desc(), KetQuaQuiz.id.desc()).all()
    total_attempts = len(all_attempts)
    passed_attempts = sum(1 for a in all_attempts if a.phan_tram_dung >= 50.0)
    avg_percentage = round(sum(a.phan_tram_dung for a in all_attempts) / total_attempts, 2) if total_attempts else 0.0
    best_percentage = max((a.phan_tram_dung for a in all_attempts), default=0.0)
    completed_event_ids = sorted({a.id_sukien for a in all_attempts if a.id_sukien is not None and a.phan_tram_dung >= 50.0})

    return {
        "user_id": str(user_id),
        "total_attempts": total_attempts,
        "passed_attempts": passed_attempts,
        "average_percentage": avg_percentage,
        "best_percentage": best_percentage,
        "completed_event_ids": completed_event_ids,
        "history": [serialize_quiz_result(a) for a in all_attempts[:limit]],
    }


# 8. API DIỄN ĐÀN BÌNH LUẬN THEO SỰ KIỆN

@router.get("/api/v1/comments/event/{event_id}", tags=["Comments (Diễn đàn Bình luận)"])
def get_event_comments(
    event_id: int = Path(..., ge=PG_INT_MIN, le=PG_INT_MAX),
    page: int = Query(1, ge=1, le=10000, description="Trang hiện tại (bắt đầu từ 1)"),
    limit: int = Query(20, ge=1, le=100, description="Số bình luận mỗi trang"),
    quiz_db: Session = Depends(get_quiz_db),
):
    """Lấy danh sách bình luận theo sự kiện có phân trang."""
    base_query = quiz_db.query(BinhLuan).filter(BinhLuan.id_sukien == event_id)
    total_comments = base_query.count()
    offset = (page - 1) * limit
    rows = (
        base_query.order_by(BinhLuan.created_at.desc(), BinhLuan.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "event_id": event_id,
        "page": page,
        "limit": limit,
        "total_comments": total_comments,
        "has_more": (offset + len(rows)) < total_comments,
        "comments": [serialize_comment(c) for c in rows],
    }


@router.post("/api/v1/comments", status_code=status.HTTP_201_CREATED, tags=["Comments (Diễn đàn Bình luận)"])
def create_comment(
    req: CommentCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    quiz_db: Session = Depends(get_quiz_db),
):
    """Đăng bình luận mới cho một sự kiện lịch sử."""
    _apply_rate_limit(request, "comments_create", max_calls=20, window_sec=60)

    clean_content = req.noi_dung.strip()
    if not clean_content:
        raise HTTPException(status_code=400, detail="Nội dung bình luận không được để trống")

    display_name = req.ten_hien_thi.strip() if req.ten_hien_thi else None
    if not display_name:
        try:
            user = db.query(User).filter(User.id == req.id_user).first()
            display_name = (user.ho_ten or user.username) if user else "Người dùng ẩn danh"
        except SQLAlchemyError:
            db.rollback()
            display_name = "Người dùng ẩn danh"
    display_name = display_name[:100]

    comment = BinhLuan(
        id_sukien=req.id_sukien,
        id_user=req.id_user,
        ten_hien_thi=display_name,
        noi_dung=clean_content,
    )
    quiz_db.add(comment)
    try:
        quiz_db.commit()
    except IntegrityError:
        quiz_db.rollback()
        raise HTTPException(status_code=400, detail="Không thể đăng bình luận do lỗi ràng buộc dữ liệu")
    quiz_db.refresh(comment)

    return {
        "message": "Đăng bình luận thành công",
        "comment": serialize_comment(comment),
    }


@router.delete("/api/v1/comments/{comment_id}", tags=["Comments (Diễn đàn Bình luận)"])
def delete_comment(
    comment_id: int = Path(..., ge=PG_INT_MIN, le=PG_INT_MAX),
    user_id: uuid.UUID = Query(..., description="ID người dùng để xác thực quyền xóa"),
    quiz_db: Session = Depends(get_quiz_db),
):
    """Xóa bình luận của chính người dùng."""
    comment = quiz_db.query(BinhLuan).filter(BinhLuan.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Không tìm thấy bình luận")
    if comment.id_user != user_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xóa bình luận này")

    quiz_db.delete(comment)
    quiz_db.commit()
    return {"message": "Đã xóa bình luận thành công", "deleted_id": comment_id}

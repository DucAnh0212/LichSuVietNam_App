from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session, sessionmaker
from pydantic import BaseModel
from typing import List, Optional

# Import engine và các Class Bảng từ file database.py của bạn
from database_config import engine, GiaiDoanLichSu, SuKien 

# Khởi tạo phiên làm việc (Session) với PostgreSQL
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Khởi tạo ứng dụng FastAPI
app = FastAPI(title="Lịch Sử VN - Backend API", version="1.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# PYDANTIC SCHEMAS (Quy định định dạng JSON trả về cho Mobile)
class GiaiDoanResponse(BaseModel):
    id: int
    ten_giai_doan: str
    nam_bat_dau: int
    nam_ket_thuc: int
    loai_hinh: Optional[str] = None

    class Config:
        from_attributes = True 

class SuKienResponse(BaseModel):
    id: int
    ten_sukien: str
    nam_dien_ra: int
    thang_dien_ra: Optional[int] = None
    noi_dung_tom_tat: Optional[str] = None

    class Config:
        from_attributes = True

# API ENDPOINTS (Các đường dẫn cho Frontend gọi)

@app.get("/api/giai-doan", response_model=List[GiaiDoanResponse])
def get_danh_sach_giai_doan(db: Session = Depends(get_db)):
    giai_doan = db.query(GiaiDoanLichSu).order_by(GiaiDoanLichSu.nam_bat_dau).all()
    return giai_doan

@app.get("/api/su-kien", response_model=List[SuKienResponse])
def get_danh_sach_su_kien(page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
    offset = (page - 1) * limit
    su_kien = db.query(SuKien).order_by(SuKien.nam_dien_ra).offset(offset).limit(limit).all()
    return su_kien
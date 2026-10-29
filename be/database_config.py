import os
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, DateTime, BigInteger, Float, UniqueConstraint, func  
from sqlalchemy.orm import declarative_base  
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg2://admin:secretpassword@localhost:5433/lichsuvn_db"
)

engine = create_engine(DATABASE_URL, echo=False) 
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    ho_ten = Column(String(100), nullable=True)
    role = Column(String(20), default="USER")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Quan hệ với tiến trình đọc
    tien_trinh = relationship("TienTrinhDoc", back_populates="user", cascade="all, delete-orphan")

class TienTrinhDoc(Base):
    __tablename__ = "tien_trinh_doc"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    id_user = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    id_sukien = Column(Integer, ForeignKey("su_kien.id", ondelete="CASCADE"), nullable=False, index=True)
    toa_do_scroll = Column(Integer, default=0)
    phan_tram_hoan_thanh = Column(Float, default=0.0)
    da_hoan_thanh = Column(Boolean, default=False)
    last_read_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("id_user", "id_sukien", name="uq_user_sukien"),
    )

    user = relationship("User", back_populates="tien_trinh")
    su_kien = relationship("SuKien")

class GiaiDoanLichSu(Base):
    __tablename__ = 'giai_doan_lich_su'
    id = Column(Integer, primary_key=True, autoincrement=True)
    ten_giai_doan = Column(String(255), nullable=False)
    nam_bat_dau = Column(Integer, nullable=False)
    nam_ket_thuc = Column(Integer, nullable=False)
    loai_hinh = Column(String(50)) 
    mo_ta_ngan = Column(Text)

class SuKien(Base):
    __tablename__ = 'su_kien'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_giai_doan = Column(Integer, ForeignKey('giai_doan_lich_su.id'), nullable=True)
    
    ten_sukien = Column(String(255), nullable=False, index=True)
    nam_dien_ra = Column(Integer, nullable=False, index=True)
    thang_dien_ra = Column(Integer, nullable=True)
    ngay_dien_ra = Column(Integer, nullable=True)
    
    noi_dung_tom_tat = Column(Text)
    noi_dung_chi_tiet = Column(Text)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class LienKetSuKien(Base):
    __tablename__ = 'lien_ket_su_kien'
    id_sukien_goc = Column(Integer, ForeignKey('su_kien.id'), primary_key=True)
    id_sukien_lien_quan = Column(Integer, ForeignKey('su_kien.id'), primary_key=True)
    loai_lien_ket = Column(String(50), nullable=False) 

class Media(Base):
    __tablename__ = 'media'
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_sukien = Column(Integer, ForeignKey('su_kien.id'), nullable=False)
    loai_media = Column(String(50), nullable=False) # 'IMAGE', 'YOUTUBE_VIDEO'
    url_link = Column(Text, nullable=False)
    nguon_goc = Column(String(255))
    tieu_de = Column(Text, nullable=True)
    is_thumbnail = Column(Boolean, default=False)
    
if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Khởi tạo thành công! Hãy mở pgAdmin để kiểm tra.")
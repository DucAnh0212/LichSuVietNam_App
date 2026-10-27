import sys
import os

# Thêm đường dẫn thư mục gốc (be/) vào sys.path để import được database_config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import sessionmaker
from database_config import engine, GiaiDoanLichSu

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DANH_SACH_GIAI_DOAN = [
    # I. CỔ ĐẠI
    {"ten": "Thời kỳ Hồng Bàng & Văn Lang", "bat_dau": -2879, "ket_thuc": -258, "loai": "CO_DAI", "mo_ta": "Thời kỳ hình thành nhà nước đầu tiên của người Việt cổ dưới thời các Vua Hùng."},
    {"ten": "Thời kỳ Âu Lạc (An Dương Vương)", "bat_dau": -257, "ket_thuc": -207, "loai": "CO_DAI", "mo_ta": "Thục Phán hợp nhất Âu Việt và Lạc Việt, lập nước Âu Lạc, xây thành Cổ Loa."},
    {"ten": "Bắc thuộc lần 1 (Nhà Triệu & Hán)", "bat_dau": -207, "ket_thuc": 39, "loai": "BAC_THUOC", "mo_ta": "Giai đoạn từ khi Triệu Đà sáp nhập Âu Lạc đến trước cuộc khởi nghĩa Hai Bà Trưng."},
    
    # II. CHỐNG BẮC THUỘC & TỰ CHỦ
    {"ten": "Trưng Nữ Vương (Hai Bà Trưng)", "bat_dau": 40, "ket_thuc": 43, "loai": "TU_CHU", "mo_ta": "Hai Bà Trưng phất cờ khởi nghĩa đánh đuổi quân Đông Hán, giành quyền tự chủ."},
    {"ten": "Thời kỳ Bắc thuộc lần 2", "bat_dau": 43, "ket_thuc": 543, "loai": "BAC_THUOC", "mo_ta": "Giai đoạn đô hộ của các triều đại phương Bắc từ Đông Hán đến nhà Lương, nổi bật với khởi nghĩa Bà Triệu."},
    {"ten": "Nhà Tiền Lý & Nước Vạn Xuân", "bat_dau": 544, "ket_thuc": 602, "loai": "TU_CHU", "mo_ta": "Lý Bí khởi nghĩa thắng lợi, xưng Lý Nam Đế, đặt quốc hiệu Vạn Xuân."},
    {"ten": "Thời kỳ Bắc thuộc lần 3", "bat_dau": 602, "ket_thuc": 905, "loai": "BAC_THUOC", "mo_ta": "Thời kỳ đô hộ của nhà Tùy, Đường với các cuộc khởi nghĩa lớn của Mai Thúc Loan, Phùng Hưng."},
    {"ten": "Thời kỳ Tự chủ (Họ Khúc, Họ Dương)", "bat_dau": 905, "ket_thuc": 938, "loai": "TU_CHU", "mo_ta": "Khúc Thừa Dụ dựng quyền tự chủ, khép lại bằng chiến thắng Bạch Đằng năm 938 của Ngô Quyền."},

    # III. PHONG KIẾN ĐỘC LẬP
    {"ten": "Nhà Ngô, Loạn 12 Sứ quân & Nhà Đinh", "bat_dau": 939, "ket_thuc": 980, "loai": "PHONG_KIEN", "mo_ta": "Ngô Quyền xưng vương, tiếp nối bởi Đinh Bộ Lĩnh dẹp loạn 12 sứ quân, lập nước Đại Cồ Việt."},
    {"ten": "Nhà Tiền Lê", "bat_dau": 980, "ket_thuc": 1009, "loai": "PHONG_KIEN", "mo_ta": "Lê Hoàn lên ngôi (Lê Đại Hành), phá Tống bình Chiêm, củng cố nền độc lập."},
    {"ten": "Nhà Lý", "bat_dau": 1009, "ket_thuc": 1225, "loai": "PHONG_KIEN", "mo_ta": "Lý Thái Tổ dời đô về Thăng Long, đổi quốc hiệu Đại Việt, mở ra kỷ nguyên văn minh rực rỡ."},
    {"ten": "Nhà Trần", "bat_dau": 1225, "ket_thuc": 1400, "loai": "PHONG_KIEN", "mo_ta": "Triều đại võ công hiển hách với hào khí Đông A và 3 lần đại thắng quân Nguyên - Mông."},
    {"ten": "Nhà Hồ", "bat_dau": 1400, "ket_thuc": 1407, "loai": "PHONG_KIEN", "mo_ta": "Hồ Quý Ly lập ra nhà Hồ, đổi quốc hiệu Đại Ngu và thực hiện nhiều cải cách táo bạo."},
    {"ten": "Bắc thuộc lần 4 (Nhà Minh đô hộ)", "bat_dau": 1407, "ket_thuc": 1427, "loai": "BAC_THUOC", "mo_ta": "Giai đoạn nhà Minh đô hộ tàn bạo và cuộc khởi nghĩa Lam Sơn hào hùng do Lê Lợi lãnh đạo."},
    {"ten": "Nhà Hậu Lê (Thời Lê Sơ)", "bat_dau": 1428, "ket_thuc": 1527, "loai": "PHONG_KIEN", "mo_ta": "Chế độ phong kiến Đại Việt đạt đến đỉnh cao cực thịnh dưới triều vua Lê Thánh Tông."},
    {"ten": "Nam - Bắc Triều (Lê - Mạc phân tranh)", "bat_dau": 1527, "ket_thuc": 1592, "loai": "PHONG_KIEN", "mo_ta": "Mạc Đăng Dung lập ra nhà Mạc (Bắc triều), đối đầu với lực lượng phù Lê (Nam triều)."},
    {"ten": "Trịnh - Nguyễn phân tranh (Lê Trung Hưng)", "bat_dau": 1593, "ket_thuc": 1777, "loai": "PHONG_KIEN", "mo_ta": "Đất nước chia cắt Đàng Trong (Chúa Nguyễn) - Đàng Ngoài (Vua Lê - Chúa Trịnh), mở mang bờ cõi về phương Nam."},
    {"ten": "Nhà Tây Sơn", "bat_dau": 1778, "ket_thuc": 1802, "loai": "PHONG_KIEN", "mo_ta": "Ba anh em Tây Sơn xóa bỏ chia cắt Đàng Trong - Đàng Ngoài, đại thắng quân Xiêm và quân Thanh."},
    {"ten": "Nhà Nguyễn (Giai đoạn Độc lập)", "bat_dau": 1802, "ket_thuc": 1883, "loai": "PHONG_KIEN", "mo_ta": "Vua Gia Long thống nhất hoàn toàn lãnh thổ, đặt quốc hiệu Việt Nam, đóng đô tại Phú Xuân (Huế)."},

    # IV. CẬN ĐẠI & HIỆN ĐẠI
    {"ten": "Thời kỳ Pháp thuộc", "bat_dau": 1884, "ket_thuc": 1945, "loai": "THUC_DIAN", "mo_ta": "Việt Nam dưới ách bảo hộ của thực dân Pháp và các phong trào yêu nước, cách mạng giải phóng dân tộc."},
    {"ten": "Kháng chiến chống Pháp (VNDCCH)", "bat_dau": 1945, "ket_thuc": 1954, "loai": "CHIEN_TRANH", "mo_ta": "Từ Cách mạng Tháng Tám 1945 đến chiến thắng lịch sử Điện Biên Phủ và Hiệp định Genève 1954."},
    {"ten": "Kháng chiến chống Mỹ cứu nước", "bat_dau": 1954, "ket_thuc": 1975, "loai": "CHIEN_TRANH", "mo_ta": "Đất nước tạm thời chia cắt hai miền, đấu tranh thống nhất đất nước kết thúc bằng Đại thắng mùa Xuân 1975."},
    {"ten": "Thời kỳ Thống nhất & Bao cấp", "bat_dau": 1975, "ket_thuc": 1986, "loai": "HIEN_DAI", "mo_ta": "Tái thiết đất nước sau chiến tranh, thống nhất về mặt nhà nước và bảo vệ biên giới."},
    {"ten": "Thời kỳ Đổi Mới & Hội nhập", "bat_dau": 1986, "ket_thuc": 2026, "loai": "HIEN_DAI", "mo_ta": "Việt Nam tiến hành công cuộc Đổi Mới toàn diện, phát triển kinh tế và hội nhập quốc tế sâu rộng."}
]

def seed_giai_doan():
    db = SessionLocal()
    try:
        # Kiểm tra xem bảng đã có dữ liệu chưa để tránh nhân đôi khi chạy lại
        existing_count = db.query(GiaiDoanLichSu).count()
        if existing_count > 0:
            print(f"[Thông báo] Bảng 'giai_doan_lich_su' đã có sẵn {existing_count} bản ghi. Bỏ qua bước nạp mới.")
            return

        print("Đang nạp 24 giai đoạn lịch sử Việt Nam vào PostgreSQL...")
        for item in DANH_SACH_GIAI_DOAN:
            gd = GiaiDoanLichSu(
                ten_giai_doan=item["ten"],
                nam_bat_dau=item["bat_dau"],
                nam_ket_thuc=item["ket_thuc"],
                loai_hinh=item["loai"],
                mo_ta_ngan=item["mo_ta"]
            )
            db.add(gd)
        
        db.commit()
        print("Thành công! Đã nạp 24 giai đoạn lịch sử vào Database.")
    except Exception as e:
        db.rollback()
        print(f"Lỗi khi nạp dữ liệu: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_giai_doan()
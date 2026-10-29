import sys
import os
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from faker import Faker
from sqlalchemy.orm import sessionmaker
from database_config import engine, User, TienTrinhDoc, SuKien
from auth_utils import hash_password

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
fake = Faker("vi_VN")

TARGET_EVENT_IDS = [
    2, 3, 4, 5, 7, 9, 10, 11, 12, 13, 14, 15, 17, 
    18, 19, 21, 22, 23, 26, 27, 28, 30, 336, 844, 891, 933
]

def seed_users_and_progress():
    db = SessionLocal()
    try:
        # Lọc danh sách ID thực sự tồn tại trong bảng su_kien
        valid_event_ids = [
            r[0] for r in db.query(SuKien.id).filter(SuKien.id.in_(TARGET_EVENT_IDS)).all()
        ]
        if not valid_event_ids:
            print(" Không tìm thấy các ID sự kiện mục tiêu trong cơ sở dữ liệu!")
            return

        print(f" Nhận diện {len(valid_event_ids)} sự kiện mục tiêu để tạo tiến trình đọc.")

        # 1. Tạo 1 tài khoản Test cố định
        test_username = "admin_test"
        existing_test = db.query(User).filter(User.username == test_username).first()
        if not existing_test:
            test_user = User(
                username=test_username,
                email="admin_test@lichsuvn.edu.vn",
                password_hash=hash_password("Test123456"),
                ho_ten="Quản Trị Viên Test",
                role="ADMIN"
            )
            db.add(test_user)
            db.flush()
            created_users = [test_user]
        else:
            created_users = [existing_test]

        # 2. Tạo 100 tài khoản mẫu ngẫu nhiên bằng Faker
        print(" Đang sinh 100 tài khoản người dùng mẫu...")
        for i in range(1, 101):
            uname = f"{fake.user_name()}_{random.randint(100, 999)}"
            email = f"{uname}@{fake.free_email_domain()}"
            random_pwd = fake.password(length=10)

            user = User(
                username=uname,
                email=email,
                password_hash=hash_password(random_pwd),
                ho_ten=fake.name(),
                role="USER"
            )
            db.add(user)
            created_users.append(user)

        db.flush()
        print(f" Đã tạo tổng cộng {len(created_users)} người dùng.")

        # 3. Tạo tiến trình đọc xoay quanh các sự kiện mục tiêu
        print(" Đang sinh dữ liệu tiến trình đọc mẫu...")
        progress_records = []

        for u in created_users:
            num_events_read = random.randint(1, min(5, len(valid_event_ids)))
            selected_events = random.sample(valid_event_ids, num_events_read)

            for ev_id in selected_events:
                is_completed = random.choice([True, False, False]) 
                
                if is_completed:
                    scroll_pos = random.randint(3000, 5000)
                    pct = 1.0
                else:
                    scroll_pos = random.randint(200, 2500)
                    pct = round(random.uniform(0.1, 0.85), 2)

                progress = TienTrinhDoc(
                    id_user=u.id,
                    id_sukien=ev_id,
                    toa_do_scroll=scroll_pos,
                    phan_tram_hoan_thanh=pct,
                    da_hoan_thanh=is_completed,
                    last_read_at=fake.date_time_between(start_date="-30d", end_date="now")
                )
                progress_records.append(progress)

        db.bulk_save_objects(progress_records)
        db.commit()
        print(f"HOÀN TẤT! Đã thêm {len(progress_records)} bản ghi tiến trình đọc vào Supabase.")
        print(f"Tài khoản test dùng để kiểm tra API: Username: 'admin_test' | Mật khẩu: 'Test123456'")

    except Exception as e:
        db.rollback()
        print(f"Lỗi khi sinh dữ liệu: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_users_and_progress()
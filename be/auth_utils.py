import bcrypt

def hash_password(plain_password: str) -> str:
    """Băm mật khẩu văn bản bằng thư viện bcrypt gốc."""
    # Giới hạn tối đa 72 bytes theo chuẩn thiết kế của thuật toán Bcrypt
    pwd_bytes = plain_password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """So khớp mật khẩu người dùng nhập với chuỗi hash trong database."""
    pwd_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False
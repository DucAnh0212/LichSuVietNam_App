# Sử dụng Python 3.11 slim tối ưu dung lượng và tương thích mã nguồn hiện tại
FROM python:3.11-slim

# Thiết lập các biến môi trường cho Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết (gcc, libpq-dev hỗ trợ biên dịch psycopg2, mwparserfromhell...)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài đặt dependencies trước để tối ưu layer caching của Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn backend vào container
COPY . .

# Expose cổng 8000 của FastAPI/Uvicorn
EXPOSE 8000

# Lệnh khởi chạy server FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

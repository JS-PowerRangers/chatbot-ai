import os
from dotenv import load_dotenv

load_dotenv() # Tùy chọn: để load biến môi trường từ file .env

# Lấy API Key từ biến môi trường hoặc điền trực tiếp (không khuyến khích cho production)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "YOUR_GOOGLE_API_KEY_HERE")

# Chuỗi kết nối MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/") # Thay bằng URI của bạn nếu khác
DB_NAME = "cua_hang_db"
COLLECTION_NAME = "san_pham"

# Cấu hình khác (nếu cần)
LANGUAGE_CODE = "vi-VN"
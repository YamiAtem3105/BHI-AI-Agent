import os
import psycopg2
from dotenv import load_dotenv

# Nạp cấu hình từ file .env
env_path=r"D:\Project_LLM\BHI - AI Agent\AI đọc file quản lý nhân sự\POC Demo\Postgres_SQL\postgres.env"
load_dotenv(dotenv_path=env_path)

# Cấu hình kết nối
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

def test_connection():
    print("=== ĐANG THỬ KẾT NỐI POSTGRES ===")
    try:
        # Chỉ thực hiện mở cổng kết nối
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Hỏi phiên bản để xác nhận đã vào được
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        print("[+] KẾT NỐI THÀNH CÔNG!")
        print(f"[+] Đã truy cập: {version[0]}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[X] KẾT NỐI THẤT BẠI: {e}")

def create_tables():
    commands = (
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE,
            chat_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255),
            role VARCHAR(50) DEFAULT 'user',
            token INTEGER DEFAULT 5,
            last_refill_token BIGINT,
            is_processing BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(commands)
        conn.commit()
        cur.close()
        conn.close()
        print("[+] Bảng 'users' đã được kiểm tra/khởi tạo thành công.")
    except Exception as e:
        print(f"[-] Lỗi khởi tạo bảng: {e}")

# Gọi hàm này ngay sau khi kết nối thành công
create_tables()

if __name__ == "__main__":
    test_connection()


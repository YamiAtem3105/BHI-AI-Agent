import gspread
import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# 1. Tự động xác định đường dẫn thư mục chứa file code này
base_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Trỏ đúng đến file nằm trong thư mục con Postgres_SQL
env_path = os.path.join(base_dir, 'postgres.env')

# 3. Load file .env
load_dotenv(dotenv_path=env_path)

# DEBUG: Kiểm tra xem đã load được mật khẩu chưa (nếu ra None là chưa được)
print(f"DEBUG: Đang load từ: {env_path}")
print(f"DEBUG: Mật khẩu đọc được là: {os.getenv('DB_PASSWORD')}")

# Lấy thông tin từ .env
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}


def get_user_by_email(email: str):
    query = "SELECT * FROM users WHERE email = %s;"
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, (email,))
        user = cur.fetchone()

        print(f"DEBUG: Dữ liệu lấy được từ DB: {user}") 
        # ------------------------------------------
        
        cur.close()
        conn.close()
        return user
    except Exception as e:
        print(f"Lỗi: {e}")
        return None
    
if __name__ == "__main__":
    
    test_email = "hoangpm@bicholder.vn" 
    user = get_user_by_email(test_email)
 
    if user:
        print(f"✅ Tìm thấy user: {user.get('name')}")
    else:
        print("❌ Không tìm thấy user trong DB.")
import gspread
import psycopg2
import os
from dotenv import load_dotenv

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


# Đường dẫn file JSON
current_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(current_dir, 'API_credentials.json')

def sync_data():
    try:
        # 1. Kết nối Google Sheet
        gc = gspread.service_account(filename=json_path)
        sh = gc.open_by_key('1IChKyDyGUUHW-rPWNbh1galfiPFhPgnmrAysuikUuP8')
        worksheet = sh.get_worksheet(1)
        data = worksheet.get_all_records()
        
        # 2. Kết nối Database dùng biến môi trường và con trỏ cur
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        

        print(f"Đang đồng bộ {len(data)} nhân sự vào Database...")

        # Duyệt qua từng dòng dữ liệu trong danh sách
        for row in data:
            # Lấy thông tin từ từng cột trong Google Sheet
            # Lưu ý: Tên cột phải khớp với tên trong file Google Sheet của bạn
            
            name = row.get('Nhân sự') 
            email = row.get('Email')
            
            # Kiểm tra xem có email không (vì email sẽ là ID để định danh user)
            if email:
                # Thực hiện lệnh SQL chèn vào bảng
                # %s là tham số để tránh lỗi bảo mật SQL Injection
                cur.execute("""
                    INSERT INTO users (name, email)
                    VALUES (%s, %s)
                    ON CONFLICT (chatid) DO NOTHING;
                """, (name, email))
        
        # Commit: Bắt buộc phải có lệnh này để lưu thay đổi vào DB
        conn.commit()
        print("[+] Đồng bộ hoàn tất!")

        # Đóng kết nối để giải phóng tài nguyên
        cur.close()
        conn.close()

    except Exception as e:
        # Nếu có lỗi (ví dụ sai mật khẩu DB, mất kết nối), nó sẽ báo cho bạn biết
        print(f"[-] Lỗi xảy ra: {e}")

if __name__ == "__main__":
    sync_data()
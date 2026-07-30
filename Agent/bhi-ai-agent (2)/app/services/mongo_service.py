# app/services/mongo_service.py
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from dotenv import load_dotenv

#  Trỏ đúng đến file nằm trong thư mục 
env_path = r'D:\Project_LLM\BHI - AI Agent\AI đọc file quản lý nhân sự\Agent\bhi-ai-agent (2)\.env'

#  Load file .env
load_dotenv(dotenv_path=env_path)

# DEBUG: Kiểm tra xem đã load được mật khẩu chưa (nếu ra None là chưa được)
print(f"DEBUG: Đang load từ: {env_path}")
print(f"DEBUG: Test{os.getenv('MONGO_URL')}")

# Lấy thông tin từ .env
DB_CONFIG = {
    "mongo_db_url" : os.getenv("MONGO_URL")
}

# Khởi tạo Motor Client bằng URL lấy từ DB_CONFIG của ông
MONGO_URL = DB_CONFIG["mongo_db_url"]
client = AsyncIOMotorClient(MONGO_URL)

# Chỉ định Database và Collection (Bảng) để lưu lịch sử
# MongoDB sẽ tự tạo database và collection này nếu chưa có
db = client["bhi_agent_db"]
history_collection = db["chat_histories"]


# --- HÀM 1: LẤY LỊCH SỬ CHAT CŨ ĐỂ NẠP CHO AI ---
async def get_chat_history(session_id: str, limit: int = 10):
    """
    Tìm lại các tin nhắn cũ của đúng phiên chat (session_id) này.
    Sắp xếp theo thời gian và lấy ra tối đa `limit` câu gần nhất.
    """
    if not session_id:
        return []
        
    # Tìm kiếm trong MongoDB: lọc theo session_id, sắp xếp timestamp giảm dần (-1)
    cursor = history_collection.find({"session_id": session_id}).sort("timestamp", -1).limit(limit)
    
    messages = []
    async for doc in cursor:
        messages.append({
            "role": doc["role"],         # 'user' hoặc 'assistant'
            "content": doc["content"]     # nội dung chat
        })
    
    # Vì lấy limit đảo ngược nên mảng đang bị (mới -> cũ)
    # Cần reverse() lại để trả về đúng thứ tự dòng thời gian (cũ -> mới) cho LLM đọc
    messages.reverse()
    return messages


# --- HÀM 2: LƯU TIN NHẮN MỚI VÀO DATABASE ---
async def save_chat_message(session_id: str, role: str, content: str):
    """
    Lưu một tin nhắn mới (của người dùng hoặc của AI) vào MongoDB
    """
    if not session_id or not content:
        return
        
    doc = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow() # Lưu thời gian dạng UTC chuẩn quốc tế
    }
    
    # Lệnh chèn dữ liệu vào MongoDB (vì dùng Motor bất đồng bộ nên phải có await)
    await history_collection.insert_one(doc)
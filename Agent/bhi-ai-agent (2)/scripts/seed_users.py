"""Seed BHI QLXD users into database.

Dữ liệu thật KHÔNG hardcode trong repo. Đặt file data/seed_users.json
(đã .gitignore) theo định dạng data/seed_users.example.json.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import engine, Base, SessionLocal
from app.models.models import User

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _load_users() -> list:
    path = os.path.join(DATA_DIR, "seed_users.json")
    if not os.path.exists(path):
        path = os.path.join(DATA_DIR, "seed_users.example.json")
        print(f"[!] data/seed_users.json không có, dùng mẫu: {os.path.basename(path)}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for u in _load_users():
            if db.query(User).filter(User.email == u["email"]).first():
                continue
            db.add(User(
                display_name=u["display_name"],
                email=u["email"],
                role=u.get("role", "member"),
                department=u.get("department", "QLXD"),
                masterplan_name=u["display_name"],
                personal_sheet_id=u.get("personal_sheet_id", ""),
            ))
        db.commit()
        print(f"Done. {db.query(User).count()} users in database.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

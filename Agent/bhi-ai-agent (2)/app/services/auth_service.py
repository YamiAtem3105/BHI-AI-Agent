from sqlalchemy.orm import Session
from app.models.models import User


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_user(self, email: str, sender_info: dict) -> User | None:
        user = self.db.query(User).filter(User.email == email).first()
        if user:
            if not user.google_chat_id and sender_info.get("name"):
                user.google_chat_id = sender_info["name"]
                self.db.commit()
            return user

        # Try match by display_name
        display_name = sender_info.get("displayName", "")
        user = self.db.query(User).filter(User.display_name == display_name).first()
        if user:
            user.google_chat_id = sender_info.get("name", "")
            if not user.email:
                user.email = email
            self.db.commit()
            return user

        return None

    def get_user_filter(self, user: User) -> dict:
        if user.role in ("admin", "super_admin"):
            return {}
        elif user.role == "manager":
            return {"department": user.department}
        return {"user": user.masterplan_name}

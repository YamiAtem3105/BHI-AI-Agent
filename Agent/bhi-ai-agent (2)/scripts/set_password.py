"""Set/reset a staff password. Usage: python scripts/set_password.py <email> <password>"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.passwords import hash_password

STAFF_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "staff.json")


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/set_password.py <email> <password>")
        sys.exit(1)
    email, password = sys.argv[1].strip().lower(), sys.argv[2]
    with open(STAFF_PATH, encoding="utf-8") as f:
        staff = json.load(f)
    for s in staff:
        if s["email"].lower() == email:
            s["password_hash"] = hash_password(password)
            with open(STAFF_PATH, "w", encoding="utf-8") as f:
                json.dump(staff, f, ensure_ascii=False, indent=2)
            print(f"Password set for {s['name']} <{email}>.")
            return
    print(f"Email not found: {email}")
    sys.exit(1)


if __name__ == "__main__":
    main()

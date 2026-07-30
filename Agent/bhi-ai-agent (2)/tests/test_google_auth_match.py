"""Test match nhân sự cho Google OAuth: theo email + fallback theo tên."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.mock_sheets import get_staff_by_email, get_staff_by_name, get_staff_for_google_login

passed = failed = 0


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS {label}")
    else:
        failed += 1
        print(f"  FAIL {label} | {detail}")


print("=" * 60)
print("1. Match theo EMAIL công ty (acc Google = email staff.json)")
print("=" * 60)
check("1.1 email đúng", (get_staff_by_email("hoangpm@bicholder.vn") or {}).get("name") == "Phan Minh Hoàng")
check("1.2 email hoa-thường", (get_staff_by_email("HoangPM@Bicholder.VN") or {}).get("name") == "Phan Minh Hoàng")
check("1.3 email lạ → None", get_staff_by_email("stranger@gmail.com") is None)

print("=" * 60)
print("2. Fallback match theo TÊN (acc Google cá nhân ≠ email công ty)")
print("=" * 60)
# Tên đúng y hệt
check("2.1 tên có dấu", (get_staff_by_name("Phan Minh Hoàng") or {}).get("email") == "hoangpm@bicholder.vn")
# Google profile thường trả tên KHÔNG dấu
check("2.2 tên không dấu", (get_staff_by_name("Phan Minh Hoang") or {}).get("name") == "Phan Minh Hoàng")
check("2.3 tên không dấu 2", (get_staff_by_name("Nguyen Van Cuong") or {}).get("name") == "Nguyễn Văn Cường")
check("2.4 tên có 'đ'", (get_staff_by_name("Do Thi Bich Hang") or {}).get("name") == "Đỗ Thị Bích Hằng")
# Khác hoa-thường + thừa khoảng trắng
check("2.5 hoa-thường + space", (get_staff_by_name("  ngô thị dung  ") or {}).get("name") == "Ngô Thị Dung")
# Người lạ
check("2.6 tên lạ → None", get_staff_by_name("Elon Musk") is None)
check("2.7 rỗng → None", get_staff_by_name("") is None)
check("2.8 None an toàn", get_staff_by_name("   ") is None)

print("=" * 60)
print("3. get_staff_for_google_login (email → google_email → name)")
print("=" * 60)
s, how = get_staff_for_google_login("hoangpm@bicholder.vn", "Anyone")
check("3.1 email công ty", s and s["name"] == "Phan Minh Hoàng" and how == "email")
s, how = get_staff_for_google_login("nosdevai2k@gmail.com", "")
check("3.2 gmail = email admin", s and s["role"] == "admin" and how == "email")
s, how = get_staff_for_google_login("random.person@gmail.com", "Phan Minh Hoang")
check("3.3 fallback tên Google", s and s["name"] == "Phan Minh Hoàng" and how == "name")
s, how = get_staff_for_google_login("unknown@gmail.com", "Elon Musk")
check("3.4 không khớp", s is None and how == "")

print("=" * 60)
print("4. Mọi nhân sự đều match được theo tên (không dấu)")
print("=" * 60)
import json
import unicodedata

DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
STAFF = json.load(open(os.path.join(DATA, "staff.json"), encoding="utf-8"))


def no_accent(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c)).replace("đ", "d").replace("Đ", "D")


for s in STAFF:
    if s["name"] == "Admin":
        continue
    na = no_accent(s["name"])
    check(f"4.{s['name']}", (get_staff_by_name(na) or {}).get("email") == s["email"],
          f"input={na}")

print("\n" + "=" * 60)
print(f"KẾT QUẢ: {passed} passed, {failed} failed, {passed+failed} total")
print("=" * 60)
if failed:
    sys.exit(1)
print("✅ Google OAuth name/email matching OK")

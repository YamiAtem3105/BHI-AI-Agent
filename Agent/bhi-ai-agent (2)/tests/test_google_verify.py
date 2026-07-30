"""Test verify id_token Google (logic audience + leeway, không gọi Google thật)."""
import os
import sys
import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.api import auth_google
from app.config import settings

passed = failed = 0


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL {label} | {detail}")


private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


class _FakeSigningKey:
    key = public_pem


def _make_token(**extra):
    now = int(time.time())
    payload = {
        "iss": "https://accounts.google.com",
        "aud": settings.google_client_id,
        "email": "test@example.com",
        "email_verified": True,
        "name": "Test User",
        "iat": now,
        "exp": now + 3600,
        **extra,
    }
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-kid"})


auth_google._get_signing_key = lambda _token: _FakeSigningKey()

print("=" * 60)
print("GOOGLE ID TOKEN VERIFY")
print("=" * 60)

claims = auth_google._verify_id_token(_make_token())
check("valid token", claims["email"] == "test@example.com")

claims = auth_google._verify_id_token(_make_token(aud=[settings.google_client_id, "other"]))
check("aud list", claims["aud"] == [settings.google_client_id, "other"])

claims = auth_google._verify_id_token(_make_token(aud="other", azp=settings.google_client_id))
check("azp fallback", claims.get("azp") == settings.google_client_id)

try:
    auth_google._verify_id_token(_make_token(aud="wrong", azp="also-wrong"))
    check("reject bad aud", False, "should raise")
except jwt.InvalidAudienceError:
    check("reject bad aud", True)

check("audience_matches str", auth_google._audience_matches({"aud": settings.google_client_id}, settings.google_client_id))
check("audience_matches azp", auth_google._audience_matches({"aud": "x", "azp": settings.google_client_id}, settings.google_client_id))

print("\n" + "=" * 60)
print(f"KẾT QUẢ: {passed} passed, {failed} failed")
print("=" * 60)
if __name__ == "__main__":
    sys.exit(1 if failed else 0)

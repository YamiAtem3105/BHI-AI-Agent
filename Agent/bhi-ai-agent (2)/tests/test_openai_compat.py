"""Tests OpenAI model compatibility helpers."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.openai_compat import (
    completion_limit_kwargs,
    model_catalog,
    uses_max_completion_tokens,
)

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS {name}")
    else:
        failed += 1
        print(f"  FAIL {name} | {detail}")


print("=" * 60)
print("OPENAI COMPAT")
print("=" * 60)

check("gpt-4o-mini uses max_tokens", not uses_max_completion_tokens("gpt-4o-mini"))
check("gpt-5.4-mini uses max_completion_tokens", uses_max_completion_tokens("gpt-5.4-mini"))
check("gpt-4.1 uses max_completion_tokens", uses_max_completion_tokens("gpt-4.1"))
check("o4-mini uses max_completion_tokens", uses_max_completion_tokens("o4-mini"))

kw = completion_limit_kwargs("gpt-4o-mini", 256)
check("legacy kw has max_tokens", "max_tokens" in kw and kw["max_tokens"] == 256)
check("legacy kw no max_completion_tokens", "max_completion_tokens" not in kw)

kw5 = completion_limit_kwargs("gpt-5.4-mini", 400)
check("new kw has max_completion_tokens", kw5.get("max_completion_tokens") == 400)
check("new kw no max_tokens", "max_tokens" not in kw5)

cat = model_catalog("gpt-5.4-mini")
check("catalog has models", len(cat["models"]) >= 5)
check("catalog current", cat["current"] == "gpt-5.4-mini")

custom = model_catalog("my-custom-model")
check("custom model listed", custom["models"][0]["id"] == "my-custom-model")

print("\n" + "=" * 60)
print(f"RESULT: {passed} passed, {failed} failed")
print("=" * 60)
if __name__ == "__main__":
    sys.exit(1 if failed else 0)

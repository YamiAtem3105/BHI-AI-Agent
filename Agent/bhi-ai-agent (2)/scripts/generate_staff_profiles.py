"""Sinh staff_profiles.json từ staff.json + dữ liệu task thực tế."""
import json
import os
import sys
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, ROOT)

import app.services.mock_sheets as mock_sheets  # noqa: E402


def _task_stats(name: str) -> dict:
    mock_sheets._load()
    ke_hoach = mock_sheets._ke_hoach or []
    total = done = doing = 0
    for t in ke_hoach:
        if not t.get("id") or "-" not in t["id"]:
            continue
        if not (mock_sheets._name_match(t["pic"], name) or mock_sheets._name_match(t["support"], name) or mock_sheets._name_match(t["reviewer"], name)):
            continue
        total += 1
        st = (t.get("status") or "").strip()
        if st == "Hoàn thành":
            done += 1
        elif st == "Đang làm":
            doing += 1
    rate = round(done / total * 100) if total else 0
    return {"total": total, "done": done, "doing": doing, "completion_rate": rate}


def _grade_from_stats(total: int, rate: int, role: str) -> tuple[str, int]:
    if role in ("admin", "super_admin", "manager") or total >= 15 or rate >= 75:
        return "Senior", 4
    if total >= 8 or rate >= 55:
        return "Middle", 3
    if total >= 3:
        return "Junior", 2
    return "Fresher", 1


def _salary_3p(skill: int, comp: int, perf: int) -> dict:
    base = 5.0 + skill * 0.5
    return {
        "position": round(min(10, base + 0.3), 1),
        "person": round(min(10, 5.5 + comp / 20), 1),
        "performance": round(min(10, 5.0 + perf / 15), 1),
    }


def _priority(rate: int, doing: int) -> str:
    if doing >= 6:
        return "Cao"
    if rate < 40 and doing >= 3:
        return "Cao"
    if doing >= 3:
        return "Trung bình"
    return "Thấp"


def generate() -> list[dict]:
    mock_sheets._load()
    with open(os.path.join(DATA, "staff.json"), encoding="utf-8") as f:
        staff = json.load(f)

    profiles = []
    for s in staff:
        role = s.get("role", "member")
        if role in ("admin", "super_admin"):
            continue
        name = s["name"]
        st = _task_stats(name)
        job_grade, skill = _grade_from_stats(st["total"], st["completion_rate"], role)
        comp = min(95, 55 + st["completion_rate"] // 3 + min(st["total"], 20))
        eff = min(95, 50 + st["completion_rate"] // 2 + min(st["doing"] * 3, 15))
        if role == "manager":
            comp = min(95, comp + 5)
            eff = min(95, eff + 3)
        profiles.append({
            "name": name,
            "email": s.get("email", ""),
            "salary_3p": _salary_3p(skill, comp, eff),
            "skill_level": skill,
            "competency_score": comp,
            "efficiency_score": eff,
            "job_grade": job_grade,
            "default_priority": _priority(st["completion_rate"], st["doing"]),
            "task_stats": st,
        })
    profiles.sort(key=lambda x: (-x["task_stats"]["total"], x["name"]))
    return profiles


def main():
    profiles = generate()
    out = os.path.join(DATA, "staff_profiles.json")
    # Lưu không có task_stats để file gọn (chỉ metadata HR)
    slim = []
    for p in profiles:
        row = {k: v for k, v in p.items() if k != "task_stats"}
        slim.append(row)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=2)
    print(f"Da ghi {len(slim)} profiles -> {out}")
    for p in slim[:5]:
        print(f"  - {p['name']}: {p['job_grade']}, NL={p['competency_score']}, tasks via script")


if __name__ == "__main__":
    main()

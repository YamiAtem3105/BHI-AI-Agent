from collections import defaultdict
from datetime import date

import httpx
from app.config import settings


class SheetsService:
    def __init__(self):
        self.base_url = settings.apps_script_url
        self.secret = settings.apps_script_secret
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def search_tasks(self, user: str = None, status: str = None,
                           date_from: str = None, date_to: str = None,
                           keyword: str = None, zone: str = None, role: str = None,
                           has_reviewer: bool = None) -> dict:
        params = {"action": "search", "secret": self.secret}
        if user: params["user"] = user
        if role: params["role"] = role
        if status: params["status"] = status
        if date_from: params["dateFrom"] = date_from
        if date_to: params["dateTo"] = date_to
        if keyword: params["keyword"] = keyword
        if zone: params["zone"] = zone
        if has_reviewer is not None: params["hasReviewer"] = "true" if has_reviewer else "false"
        resp = await self.client.get(self.base_url, params=params)
        print("========== DEBUG ==========")
        print("Status:", resp.status_code)
        print("URL:", resp.url)
        print("Body:", resp.text)
        print("===========================")
        return resp.json()

    async def get_task_detail(self, task_id: str) -> dict:
        resp = await self.client.get(self.base_url, params={"action": "detail", "taskId": task_id, "secret": self.secret})
        print("=" * 50)
        print("Status:", resp.status_code)
        print("URL:", resp.url)
        print("Body:")
        print(resp.text)
        print("=" * 50)
        return resp.json()

    async def get_subtasks(self, parent_id: str) -> dict:
        resp = await self.client.get(self.base_url, params={"action": "subtasks", "parentId": parent_id, "secret": self.secret})
        return resp.json()

    async def search_archive(self, user: str = None, project: str = None,
                             date_from: str = None, date_to: str = None) -> dict:
        params = {"action": "archive", "secret": self.secret}
        if user: params["user"] = user
        if project: params["project"] = project
        if date_from: params["dateFrom"] = date_from
        if date_to: params["dateTo"] = date_to
        resp = await self.client.get(self.base_url, params=params)
        print("=" * 50)
        print("Status:", resp.status_code)
        print("URL:", resp.url)
        print("Body:")
        print(resp.text)
        print("=" * 50)

        return resp.json()
        

    async def search_overdue_tasks(self, user: str = None, role: str = "pic") -> dict:
        """Dẫn xuất từ search: chưa hoàn thành và end_date < hôm nay."""
        res = await self.search_tasks(user=user, role=role)
        today = date.today().isoformat()
        overdue = [
            t for t in res.get("tasks", [])
            if (t.get("status") or "").strip() != "Hoàn thành"
            and t.get("end_date") and t["end_date"] < today
        ]
        return {"tasks": overdue[:50], "count": len(overdue), "filter": "overdue"}

    async def get_hours_summary(self, user_name: str, date_from: str = None, date_to: str = None) -> dict:
        """Tổng giờ theo dự án — dẫn xuất từ _ARCHIVE_LOG (cột Thời lượng/Giờ)."""
        res = await self.search_archive(user=user_name, date_from=date_from, date_to=date_to)
        reports = res.get("reports", [])
        by_project: dict = defaultdict(float)
        total = 0.0
        for r in reports:
            h = r.get("hours") or 0
            try:
                h = float(h)
            except (TypeError, ValueError):
                h = 0
            by_project[r.get("project") or "Khác"] += h
            total += h
        return {
            "by_project": dict(by_project), "total_hours": round(total, 1),
            "report_count": len(reports), "user": user_name,
            "date_from": date_from, "date_to": date_to,
        }

    async def get_personal_log(self, user_name: str, project: str = None,
                               date_from: str = None, date_to: str = None,
                               status: str = None) -> dict:
        """Log cá nhân — dẫn xuất từ _ARCHIVE_LOG lọc theo user/dự án/thời gian."""
        res = await self.search_archive(
            user=user_name, project=project, date_from=date_from, date_to=date_to,
        )
        reports = res.get("reports", [])
        if status:
            reports = [r for r in reports if (r.get("status") or "").strip() == status]
        return {
            "reports": reports, "count": len(reports), "user": user_name,
            "date_from": date_from, "date_to": date_to,
        }

    async def create_wbs(self, parent_name: str, children: list) -> dict:
        tasks = [{"name": parent_name, "level": 1}]
        for child in children:
            tasks.append({
                "name": child.get("name"),
                "pic": child.get("pic", ""),
                "support": child.get("support", ""),
                "reviewer": child.get("reviewer", ""),
                "duration": child.get("duration"),
                "predecessor": child.get("predecessor", ""),
                "zone": child.get("zone", ""),
            })
        resp = await self.client.post(self.base_url, json={"action": "create", "tasks": tasks, "secret": self.secret})
        result = resp.json()
        result["message"] = f"Đã tạo '{parent_name}' với {len(children)} task con"
        return result

    async def update_task(self, task_id: str, fields: dict) -> dict:
        resp = await self.client.post(self.base_url, json={
            "action": "update", "taskId": task_id, "fields": fields, "secret": self.secret
        })
        result = resp.json()
        if result.get("success"):
            result["message"] = f"Đã cập nhật task {task_id}"
        return result

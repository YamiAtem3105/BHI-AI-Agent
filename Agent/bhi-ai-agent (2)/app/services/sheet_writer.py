"""Ghi dữ liệu vào sheet (mock JSON + Apps Script khi có URL)."""
import json
import os
import uuid
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.services import mock_sheets
from app.services.mock_sheets import DATA_DIR, _slugify, _load_personal

ARCHIVE_PATH = os.path.join(DATA_DIR, "archive_log.json")
KE_HOACH_PATH = os.path.join(DATA_DIR, "ke_hoach.json")


class SheetWriter:
    async def execute(self, tool: str, params: dict) -> dict:
        if settings.apps_script_url:
            return await self._call_apps_script(tool, params)
        if tool == "update_task":
            return self._update_task_local(params)
        if tool in ("create_task", "create_wbs"):
            return self._create_task_local(params)
        if tool == "append_field_report":
            return self._append_report_local(params)
        return {"error": f"Unknown tool: {tool}"}

    async def execute_pending(self, pending: dict) -> dict:
        return await self.execute(pending["tool"], pending["params"])

    def _update_task_local(self, params: dict) -> dict:
        task_id = params.get("task_id")
        if not task_id:
            return {"error": "Thiếu task_id"}
        mock_sheets._load()
        plan = mock_sheets._ke_hoach or []
        updated = False
        for t in plan:
            if t["id"] == task_id:
                for k, v in params.items():
                    if k not in ("task_id", "source") and v is not None:
                        t[k] = v
                updated = True
                break
        if not updated:
            return {"error": f"Không tìm thấy task {task_id}"}
        with open(KE_HOACH_PATH, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        return {"success": True, "message": f"Đã cập nhật {task_id}: {params}"}

    def _create_task_local(self, params: dict) -> dict:
        tasks = params.get("tasks") or []
        if not tasks:
            return {"error": "Không có task nào để tạo"}
        mock_sheets._load()
        plan = mock_sheets._ke_hoach
        if plan is None:
            plan = []
            mock_sheets._ke_hoach = plan
        created = []
        for spec in tasks:
            tid = spec.get("id") or f"T-{uuid.uuid4().hex[:4].upper()}"
            plan.append({
                "id": tid,
                "name": spec.get("name", ""),
                "start_date": spec.get("start_date"),
                "end_date": spec.get("end_date"),
                "duration_days": spec.get("duration"),
                "predecessor": spec.get("predecessor", ""),
                "status": spec.get("status", "Chưa làm"),
                "pic": spec.get("pic", ""),
                "support": spec.get("support", ""),
                "reviewer": spec.get("reviewer", ""),
                "note": spec.get("note", ""),
                "zone": spec.get("zone", ""),
            })
            created.append(tid)
        with open(KE_HOACH_PATH, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        return {
            "success": True,
            "created": len(created),
            "task_ids": created,
            "message": f"Đã tạo {len(created)} task: {', '.join(created)}",
        }

    def _append_report_local(self, params: dict) -> dict:
        user = params.get("user", "")
        entry = {
            "report_date": params.get("report_date") or datetime.now(timezone.utc).isoformat(),
            "user": user,
            "employee_id": "",
            "role": "Thực hiện",
            "project": params.get("project", "Hiện trường"),
            "task_content": params.get("task_content", ""),
            "hours": params.get("hours"),
            "status": params.get("status", "Đang làm"),
            "deadline": params.get("deadline", ""),
            "evaluation": "",
            "report_note": f"[Chatbot {datetime.now().strftime('%d/%m %H:%M')}]",
        }

        # Ghi archive chung
        archive = []
        if os.path.exists(ARCHIVE_PATH):
            with open(ARCHIVE_PATH, encoding="utf-8") as f:
                archive = json.load(f)
        archive.append(entry)
        with open(ARCHIVE_PATH, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)

        # Ghi file cá nhân nếu có
        personal = _load_personal(user)
        if personal is not None:
            personal.setdefault("archive", []).append({
                **entry,
                "progress": params.get("status", "Đang làm"),
            })
            ppath = os.path.join(DATA_DIR, "personal", _slugify(user) + ".json")
            with open(ppath, "w", encoding="utf-8") as f:
                json.dump(personal, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "message": f"Đã ghi báo cáo cho {user}: {entry['task_content'][:80]}…",
            "entry_id": uuid.uuid4().hex[:8],
        }

    def _build_apps_script_payload(self, tool: str, params: dict) -> dict:
        """Dịch tool nội bộ → đúng contract Apps Script (create/update/report).

        Hỗ trợ chọn sheet ghi qua params['source'] ('1' sheet gắn script | '2').
        """
        secret = settings.apps_script_secret
        source = params.get("source")
        if tool == "update_task":
            fields = {k: v for k, v in params.items()
                      if k not in ("task_id", "source") and v is not None}
            payload = {"action": "update", "taskId": params.get("task_id"),
                       "fields": fields, "secret": secret}
            if source:
                payload["source"] = str(source)
            return payload
        if tool in ("create_task", "create_wbs"):
            payload = {"action": "create", "tasks": params.get("tasks", []), "secret": secret}
            if source:
                payload["source"] = str(source)
            return payload
        if tool == "append_field_report":
            report = {k: v for k, v in params.items() if k != "source"}
            payload = {"action": "report", "report": report, "secret": secret}
            if source:
                payload["source"] = str(source)
            return payload
        return {"action": tool, "params": params, "secret": secret}

    async def _call_apps_script(self, tool: str, params: dict) -> dict:
        # Apps Script /exec luôn 302-redirect sang googleusercontent → phải follow.
        payload = self._build_apps_script_payload(tool, params)
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.post(settings.apps_script_url, json=payload)
            r.raise_for_status()
            return r.json()

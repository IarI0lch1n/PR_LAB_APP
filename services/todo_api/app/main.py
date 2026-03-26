from __future__ import annotations

import os
import httpx
from fastapi import FastAPI, Header, HTTPException
from sqlalchemy import text as sql

from .db import engine

app = FastAPI(title="ToDo API", version="1.0")

ACCOUNT_API_URL = os.getenv("ACCOUNT_API_URL", "http://account_api:8003").rstrip("/")


@app.get("/health")
def health():
    return {"status": "ok", "service": "todo_api"}


def get_current_user(x_employee_key: str | None) -> dict:
    if not x_employee_key:
        raise HTTPException(status_code=401, detail="X-Employee-Key required")

    try:
        r = httpx.get(
            f"{ACCOUNT_API_URL}/me",
            headers={"X-Employee-Key": x_employee_key},
            timeout=5.0,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Account service unavailable")

    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid employee key")

    return r.json()


def require_lead_or_admin(x_employee_key: str | None) -> dict:
    me = get_current_user(x_employee_key)
    role = str(me.get("role") or "employee").lower()
    if role not in ("admin", "hr"):
        # сюда можно потом добавить teamlead, если введёшь такую роль
        raise HTTPException(status_code=403, detail="Admin/HR access required")
    return me


@app.get("/todo")
def list_my_todo(x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")):
    me = get_current_user(x_employee_key)
    my_id = int(me["id"])

    with engine.connect() as conn:
        rows = conn.execute(sql("""
            SELECT
                ta.id,
                ta.todo_list_id,
                tl.title,
                tl.description,
                ta.deadline,
                ta.is_completed,
                ta.completed_at,
                ta.completion_note,
                tl.created_by_employee_id,
                e.full_name AS created_by_name
            FROM dbo.todo_assignments ta
            JOIN dbo.todo_lists tl ON tl.id = ta.todo_list_id
            JOIN dbo.employees e ON e.id = tl.created_by_employee_id
            WHERE ta.employee_id = :me
            ORDER BY ta.is_completed ASC, ta.deadline ASC, ta.id DESC
        """), {"me": my_id}).mappings().all()

    return {"items": [dict(r) for r in rows]}


@app.post("/todo")
def create_todo(
    title: str,
    deadline: str,
    employee_ids: str,
    description: str | None = None,
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key"),
):
    me = require_lead_or_admin(x_employee_key)
    sender_id = int(me["id"])
    sender_name = me["full_name"]

    try:
        ids = [int(x.strip()) for x in employee_ids.split(",") if x.strip()]
    except Exception:
        raise HTTPException(status_code=400, detail="employee_ids must be comma-separated integers")

    if not ids:
        raise HTTPException(status_code=400, detail="At least one employee_id required")

    with engine.begin() as conn:
        todo_list_id = conn.execute(sql("""
            INSERT INTO dbo.todo_lists (title, description, created_by_employee_id)
            OUTPUT INSERTED.id
            VALUES (:title, :description, :created_by)
        """), {
            "title": title,
            "description": description,
            "created_by": sender_id,
        }).scalar()

        for emp_id in ids:
            conn.execute(sql("""
                INSERT INTO dbo.todo_assignments (todo_list_id, employee_id, deadline, is_completed)
                VALUES (:todo_list_id, :employee_id, TRY_CONVERT(datetime2, :deadline), 0)
            """), {
                "todo_list_id": int(todo_list_id),
                "employee_id": emp_id,
                "deadline": deadline,
            })

        recipients = []
        for emp_id in ids:
            row = conn.execute(sql("""
                SELECT id, full_name, email
                FROM dbo.employees
                WHERE id = :id
            """), {"id": emp_id}).mappings().first()
            if row:
                recipients.append(dict(row))

    for r in recipients:
        if r.get("email"):
            try:
                httpx.post(
                    f"{ACCOUNT_API_URL}/internal/send-todo-email",
                    params={
                        "to_email": r["email"],
                        "full_name": r["full_name"],
                        "title": title,
                        "description": description or "",
                        "deadline": deadline,
                        "sender_name": sender_name,
                    },
                    timeout=10.0,
                )
            except Exception:
                pass

    return {
        "message": "todo created",
        "todo_list_id": int(todo_list_id),
        "assigned_count": len(ids),
    }


@app.put("/todo/{assignment_id}/complete")
def complete_todo(
    assignment_id: int,
    completion_note: str | None = None,
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key"),
):
    me = get_current_user(x_employee_key)
    my_id = int(me["id"])
    my_name = me["full_name"]

    with engine.begin() as conn:
        row = conn.execute(sql("""
            SELECT
                ta.id,
                ta.employee_id,
                ta.deadline,
                ta.is_completed,
                tl.title,
                tl.created_by_employee_id,
                creator.full_name AS creator_name,
                creator.email AS creator_email
            FROM dbo.todo_assignments ta
            JOIN dbo.todo_lists tl ON tl.id = ta.todo_list_id
            JOIN dbo.employees creator ON creator.id = tl.created_by_employee_id
            WHERE ta.id = :id
        """), {"id": int(assignment_id)}).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Assignment not found")

        if int(row["employee_id"]) != my_id:
            raise HTTPException(status_code=403, detail="You can complete only your own tasks")

        conn.execute(sql("""
            UPDATE dbo.todo_assignments
            SET is_completed = 1,
                completed_at = SYSUTCDATETIME(),
                completion_note = :note
            WHERE id = :id
        """), {
            "id": int(assignment_id),
            "note": completion_note,
        })

    if row.get("creator_email"):
        try:
            httpx.post(
                f"{ACCOUNT_API_URL}/internal/send-todo-completed-email",
                params={
                    "to_email": row["creator_email"],
                    "recipient_name": row["creator_name"],
                    "employee_name": my_name,
                    "title": row["title"],
                    "deadline": str(row["deadline"]),
                    "note": completion_note or "",
                },
                timeout=10.0,
            )
        except Exception:
            pass

    return {"message": "task marked as completed", "assignment_id": int(assignment_id)}
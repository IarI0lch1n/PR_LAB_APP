from __future__ import annotations

import os
import httpx
from fastapi import FastAPI, Header, HTTPException
from sqlalchemy import text as sql

from .db import engine

app = FastAPI(title="Chat API", version="5.0")

ACCOUNT_API_URL = os.getenv("ACCOUNT_API_URL", "http://account_api:8003")


@app.get("/health")
def health():
    return {"status": "ok", "service": "chat_api"}


def get_current_user(x_employee_key: str | None) -> dict:
    if not x_employee_key:
        raise HTTPException(status_code=401, detail="X-Employee-Key required")

    try:
        r = httpx.get(
            f"{ACCOUNT_API_URL}/me",
            headers={"X-Employee-Key": x_employee_key},
            timeout=5.0
        )
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid employee key")
        return r.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Account service unavailable")


@app.get("/chats")
def list_chats(x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")):
    me = get_current_user(x_employee_key)
    my_id = int(me["id"])

    # Идея:
    # 1) делаем "плоский" список (other_id, created_at) через UNION ALL
    # 2) группируем уже по other_id и берём MAX(created_at)
    with engine.connect() as conn:
        rows = conn.execute(sql("""
            WITH conv AS (
              SELECT recipient_employee_id AS other_id, created_at
              FROM dbo.messages
              WHERE sender_employee_id = :me

              UNION ALL

              SELECT sender_employee_id AS other_id, created_at
              FROM dbo.messages
              WHERE recipient_employee_id = :me
            ),
            pairs AS (
              SELECT other_id, MAX(created_at) AS last_time
              FROM conv
              WHERE other_id IS NOT NULL
              GROUP BY other_id
            )
            SELECT p.other_id, e.full_name, e.email, e.phone, p.last_time
            FROM pairs p
            JOIN dbo.employees e ON e.id = p.other_id
            ORDER BY p.last_time DESC;
        """), {"me": my_id}).mappings().all()

    return {"chats": [dict(r) for r in rows]}


@app.get("/chats/{other_id}/messages")
def chat_messages(
    other_id: int,
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")
):
    me = get_current_user(x_employee_key)
    my_id = int(me["id"])

    with engine.connect() as conn:
        rows = conn.execute(sql("""
            SELECT
              m.id,
              m.text,
              m.file_id,
              m.created_at,
              m.sender_employee_id,
              m.recipient_employee_id,
              es.full_name AS sender_name,
              er.full_name AS recipient_name
            FROM dbo.messages m
            LEFT JOIN dbo.employees es ON es.id = m.sender_employee_id
            LEFT JOIN dbo.employees er ON er.id = m.recipient_employee_id
            WHERE (
              (m.sender_employee_id = :me AND m.recipient_employee_id = :other)
              OR
              (m.sender_employee_id = :other AND m.recipient_employee_id = :me)
            )
            ORDER BY m.created_at ASC, m.id ASC;
        """), {"me": my_id, "other": int(other_id)}).mappings().all()

    return {"messages": [dict(r) for r in rows]}


@app.post("/chats/{other_id}/messages")
def send_message(
    other_id: int,
    text: str,
    file_id: int | None = None,
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")
):
    me = get_current_user(x_employee_key)
    my_id = int(me["id"])

    with engine.begin() as conn:
        # вставка сообщения
        res = conn.execute(sql("""
            INSERT INTO dbo.messages (text, file_id, sender_employee_id, recipient_employee_id)
            OUTPUT INSERTED.id
            VALUES (:text, :file_id, :sender, :recipient)
        """), {
            "text": text,
            "file_id": file_id,
            "sender": my_id,
            "recipient": int(other_id)
        })
        mid = int(res.scalar())

        row = conn.execute(sql("""
            SELECT
              m.id, m.text, m.file_id, m.created_at,
              m.sender_employee_id, m.recipient_employee_id,
              es.full_name AS sender_name,
              er.full_name AS recipient_name
            FROM dbo.messages m
            LEFT JOIN dbo.employees es ON es.id = m.sender_employee_id
            LEFT JOIN dbo.employees er ON er.id = m.recipient_employee_id
            WHERE m.id = :id
        """), {"id": mid}).mappings().first()

    return dict(row)
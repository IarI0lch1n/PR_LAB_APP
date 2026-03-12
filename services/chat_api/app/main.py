from fastapi import FastAPI, HTTPException
from sqlalchemy import text as sql
import httpx
import os

from .db import engine

app = FastAPI(title="Chat API", version="4.0")

FILE_API_URL = os.getenv("FILE_API_URL", "http://file_api:8002")


@app.get("/health")
def health():
    return {"status": "ok", "service": "chat_api"}


def ensure_file_id_exists(file_id: int) -> None:
    try:
        r = httpx.get(f"{FILE_API_URL}/files/{file_id}", timeout=5.0)
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="Attached file not found")
        r.raise_for_status()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="File service unavailable")


def _row_to_message_dict(row) -> dict:
    d = dict(row)
    d["file"] = d.pop("filename", None)
    d["file_id"] = d.get("file_id")
    return d


@app.get("/messages")
def get_messages():
    with engine.connect() as conn:
        rows = conn.execute(sql("""
            SELECT m.id, m.text, m.file_id, m.created_at,
                   f.filename
            FROM dbo.messages m
            LEFT JOIN dbo.files f ON f.id = m.file_id
            ORDER BY m.id ASC
        """)).mappings().all()

    return {"messages": [_row_to_message_dict(r) for r in rows]}


@app.post("/messages")
def send_message(text: str, file_id: int | None = None):
    if file_id is not None:
        ensure_file_id_exists(file_id)

    with engine.begin() as conn:
        res = conn.execute(sql("""
            INSERT INTO dbo.messages (text, file_id)
            OUTPUT INSERTED.id, INSERTED.text, INSERTED.file_id, INSERTED.created_at
            VALUES (:text, :file_id)
        """), {"text": text, "file_id": file_id})

        row = res.mappings().first()

        row2 = conn.execute(sql("""
            SELECT m.id, m.text, m.file_id, m.created_at, f.filename
            FROM dbo.messages m
            LEFT JOIN dbo.files f ON f.id = m.file_id
            WHERE m.id = :id
        """), {"id": row["id"]}).mappings().first()

    return _row_to_message_dict(row2)


@app.delete("/messages/{message_id}")
def delete_message(message_id: int):
    with engine.begin() as conn:
        row = conn.execute(sql("""
            SELECT m.id, m.text, m.file_id, m.created_at, f.filename
            FROM dbo.messages m
            LEFT JOIN dbo.files f ON f.id = m.file_id
            WHERE m.id = :id
        """), {"id": message_id}).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Message not found")

        conn.execute(sql("DELETE FROM dbo.messages WHERE id=:id"), {"id": message_id})

    return {"deleted": _row_to_message_dict(row)}
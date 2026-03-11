from fastapi import FastAPI, HTTPException
from sqlalchemy import text as sql
import httpx
import os

from .db import engine

app = FastAPI(title="Chat API", version="3.1")

FILE_API_URL = os.getenv("FILE_API_URL", "http://file_api:8002")


@app.get("/health")
def health():
    return {"status": "ok", "service": "chat_api"}


def ensure_file_exists(filename: str) -> None:
    try:
        r = httpx.get(f"{FILE_API_URL}/files", timeout=5.0)
        r.raise_for_status()
        files = r.json().get("files", [])
    except Exception:
        raise HTTPException(status_code=500, detail="File service unavailable")

    if filename not in files:
        raise HTTPException(status_code=404, detail="Attached file not found in file service")


def _row_to_message_dict(row) -> dict:
    d = dict(row)
    d["file"] = d.pop("attached_file", None)
    return d


@app.get("/messages")
def get_messages():
    with engine.connect() as conn:
        rows = conn.execute(sql("""
            SELECT id, text, file_name AS attached_file, created_at
            FROM dbo.messages
            ORDER BY id ASC
        """)).mappings().all()

    return {"messages": [_row_to_message_dict(r) for r in rows]}


@app.post("/messages")
def send_message(text: str, filename: str | None = None):
    if filename:
        ensure_file_exists(filename)

    with engine.begin() as conn:
        res = conn.execute(sql("""
            INSERT INTO dbo.messages (text, file_name)
            OUTPUT INSERTED.id,
                   INSERTED.text,
                   INSERTED.file_name AS attached_file,
                   INSERTED.created_at
            VALUES (:text, :file)
        """), {"text": text, "file": filename})

        row = res.mappings().first()

    return _row_to_message_dict(row)


@app.put("/messages/{message_id}")
def update_message(message_id: int, text: str | None = None, filename: str | None = None):
    if filename:
        ensure_file_exists(filename)

    with engine.begin() as conn:
        exists = conn.execute(
            sql("SELECT 1 FROM dbo.messages WHERE id=:id"),
            {"id": message_id}
        ).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Message not found")

        if text is not None:
            conn.execute(
                sql("UPDATE dbo.messages SET text=:t WHERE id=:id"),
                {"t": text, "id": message_id}
            )

        if filename is not None:
            conn.execute(
                sql("UPDATE dbo.messages SET file_name=:f WHERE id=:id"),
                {"f": filename, "id": message_id}
            )

        row = conn.execute(sql("""
            SELECT id, text, file_name AS attached_file, created_at
            FROM dbo.messages
            WHERE id=:id
        """), {"id": message_id}).mappings().first()

    return _row_to_message_dict(row)


@app.delete("/messages/{message_id}")
def delete_message(message_id: int):
    with engine.begin() as conn:
        row = conn.execute(sql("""
            SELECT id, text, file_name AS attached_file, created_at
            FROM dbo.messages
            WHERE id=:id
        """), {"id": message_id}).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Message not found")

        conn.execute(sql("DELETE FROM dbo.messages WHERE id=:id"), {"id": message_id})

    return {"deleted": _row_to_message_dict(row)}
from __future__ import annotations

import os
from urllib.parse import quote

import httpx
from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Form
from fastapi.responses import Response
from sqlalchemy import text as sql

from .db import engine

app = FastAPI(title="File API", version="6.0")

ACCOUNT_API_URL = os.getenv("ACCOUNT_API_URL", "http://account_api:8003").rstrip("/")


@app.get("/health")
def health():
    return {"status": "ok", "service": "file_api"}


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


@app.get("/files")
def list_files(x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")):
    me = get_current_user(x_employee_key)
    my_id = int(me["id"])

    with engine.connect() as conn:
        rows = conn.execute(sql("""
            WITH visible AS (
              SELECT
                f.id,
                f.filename,
                f.owner_employee_id,
                f.is_public_download,
                CAST(0 AS BIT) AS shared
              FROM dbo.files f
              WHERE f.owner_employee_id = :me

              UNION

              SELECT
                f.id,
                f.filename,
                f.owner_employee_id,
                f.is_public_download,
                CAST(1 AS BIT) AS shared
              FROM dbo.messages m
              JOIN dbo.files f ON f.id = m.file_id
              WHERE m.recipient_employee_id = :me
                AND m.file_id IS NOT NULL
            )
            SELECT
              v.id,
              v.filename,
              v.shared,
              v.owner_employee_id,
              v.is_public_download,
              e.full_name AS owner_name,
              e.email AS owner_email
            FROM visible v
            JOIN dbo.employees e ON e.id = v.owner_employee_id
            GROUP BY
              v.id,
              v.filename,
              v.shared,
              v.owner_employee_id,
              v.is_public_download,
              e.full_name,
              e.email
            ORDER BY v.filename ASC
        """), {"me": my_id}).mappings().all()

    result = [dict(r) for r in rows]
    print("[DEBUG /files RESULT]", result)
    return {"files": result}


@app.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key"),
):
    me = get_current_user(x_employee_key)
    my_id = int(me["id"])

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    filename = file.filename or "file"
    content_type = file.content_type or "application/octet-stream"
    size_bytes = len(content)

    with engine.begin() as conn:
        new_id = conn.execute(sql("""
            INSERT INTO dbo.files (filename, content, content_type, size_bytes, owner_employee_id)
            OUTPUT INSERTED.id
            VALUES (:filename, :content, :content_type, :size_bytes, :owner_id)
        """), {
            "filename": filename,
            "content": content,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "owner_id": my_id,
        }).scalar()

    return {"message": "file uploaded", "id": int(new_id), "filename": filename}


@app.get("/files/{file_id}")
def get_file_meta(
    file_id: int,
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key"),
):
    me = get_current_user(x_employee_key)
    my_id = int(me["id"])

    with engine.connect() as conn:
        row = conn.execute(sql("""
            SELECT
              f.id,
              f.filename,
              f.content_type,
              f.size_bytes,
              f.owner_employee_id,
              e.full_name AS owner_name,
              e.email AS owner_email
            FROM dbo.files f
            JOIN dbo.employees e ON e.id = f.owner_employee_id
            WHERE f.id = :id
        """), {"id": int(file_id)}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    if int(row["owner_employee_id"]) != my_id:
        with engine.connect() as conn:
            allowed = conn.execute(sql("""
                SELECT TOP 1 1
                FROM dbo.messages
                WHERE recipient_employee_id = :me AND file_id = :fid
            """), {"me": my_id, "fid": int(file_id)}).scalar()

        if not allowed:
            raise HTTPException(status_code=403, detail="No access")

    return dict(row)


@app.get("/download/{file_id}")
def download_file(
    file_id: int,
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key"),
):
    me = get_current_user(x_employee_key)
    my_id = int(me["id"])

    with engine.connect() as conn:
        row = conn.execute(sql("""
            SELECT
              f.id,
              f.filename,
              f.content,
              f.content_type,
              f.owner_employee_id,
              f.is_public_download
            FROM dbo.files f
            WHERE f.id = :id
        """), {"id": int(file_id)}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    allowed = False

    if int(row["owner_employee_id"]) == my_id:
        allowed = True
    elif int(row["is_public_download"]) == 1:
        allowed = True
    else:
        with engine.connect() as conn:
            msg_access = conn.execute(sql("""
                SELECT TOP 1 1
                FROM dbo.messages
                WHERE recipient_employee_id = :me AND file_id = :fid
            """), {"me": my_id, "fid": int(file_id)}).scalar()

        if msg_access:
            allowed = True

    if not allowed:
        raise HTTPException(status_code=403, detail="No access")

    blob = row["content"]
    if blob is None:
        raise HTTPException(status_code=404, detail="File content is empty")

    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    elif not isinstance(blob, (bytes, bytearray)):
        blob = bytes(blob)

    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(str(row['filename']))}"
    }

    return Response(
        content=blob,
        media_type=row["content_type"] or "application/octet-stream",
        headers=headers,
    )

@app.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key"),
):
    me = get_current_user(x_employee_key)
    my_id = int(me["id"])

    with engine.begin() as conn:
        row = conn.execute(sql("""
            SELECT id, filename, owner_employee_id
            FROM dbo.files
            WHERE id = :id
        """), {"id": int(file_id)}).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="File not found")

        if int(row["owner_employee_id"]) != my_id:
            raise HTTPException(status_code=403, detail="Only file owner can delete file")

        conn.execute(sql("DELETE FROM dbo.files WHERE id = :id"), {"id": int(file_id)})

    return {"message": "file deleted", "id": int(row["id"]), "filename": row["filename"]}

@app.put("/files/{file_id}")
def update_file(
    file_id: int,
    file: UploadFile | None = File(default=None),
    is_public_download: int | None = Form(default=None),
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key"),
):
    me = get_current_user(x_employee_key)
    my_id = int(me["id"])

    with engine.begin() as conn:
        current = conn.execute(sql("""
            SELECT id, filename, owner_employee_id, content, content_type, size_bytes, is_public_download
            FROM dbo.files
            WHERE id = :id
        """), {"id": int(file_id)}).mappings().first()

        if not current:
            raise HTTPException(status_code=404, detail="File not found")

        if int(current["owner_employee_id"]) != my_id:
            raise HTTPException(status_code=403, detail="Only file owner can update file")

        new_filename = current["filename"]
        new_content = current["content"]
        new_content_type = current["content_type"]
        new_size_bytes = current["size_bytes"]
        new_public = current["is_public_download"]

        if file is not None:
            content = file.file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Empty file")

            new_filename = file.filename or current["filename"]
            new_content = content
            new_content_type = file.content_type or "application/octet-stream"
            new_size_bytes = len(content)

        if is_public_download is not None:
            if is_public_download not in (0, 1):
                raise HTTPException(status_code=400, detail="is_public_download must be 0 or 1")
            new_public = is_public_download

        conn.execute(sql("""
            UPDATE dbo.files
            SET filename = :filename,
                content = :content,
                content_type = :content_type,
                size_bytes = :size_bytes,
                is_public_download = :is_public_download
            WHERE id = :id
        """), {
            "id": int(file_id),
            "filename": new_filename,
            "content": new_content,
            "content_type": new_content_type,
            "size_bytes": new_size_bytes,
            "is_public_download": int(new_public),
        })

        row = conn.execute(sql("""
            SELECT
                f.id,
                f.filename,
                f.size_bytes,
                f.is_public_download,
                f.owner_employee_id,
                e.full_name AS owner_name,
                e.email AS owner_email
            FROM dbo.files f
            JOIN dbo.employees e ON e.id = f.owner_employee_id
            WHERE f.id = :id
        """), {"id": int(file_id)}).mappings().first()

    return {
        "message": "file updated",
        **dict(row)
    }
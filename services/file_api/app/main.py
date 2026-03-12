from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy import text as sql

from .db import engine

app = FastAPI(title="File Cloud Service", version="4.0")


@app.get("/health")
def health():
    return {"status": "ok", "service": "file_api"}


@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    filename = file.filename
    content_type = file.content_type or "application/octet-stream"
    data = file.file.read() 

    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    size = len(data)

    with engine.begin() as conn:
        conn.execute(sql("""
            MERGE dbo.files AS target
            USING (SELECT :filename AS filename) AS src
            ON target.filename = src.filename
            WHEN MATCHED THEN
                UPDATE SET content = :content,
                           content_type = :content_type,
                           size_bytes = :size_bytes,
                           uploaded_at = SYSUTCDATETIME()
            WHEN NOT MATCHED THEN
                INSERT (filename, content, content_type, size_bytes)
                VALUES (:filename, :content, :content_type, :size_bytes);
        """), {
            "filename": filename,
            "content": data,
            "content_type": content_type,
            "size_bytes": size
        })

        row = conn.execute(sql("""
            SELECT TOP 1 id, filename, size_bytes, uploaded_at
            FROM dbo.files
            WHERE filename = :filename
        """), {"filename": filename}).mappings().first()

    return {"message": "file uploaded", **dict(row)}


@app.get("/files")
def list_files():
    with engine.connect() as conn:
        rows = conn.execute(sql("""
            SELECT id, filename
            FROM dbo.files
            ORDER BY uploaded_at DESC
        """)).mappings().all()

    return {"files": [dict(r) for r in rows]}


@app.get("/files/{file_id}")
def get_file_meta(file_id: int):
    with engine.connect() as conn:
        row = conn.execute(sql("""
            SELECT id, filename, size_bytes, uploaded_at
            FROM dbo.files
            WHERE id = :id
        """), {"id": file_id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    return dict(row)


@app.get("/download/{file_id}")
def download_file(file_id: int):
    with engine.connect() as conn:
        row = conn.execute(sql("""
            SELECT filename, content_type, content
            FROM dbo.files
            WHERE id = :id
        """), {"id": file_id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    blob = row["content"]
    if blob is None:
        raise HTTPException(status_code=404, detail="File has no content")

    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    elif not isinstance(blob, (bytes, bytearray)):
        blob = bytes(blob)

    return Response(
        content=blob,
        media_type=row["content_type"] or "application/octet-stream",
    )


@app.delete("/files/{file_id}")
def delete_file(file_id: int):
    with engine.begin() as conn:
        row = conn.execute(sql("""
            SELECT id, filename FROM dbo.files WHERE id = :id
        """), {"id": file_id}).mappings().first()

        if not row:
            raise HTTPException(status_code=404, detail="Not Found")

        conn.execute(sql("DELETE FROM dbo.files WHERE id = :id"), {"id": file_id})

    return {"message": "file deleted", "id": row["id"], "filename": row["filename"]}
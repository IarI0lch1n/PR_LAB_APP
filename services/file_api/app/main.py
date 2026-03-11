from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import text as sql

from .db import engine

app = FastAPI(title="File Cloud Service", version="3.0")

# В контейнере это будет volume: -v D:\...\storage:/app/storage
STORAGE = Path("/app/storage")
STORAGE.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok", "service": "file_api"}


@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    safe_name = Path(file.filename).name
    file_path = STORAGE / safe_name

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    size = file_path.stat().st_size

    # upsert (MERGE) в dbo.files
    try:
        with engine.begin() as conn:
            conn.execute(sql("""
                MERGE dbo.files AS target
                USING (SELECT :filename AS filename, :size_bytes AS size_bytes) AS src
                ON target.filename = src.filename
                WHEN MATCHED THEN
                    UPDATE SET size_bytes = src.size_bytes, uploaded_at = SYSUTCDATETIME()
                WHEN NOT MATCHED THEN
                    INSERT (filename, size_bytes) VALUES (src.filename, src.size_bytes);
            """), {"filename": safe_name, "size_bytes": size})
    except Exception as e:
        # Если запись в БД не удалась — удалим файл, чтобы не было рассинхрона
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    return {"message": "file uploaded", "filename": safe_name, "size_bytes": size}


@app.get("/files")
def list_files():
    # Берём список из БД (как “облачный индекс”)
    with engine.connect() as conn:
        rows = conn.execute(sql("""
            SELECT filename
            FROM dbo.files
            ORDER BY uploaded_at DESC
        """)).all()

    return {"files": [r[0] for r in rows]}


@app.get("/download/{filename}")
def download_file(filename: str):
    safe_name = Path(filename).name
    file_path = STORAGE / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type="application/octet-stream"
    )


@app.delete("/files/{filename}")
def delete_file(filename: str):
    safe_name = Path(filename).name
    file_path = STORAGE / safe_name

    # Удаляем файл с диска (если его нет — 404)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        file_path.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")

    # Удаляем запись из БД (если записи нет — не страшно)
    try:
        with engine.begin() as conn:
            conn.execute(sql("DELETE FROM dbo.files WHERE filename=:f"), {"f": safe_name})
    except Exception as e:
        # Файл уже удалён, но БД не обновилась — сообщим как warning
        raise HTTPException(status_code=500, detail=f"File deleted, but DB delete failed: {e}")

    return {"message": "file deleted", "filename": safe_name}
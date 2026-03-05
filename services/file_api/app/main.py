from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import shutil

app = FastAPI(title="File Cloud Service", version="1.0")

STORAGE = Path("storage")
STORAGE.mkdir(exist_ok=True)

# Проверка сервиса
@app.get("/health")
def health():
    return {"status": "ok", "service": "file_api"}

# Загрузка файла
@app.post("/upload")
def upload_file(file: UploadFile = File(...)):
    file_path = STORAGE / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"message": "file uploaded", "filename": file.filename}

# Список файлов
@app.get("/files")
def list_files():
    files = [f.name for f in STORAGE.iterdir() if f.is_file()]
    return {"files": files}

# Скачивание файла
@app.get("/download/{filename}")
def download_file(filename: str):
    file_path = STORAGE / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,          
        media_type="application/octet-stream"
    )

@app.delete("/files/{filename}")
def delete_file(filename: str):
    file_path = STORAGE / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Not Found")

    file_path.unlink()
    return {"message": "file deleted", "filename": filename}
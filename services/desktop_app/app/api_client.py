from __future__ import annotations

from pathlib import Path
import mimetypes
from typing import Any, Dict, List, Optional

import httpx


class ApiClient:
    """
    Desktop app HTTP client for chat_api and file_api.
    Works with:
      - chat_api:  GET /messages, POST /messages, PUT /messages/{id}, DELETE /messages/{id}
      - file_api:  GET /files, POST /upload (multipart), GET /download/{filename}
    """

    def __init__(self, chat_api_url: str, file_api_url: str, timeout: float = 10.0):
        self.chat_api_url = chat_api_url.rstrip("/")
        self.file_api_url = file_api_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    # -----------------------------
    # Chat API
    # -----------------------------
    def get_messages(self) -> List[Dict[str, Any]]:
        r = self._client.get(f"{self.chat_api_url}/messages")
        r.raise_for_status()
        data = r.json()
        return data.get("messages", [])

    def send_message(self, text: str, filename: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, str] = {"text": text}
        if filename:
            params["filename"] = filename

        r = self._client.post(f"{self.chat_api_url}/messages", params=params)

        if r.status_code >= 400:
            # keep error details from API if available
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text or "Error"
            raise RuntimeError(f"{r.status_code}: {detail}")

        return r.json()

    def update_message(
        self,
        message_id: int,
        text: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, str] = {}
        if text is not None:
            params["text"] = text
        if filename is not None:
            params["filename"] = filename

        r = self._client.put(f"{self.chat_api_url}/messages/{message_id}", params=params)

        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text or "Error"
            raise RuntimeError(f"{r.status_code}: {detail}")

        return r.json()

    def delete_message(self, message_id: int) -> Dict[str, Any]:
        r = self._client.delete(f"{self.chat_api_url}/messages/{message_id}")

        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text or "Error"
            raise RuntimeError(f"{r.status_code}: {detail}")

        return r.json()

    # -----------------------------
    # File API
    # -----------------------------
    def list_files(self) -> List[str]:
        r = self._client.get(f"{self.file_api_url}/files")
        r.raise_for_status()
        data = r.json()
        return data.get("files", [])

    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """
        Uploads file via multipart/form-data as field "file".
        This is compatible with FastAPI UploadFile.
        """
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        filename = p.name  # IMPORTANT: only the file name, no directories
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        with p.open("rb") as f:
            files = {"file": (filename, f, content_type)}
            r = self._client.post(f"{self.file_api_url}/upload", files=files)

        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text or "Error"
            raise RuntimeError(f"{r.status_code}: {detail}")

        return r.json()

    def download_file(self, filename: str, save_path: str) -> None:
        r = self._client.get(f"{self.file_api_url}/download/{filename}")

        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text or "Error"
            raise RuntimeError(f"{r.status_code}: {detail}")

        out = Path(save_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.content)
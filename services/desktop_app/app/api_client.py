from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


class ApiClient:
    """
    Desktop app HTTP client for chat_api and file_api (DB-backed files).

    chat_api:
      - GET    /messages
      - POST   /messages?text=...&file_id=...
      - DELETE /messages/{id}

    file_api:
      - GET    /files              -> {"files":[{"id":..,"filename":..}, ...]}
      - POST   /upload             (multipart file)
      - GET    /download/{file_id} (raw bytes)
      - DELETE /files/{file_id}
      - GET    /files/{file_id}    (meta)  [optional]
    """

    def __init__(self, chat_api_url: str, file_api_url: str, timeout: float = 20.0):
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

    def send_message(self, text: str, file_id: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, str] = {"text": text}
        if file_id is not None:
            params["file_id"] = str(int(file_id))

        r = self._client.post(f"{self.chat_api_url}/messages", params=params)

        if r.status_code >= 400:
            detail = _extract_error(r)
            raise RuntimeError(f"{r.status_code}: {detail}")

        return r.json()

    def delete_message(self, message_id: int) -> Dict[str, Any]:
        r = self._client.delete(f"{self.chat_api_url}/messages/{int(message_id)}")

        if r.status_code >= 400:
            detail = _extract_error(r)
            raise RuntimeError(f"{r.status_code}: {detail}")

        return r.json()

    # -----------------------------
    # File API
    # -----------------------------
    def list_files(self) -> List[Dict[str, Any]]:
        r = self._client.get(f"{self.file_api_url}/files")
        r.raise_for_status()
        return r.json().get("files", [])

    def upload_file(self, file_path: str) -> Dict[str, Any]:
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        with p.open("rb") as f:
            files = {"file": (p.name, f, "application/octet-stream")}
            r = self._client.post(f"{self.file_api_url}/upload", files=files)

        if r.status_code >= 400:
            detail = _extract_error(r)
            raise RuntimeError(f"{r.status_code}: {detail}")

        return r.json()

    def download_file(self, file_id: int, save_path: str) -> None:
        r = self._client.get(f"{self.file_api_url}/download/{int(file_id)}")

        if r.status_code >= 400:
            detail = _extract_error(r)
            raise RuntimeError(f"{r.status_code}: {detail}")

        out = Path(save_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.content)

    def delete_file(self, file_id: int) -> Dict[str, Any]:
        r = self._client.delete(f"{self.file_api_url}/files/{int(file_id)}")

        if r.status_code >= 400:
            detail = _extract_error(r)
            raise RuntimeError(f"{r.status_code}: {detail}")

        return r.json()


def _extract_error(r: httpx.Response) -> str:
    try:
        j = r.json()
        if isinstance(j, dict) and "detail" in j:
            return str(j["detail"])
        return r.text or "Error"
    except Exception:
        return r.text or "Error"
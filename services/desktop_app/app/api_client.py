from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


class ApiClient:
    def __init__(
        self,
        chat_api_url: str,
        file_api_url: str,
        account_api_url: str,
        timeout: float = 20.0,
    ):
        self.chat_api_url = chat_api_url.rstrip("/")
        self.file_api_url = file_api_url.rstrip("/")
        self.account_api_url = account_api_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)
        self.employee_key: Optional[str] = None

    def close(self) -> None:
        self._client.close()

    def set_employee_key(self, key: str) -> None:
        self.employee_key = key

    def _auth_headers(self) -> Dict[str, str]:
        if not self.employee_key:
            return {}
        return {"X-Employee-Key": self.employee_key}

    # ---------------- account ----------------
    def me(self) -> Dict[str, Any]:
        r = self._client.get(f"{self.account_api_url}/me", headers=self._auth_headers())
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json()

    def search_employees(self, q: str) -> List[Dict[str, Any]]:
        r = self._client.get(
            f"{self.account_api_url}/employees/search",
            params={"q": q},
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json().get("items", [])

    # ---------------- chats ----------------
    def list_chats(self) -> List[Dict[str, Any]]:
        r = self._client.get(f"{self.chat_api_url}/chats", headers=self._auth_headers())
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json().get("chats", [])

    def get_chat_messages(self, other_id: int) -> List[Dict[str, Any]]:
        r = self._client.get(
            f"{self.chat_api_url}/chats/{int(other_id)}/messages",
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json().get("messages", [])

    def send_chat_message(self, other_id: int, text: str, file_id: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, str] = {"text": text}
        if file_id is not None:
            params["file_id"] = str(int(file_id))

        r = self._client.post(
            f"{self.chat_api_url}/chats/{int(other_id)}/messages",
            params=params,
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json()

    # ---------------- files ----------------
    def list_files(self) -> List[Dict[str, Any]]:
        r = self._client.get(f"{self.file_api_url}/files", headers=self._auth_headers())
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json().get("files", [])

    def upload_file(self, file_path: str) -> Dict[str, Any]:
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        with p.open("rb") as f:
            files = {"file": (p.name, f, "application/octet-stream")}
            r = self._client.post(
                f"{self.file_api_url}/upload",
                files=files,
                headers=self._auth_headers(),
            )

        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json()

    def get_file_meta(self, file_id: int) -> Dict[str, Any]:
        r = self._client.get(
            f"{self.file_api_url}/files/{int(file_id)}",
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json()

    def download_file(self, file_id: int, save_path: str) -> None:
        r = self._client.get(
            f"{self.file_api_url}/download/{int(file_id)}",
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))

        out = Path(save_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.content)

    def delete_file(self, file_id: int) -> Dict[str, Any]:
        r = self._client.delete(
            f"{self.file_api_url}/files/{int(file_id)}",
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json()


def _extract_error(r: httpx.Response) -> str:
    try:
        j = r.json()
        if isinstance(j, dict) and "detail" in j:
            return str(j["detail"])
    except Exception:
        pass
    return r.text or f"HTTP {r.status_code}"
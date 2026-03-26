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
        todo_api_url: str,
        timeout: float = 20.0,
    ):
        self.chat_api_url = chat_api_url.rstrip("/")
        self.file_api_url = file_api_url.rstrip("/")
        self.account_api_url = account_api_url.rstrip("/")
        self.todo_api_url = todo_api_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)
        self.employee_key: Optional[str] = None

    def close(self) -> None:
        self._client.close()

    def set_employee_key(self, key: str | None) -> None:
        self.employee_key = key

    def logout(self) -> None:
        self.employee_key = None

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

    def update_file(
        self,
        file_id: int,
        file_path: str | None = None,
        is_public_download: int | None = None,
    ) -> dict:
        files = None
        data = {}

        f = None
        if file_path is not None:
            p = Path(file_path)
            if not p.exists() or not p.is_file():
                raise FileNotFoundError(f"File not found: {file_path}")
            f = p.open("rb")
            files = {"file": (p.name, f, "application/octet-stream")}

        if is_public_download is not None:
            data["is_public_download"] = str(int(is_public_download))

        try:
            r = self._client.put(
                f"{self.file_api_url}/files/{int(file_id)}",
                files=files,
                data=data,
                headers=self._auth_headers(),
            )
        finally:
            if f is not None:
                f.close()

        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json()

    def list_employees(self) -> list[dict]:
        r = self._client.get(
            f"{self.account_api_url}/employees",
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json().get("items", [])

    def create_employee(
        self,
        full_name: str,
        office_country: str,
        position: str,
        email: str | None = None,
        phone: str | None = None,
        role: str = "employee",
    ) -> dict:
        params = {
            "full_name": full_name,
            "office_country": office_country,
            "position": position,
            "role": role,
        }
        if email:
            params["email"] = email
        if phone:
            params["phone"] = phone

        r = self._client.post(
            f"{self.account_api_url}/employees",
            params=params,
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json()

    def update_employee(
        self,
        employee_id: int,
        full_name: str | None = None,
        office_country: str | None = None,
        position: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        is_active: int | None = None,
        role: str | None = None,
    ) -> dict:
        params = {}
        if full_name is not None:
            params["full_name"] = full_name
        if office_country is not None:
            params["office_country"] = office_country
        if position is not None:
            params["position"] = position
        if email is not None:
            params["email"] = email
        if phone is not None:
            params["phone"] = phone
        if is_active is not None:
            params["is_active"] = str(int(is_active))
        if role is not None:
            params["role"] = role

        r = self._client.put(
            f"{self.account_api_url}/employees/{int(employee_id)}",
            params=params,
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json()

    def regenerate_employee_key(self, employee_id: int) -> dict:
        r = self._client.post(
            f"{self.account_api_url}/employees/{int(employee_id)}/regenerate-key",
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json()

    def list_todo(self) -> list[dict]:
        r = self._client.get(
            f"{self.todo_api_url}/todo",
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json().get("items", [])

    def create_todo(
        self,
        title: str,
        deadline: str,
        employee_ids: list[int],
        description: str | None = None,
    ) -> dict:
        params = {
            "title": title,
            "deadline": deadline,
            "employee_ids": ",".join(str(x) for x in employee_ids),
        }
        if description:
            params["description"] = description

        r = self._client.post(
            f"{self.todo_api_url}/todo",
            params=params,
            headers=self._auth_headers(),
        )
        if r.status_code >= 400:
            raise RuntimeError(_extract_error(r))
        return r.json()

    def complete_todo(self, assignment_id: int, completion_note: str | None = None) -> dict:
        params = {}
        if completion_note:
            params["completion_note"] = completion_note

        r = self._client.put(
            f"{self.todo_api_url}/todo/{int(assignment_id)}/complete",
            params=params,
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
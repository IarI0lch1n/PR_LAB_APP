from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class AppConfig:
    chat_api_url: str
    file_api_url: str
    account_api_url: str
    todo_api_url: str


def get_config() -> AppConfig:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)

    chat = os.getenv("CHAT_API_URL", "http://localhost:8001").rstrip("/")
    files = os.getenv("FILE_API_URL", "http://localhost:8002").rstrip("/")
    acc = os.getenv("ACCOUNT_API_URL", "http://localhost:8003").rstrip("/")
    todo = os.getenv("TODO_API_URL", "http://localhost:8005").rstrip("/")

    return AppConfig(
        chat_api_url=chat,
        file_api_url=files,
        account_api_url=acc,
        todo_api_url=todo,
    )
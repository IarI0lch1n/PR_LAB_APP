import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  

@dataclass(frozen=True)
class AppConfig:
    chat_api_url: str
    file_api_url: str
    account_api_url: str

def get_config() -> AppConfig:
    chat = os.getenv("CHAT_API_URL", "http://localhost:8001").rstrip("/")
    files = os.getenv("FILE_API_URL", "http://localhost:8002").rstrip("/")
    acc = os.getenv("ACCOUNT_API_URL", "http://localhost:8003").rstrip("/")
    return AppConfig(chat_api_url=chat, file_api_url=files, account_api_url=acc)
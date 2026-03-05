from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Message:
    id: int
    text: str
    file: Optional[str] = None

@dataclass
class AppState:
    messages: List[Message] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
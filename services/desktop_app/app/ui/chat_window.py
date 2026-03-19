from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem
)

from app.api_client import ApiClient
from app.ui.widgets import show_error, show_info


class ChatWindow(QWidget):
    """
    Separate window with full conversation with one user.
    """
    def __init__(self, api: ApiClient, other_id: int, title: str):
        super().__init__()
        self.api = api
        self.other_id = other_id

        self.setWindowTitle(f"Chat with {title}")
        self.resize(520, 700)

        root = QVBoxLayout(self)

        header = QLabel(f"Conversation: {title}")
        header.setStyleSheet("font-size: 16px; font-weight: 600;")
        root.addWidget(header)

        self.messages = QListWidget()
        root.addWidget(self.messages, 1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type message...")
        row.addWidget(self.input, 1)

        self.send_btn = QPushButton("Send")
        row.addWidget(self.send_btn)

        self.refresh_btn = QPushButton("Refresh")
        row.addWidget(self.refresh_btn)

        root.addLayout(row)

        self.send_btn.clicked.connect(self.on_send)
        self.refresh_btn.clicked.connect(self.load_messages)

        self.load_messages()

    def load_messages(self) -> None:
        self.messages.clear()
        try:
            msgs = self.api.get_chat_messages(self.other_id)
        except Exception as e:
            show_error(self, "Chat", str(e))
            return

        if not msgs:
            it = QListWidgetItem("(no messages)")
            it.setFlags(Qt.NoItemFlags)
            self.messages.addItem(it)
            return

        for m in msgs:
            sender = m.get("sender_name") or f'#{m.get("sender_employee_id")}'
            text = m.get("text") or ""
            it = QListWidgetItem(f"{sender}: {text}")
            it.setFlags(Qt.ItemIsEnabled)
            self.messages.addItem(it)

        self.messages.scrollToBottom()

    def on_send(self) -> None:
        txt = self.input.text().strip()
        if not txt:
            show_info(self, "Send", "Message is empty.")
            return

        try:
            self.api.send_chat_message(self.other_id, txt, file_id=None)
        except Exception as e:
            show_error(self, "Send failed", str(e))
            return

        self.input.clear()
        self.load_messages()
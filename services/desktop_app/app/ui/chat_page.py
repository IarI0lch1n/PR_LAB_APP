from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox
)

from app.api_client import ApiClient
from app.ui.widgets import show_error, show_info


class ChatPage(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

        root = QVBoxLayout(self)

        title = QLabel("Chat")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        # Form
        form_box = QGroupBox("Send message")
        form = QVBoxLayout(form_box)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Text:"))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("hello")
        row1.addWidget(self.text_input)
        form.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Attach filename (optional):"))
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("example.pdf")
        row2.addWidget(self.file_input)
        form.addLayout(row2)

        btns = QHBoxLayout()
        self.send_btn = QPushButton("Send")
        self.refresh_btn = QPushButton("Refresh")
        btns.addWidget(self.send_btn)
        btns.addWidget(self.refresh_btn)
        btns.addStretch(1)
        form.addLayout(btns)

        root.addWidget(form_box)

        # Messages list
        self.list = QListWidget()
        root.addWidget(QLabel("Messages:"))
        root.addWidget(self.list, 1)

        # Hook events
        self.send_btn.clicked.connect(self.on_send)
        self.refresh_btn.clicked.connect(self.load_messages)

        # initial load
        self.load_messages()

    def load_messages(self) -> None:
        self.list.clear()
        try:
            msgs = self.api.get_messages()
        except Exception as e:
            show_error(self, "Chat API error", str(e))
            return

        if not msgs:
            item = QListWidgetItem("No messages yet")
            item.setFlags(Qt.NoItemFlags)
            self.list.addItem(item)
            return

        for m in msgs:
            mid = m.get("id", "?")
            text = m.get("text", "")
            file_ = m.get("file", None)
            label = f"#{mid}: {text}"
            if file_:
                label += f"  [file: {file_}]"
            self.list.addItem(label)

    def on_send(self) -> None:
        text = self.text_input.text().strip()
        filename = self.file_input.text().strip()

        if not text:
            show_info(self, "Validation", "Text is required.")
            return

        try:
            self.api.send_message(text=text, filename=(filename or None))
        except Exception as e:
            show_error(self, "Send failed", str(e))
            return

        self.text_input.clear()
        self.file_input.clear()
        self.load_messages()
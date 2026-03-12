from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QGroupBox, QComboBox
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

        form_box = QGroupBox("Send message")
        form = QVBoxLayout(form_box)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Text:"))
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("hello")
        row1.addWidget(self.text_input)
        form.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Attach file (optional):"))

        self.file_combo = QComboBox()
        self.file_combo.addItem("None", None)
        row2.addWidget(self.file_combo)

        self.reload_files_btn = QPushButton("Reload files")
        row2.addWidget(self.reload_files_btn)

        form.addLayout(row2)

        btns = QHBoxLayout()
        self.send_btn = QPushButton("Send")
        self.refresh_btn = QPushButton("Refresh")
        self.delete_btn = QPushButton("Delete selected")
        btns.addWidget(self.send_btn)
        btns.addWidget(self.refresh_btn)
        btns.addWidget(self.delete_btn)
        btns.addStretch(1)
        form.addLayout(btns)

        root.addWidget(form_box)

        self.list = QListWidget()
        root.addWidget(QLabel("Messages:"))
        root.addWidget(self.list, 1)

        self.send_btn.clicked.connect(self.on_send)
        self.refresh_btn.clicked.connect(self.load_messages)
        self.delete_btn.clicked.connect(self.on_delete)
        self.reload_files_btn.clicked.connect(self.load_files_into_combo)

        self.load_files_into_combo()
        self.load_messages()

    def load_files_into_combo(self) -> None:
        current = self.file_combo.currentData()

        self.file_combo.clear()
        self.file_combo.addItem("None", None)

        try:
            files = self.api.list_files()  
        except Exception:
            files = []

        for f in files:
            fid = f.get("id")
            name = f.get("filename")
            if fid is None or not name:
                continue
            self.file_combo.addItem(name, int(fid))

        if current is not None:
            idx = self.file_combo.findData(current)
            if idx >= 0:
                self.file_combo.setCurrentIndex(idx)

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
            filename = m.get("file", None)  
            file_id = m.get("file_id", None)

            label = f"#{mid}: {text}"
            if filename:
                label += f"  [file: {filename}]"
                if file_id is not None:
                    label += f" (id={file_id})"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, mid)
            self.list.addItem(item)

    def on_send(self) -> None:
        text = self.text_input.text().strip()
        if not text:
            show_info(self, "Validation", "Text is required.")
            return

        file_id = self.file_combo.currentData()  

        try:
            self.api.send_message(text=text, file_id=file_id)
        except Exception as e:
            show_error(self, "Send failed", str(e))
            return

        self.text_input.clear()
        self.load_messages()

    def on_delete(self) -> None:
        item = self.list.currentItem()
        if not item:
            show_info(self, "Delete", "Select a message first.")
            return

        mid = item.data(Qt.UserRole)
        if mid in (None, "?", ""):
            show_info(self, "Delete", "This item cannot be deleted.")
            return

        try:
            self.api.delete_message(int(mid))
        except Exception as e:
            show_error(self, "Delete failed", str(e))
            return

        self.load_messages()
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QFileDialog, QGroupBox
)

from app.api_client import ApiClient
from app.ui.widgets import show_error, show_info


class ChatWindow(QWidget):
    def __init__(self, api: ApiClient, other_id: int, title: str):
        super().__init__()
        self.api = api
        self.other_id = other_id

        self.setWindowTitle(f"Chat with {title}")
        self.resize(700, 760)

        root = QVBoxLayout(self)

        header = QLabel(f"Conversation: {title}")
        header.setStyleSheet("font-size: 16px; font-weight: 600;")
        root.addWidget(header)

        self.messages = QListWidget()
        root.addWidget(self.messages, 1)

        # attachment download box
        dl_box = QGroupBox("Download attachment from selected message")
        dl = QHBoxLayout(dl_box)

        self.save_path = QLineEdit()
        self.save_path.setPlaceholderText("Choose where to save attached file...")
        dl.addWidget(self.save_path, 1)

        self.choose_btn = QPushButton("Save as...")
        self.download_btn = QPushButton("Download")
        dl.addWidget(self.choose_btn)
        dl.addWidget(self.download_btn)

        root.addWidget(dl_box)

        # send row
        send_box = QGroupBox("Send message")
        send_layout = QVBoxLayout(send_box)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Text:"))
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type message...")
        row1.addWidget(self.input, 1)
        send_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Attach file (optional):"))
        self.file_combo = QComboBox()
        self.file_combo.addItem("None", None)
        row2.addWidget(self.file_combo, 1)

        self.reload_files_btn = QPushButton("Reload files")
        row2.addWidget(self.reload_files_btn)
        send_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.send_btn = QPushButton("Send")
        self.refresh_btn = QPushButton("Refresh")
        row3.addWidget(self.send_btn)
        row3.addWidget(self.refresh_btn)
        row3.addStretch(1)
        send_layout.addLayout(row3)

        root.addWidget(send_box)

        self.send_btn.clicked.connect(self.on_send)
        self.refresh_btn.clicked.connect(self.load_messages)
        self.reload_files_btn.clicked.connect(self.load_files_into_combo)
        self.choose_btn.clicked.connect(self.on_choose_save)
        self.download_btn.clicked.connect(self.on_download_selected_attachment)

        self.load_files_into_combo()
        self.load_messages()

    def load_files_into_combo(self) -> None:
        current = self.file_combo.currentData()

        self.file_combo.clear()
        self.file_combo.addItem("None", None)

        try:
            files = self.api.list_files()
        except Exception as e:
            show_error(self, "Files", str(e))
            return

        for f in files:
            fid = f.get("id")
            if fid is None:
                continue

            name = f.get("filename") or f"file #{fid}"
            owner_name = f.get("owner_name") or "unknown"
            shared = bool(f.get("shared"))
            suffix = " [shared]" if shared else ""
            label = f"{name} | author: {owner_name}{suffix}"

            self.file_combo.addItem(label, int(fid))

        if current is not None:
            idx = self.file_combo.findData(current)
            if idx >= 0:
                self.file_combo.setCurrentIndex(idx)

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

            line = f"{sender}: {text}"

            if m.get("file_id") is not None:
                filename = m.get("filename") or f'file #{m["file_id"]}'
                owner = m.get("file_owner_name") or "unknown"
                line += f"\n  Attachment: {filename} (author: {owner})"

            it = QListWidgetItem(line)
            it.setData(Qt.UserRole, dict(m))
            self.messages.addItem(it)

        self.messages.scrollToBottom()

    def on_send(self) -> None:
        txt = self.input.text().strip()
        if not txt:
            show_info(self, "Send", "Message is empty.")
            return

        file_id = self.file_combo.currentData()

        try:
            self.api.send_chat_message(self.other_id, txt, file_id=file_id)
        except Exception as e:
            show_error(self, "Send failed", str(e))
            return

        self.input.clear()
        self.load_messages()

    def on_choose_save(self) -> None:
        msg = self._selected_message()
        if not msg or msg.get("file_id") is None:
            show_info(self, "Download", "Select a message with an attachment.")
            return

        filename = msg.get("filename") or f'file_{msg["file_id"]}'
        out_path, _ = QFileDialog.getSaveFileName(self, "Save attachment as", filename)
        if out_path:
            self.save_path.setText(out_path)

    def on_download_selected_attachment(self) -> None:
        msg = self._selected_message()
        if not msg or msg.get("file_id") is None:
            show_info(self, "Download", "Select a message with an attachment.")
            return

        file_id = int(msg["file_id"])
        filename = msg.get("filename") or f"file_{file_id}"
        out_path = self.save_path.text().strip()

        if not out_path:
            out_path = str((Path.home() / "Downloads" / filename))
            self.save_path.setText(out_path)

        try:
            self.api.download_file(file_id, out_path)
        except Exception as e:
            show_error(self, "Download failed", str(e))
            return

        show_info(self, "Download", f"Saved:\n{out_path}")

    def _selected_message(self) -> dict | None:
        item = self.messages.currentItem()
        if not item:
            return None
        data = item.data(Qt.UserRole)
        if not isinstance(data, dict):
            return None
        return data
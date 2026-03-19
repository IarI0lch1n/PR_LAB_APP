from __future__ import annotations

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QCompleter
)

from app.api_client import ApiClient
from app.ui.chat_window import ChatWindow
from app.ui.widgets import show_error, show_info


class ChatsWindow(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

        self.setWindowTitle("Chats")
        self.resize(700, 600)

        root = QVBoxLayout(self)

        sr = QHBoxLayout()
        sr.addWidget(QLabel("New chat:"))

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name / email / phone")
        sr.addWidget(self.search, 1)

        self.open_btn = QPushButton("Open")
        sr.addWidget(self.open_btn)
        root.addLayout(sr)

        self._suggestions: list[dict] = []
        self._model = QStringListModel()
        self._completer = QCompleter(self._model)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self.search.setCompleter(self._completer)

        root.addWidget(QLabel("Your chats:"))
        self.list = QListWidget()
        root.addWidget(self.list, 1)

        bottom = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        bottom.addWidget(self.refresh_btn)
        bottom.addStretch(1)
        root.addLayout(bottom)

        self.refresh_btn.clicked.connect(self.load_chats)
        self.search.textChanged.connect(self.on_search_changed)
        self.open_btn.clicked.connect(self.open_chat_from_search)
        self.list.itemDoubleClicked.connect(self.open_chat_from_item)

        self.load_chats()

    def load_chats(self) -> None:
        self.list.clear()

        try:
            chats = self.api.list_chats()
        except Exception as e:
            show_error(self, "Chats", str(e))
            return

        if not chats:
            it = QListWidgetItem("(no chats yet)")
            it.setFlags(Qt.NoItemFlags)
            self.list.addItem(it)
            return

        for c in chats:
            other_id = c.get("other_id")
            if other_id is None:
                continue

            name = c.get("full_name") or f"User #{other_id}"
            email = c.get("email") or "-"
            phone = c.get("phone") or "-"
            title = f"{name} | {email} | {phone}"

            it = QListWidgetItem(title)
            it.setData(Qt.UserRole, int(other_id))
            self.list.addItem(it)

    def on_search_changed(self, text: str) -> None:
        text = text.strip()

        if "|" in text:
            return

        if len(text) < 2:
            self._model.setStringList([])
            self._suggestions = []
            return

        try:
            items = self.api.search_employees(text)
        except Exception as e:
            show_error(self, "Search failed", str(e))
            self._model.setStringList([])
            self._suggestions = []
            return

        self._suggestions = items

        view = []
        for it in items[:10]:
            s = f'{it.get("full_name") or "-"} | {it.get("email") or "-"} | {it.get("phone") or "-"}'
            view.append(s)

        self._model.setStringList(view)

    def open_chat_from_search(self) -> None:
        if not self._suggestions:
            show_info(self, "Open chat", "No users found.")
            return

        typed = self.search.text().strip().lower()

        selected = None
        for it in self._suggestions:
            line = f'{(it.get("full_name") or "-")} | {(it.get("email") or "-")} | {(it.get("phone") or "-")}'.lower()
            if line == typed:
                selected = it
                break

        if selected is None:
            selected = self._suggestions[0]

        other_id = int(selected["id"])
        title = selected.get("full_name") or f"User #{other_id}"
        self.open_chat(other_id, title)

    def open_chat_from_item(self, item: QListWidgetItem) -> None:
        other_id = item.data(Qt.UserRole)
        if not other_id:
            return
        self.open_chat(int(other_id), item.text())

    def open_chat(self, other_id: int, title: str) -> None:
        self._child = ChatWindow(self.api, other_id, title)
        self._child.show()
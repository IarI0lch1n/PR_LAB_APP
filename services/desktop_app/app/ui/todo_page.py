from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QTextEdit, QFileDialog, QGroupBox
)

from app.api_client import ApiClient
from app.ui.widgets import show_error, show_info


class ToDoPage(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

        root = QVBoxLayout(self)

        title = QLabel("ToDo")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        self.list = QListWidget()
        root.addWidget(self.list, 1)

        btns = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.complete_btn = QPushButton("Mark completed")
        self.save_txt_btn = QPushButton("Save selected to TXT")
        btns.addWidget(self.refresh_btn)
        btns.addWidget(self.complete_btn)
        btns.addWidget(self.save_txt_btn)
        btns.addStretch(1)
        root.addLayout(btns)

        # creator box for HR/Admin
        try:
            me = self.api.me()
            role = str(me.get("role") or "employee").lower()
        except Exception:
            role = "employee"

        if role in ("admin", "hr"):
            box = QGroupBox("Create ToDo list")
            form = QVBoxLayout(box)

            self.todo_title = QLineEdit()
            self.todo_title.setPlaceholderText("Title")
            form.addWidget(self.todo_title)

            self.todo_desc = QTextEdit()
            self.todo_desc.setPlaceholderText("Description")
            form.addWidget(self.todo_desc)

            self.todo_deadline = QLineEdit()
            self.todo_deadline.setPlaceholderText("Deadline (YYYY-MM-DD HH:MM:SS)")
            form.addWidget(self.todo_deadline)

            self.todo_employees = QLineEdit()
            self.todo_employees.setPlaceholderText("Employee IDs, comma separated (e.g. 2,3,5)")
            form.addWidget(self.todo_employees)

            self.todo_send_btn = QPushButton("Send ToDo list")
            form.addWidget(self.todo_send_btn)

            self.todo_send_btn.clicked.connect(self.on_create_todo)
            root.addWidget(box)

        self.refresh_btn.clicked.connect(self.load_items)
        self.complete_btn.clicked.connect(self.on_complete)
        self.save_txt_btn.clicked.connect(self.on_save_txt)

        self.load_items()

    def load_items(self):
        self.list.clear()
        try:
            items = self.api.list_todo()
        except Exception as e:
            show_error(self, "ToDo", str(e))
            return

        if not items:
            it = QListWidgetItem("(no tasks)")
            it.setFlags(Qt.NoItemFlags)
            self.list.addItem(it)
            return

        for t in items:
            status = "completed" if t.get("is_completed") else "open"
            line = f'{t.get("title")} | deadline: {t.get("deadline")} | {status}'
            it = QListWidgetItem(line)
            it.setData(Qt.UserRole, dict(t))
            self.list.addItem(it)

    def current_item(self) -> dict | None:
        item = self.list.currentItem()
        if not item:
            return None
        data = item.data(Qt.UserRole)
        if not isinstance(data, dict):
            return None
        return data

    def on_complete(self):
        t = self.current_item()
        if not t:
            show_info(self, "ToDo", "Select a task first.")
            return

        if t.get("is_completed"):
            show_info(self, "ToDo", "Task is already completed.")
            return

        try:
            self.api.complete_todo(int(t["id"]))
        except Exception as e:
            show_error(self, "Complete task failed", str(e))
            return

        show_info(self, "ToDo", "Task marked as completed.")
        self.load_items()

    def on_save_txt(self):
        t = self.current_item()
        if not t:
            show_info(self, "ToDo", "Select a task first.")
            return

        default_name = f'todo_{t.get("id")}.txt'
        path, _ = QFileDialog.getSaveFileName(self, "Save task to TXT", default_name, "Text files (*.txt)")
        if not path:
            return

        content = (
            f'Title: {t.get("title")}\n'
            f'Description: {t.get("description") or "-"}\n'
            f'Deadline: {t.get("deadline")}\n'
            f'Created by: {t.get("created_by_name") or "-"}\n'
            f'Status: {"completed" if t.get("is_completed") else "open"}\n'
            f'Note: {t.get("completion_note") or "-"}\n'
        )

        Path(path).write_text(content, encoding="utf-8")
        show_info(self, "ToDo", f"Saved:\n{path}")

    def on_create_todo(self):
        title = self.todo_title.text().strip()
        deadline = self.todo_deadline.text().strip()
        employee_ids_raw = self.todo_employees.text().strip()
        description = self.todo_desc.toPlainText().strip()

        if not title or not deadline or not employee_ids_raw:
            show_info(self, "ToDo", "Title, deadline and employee IDs are required.")
            return

        try:
            ids = [int(x.strip()) for x in employee_ids_raw.split(",") if x.strip()]
        except Exception:
            show_error(self, "ToDo", "Employee IDs must be comma-separated integers.")
            return

        try:
            self.api.create_todo(title, deadline, ids, description or None)
        except Exception as e:
            show_error(self, "Create ToDo failed", str(e))
            return

        show_info(self, "ToDo", "ToDo list sent.")
        self.todo_title.clear()
        self.todo_desc.clear()
        self.todo_deadline.clear()
        self.todo_employees.clear()
        self.load_items()
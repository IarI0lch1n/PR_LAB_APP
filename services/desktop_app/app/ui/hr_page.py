from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QGroupBox
)

from app.api_client import ApiClient
from app.ui.widgets import show_error, show_info


class HRPage(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

        root = QVBoxLayout(self)

        title = QLabel("HR / Admin")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        content = QHBoxLayout()
        root.addLayout(content, 1)

        # left: employee list
        left = QVBoxLayout()
        left.addWidget(QLabel("Employees:"))

        self.list = QListWidget()
        left.addWidget(self.list, 1)

        self.refresh_btn = QPushButton("Refresh")
        left.addWidget(self.refresh_btn)

        content.addLayout(left, 1)

        # right: form
        right_box = QGroupBox("Employee form")
        right = QVBoxLayout(right_box)

        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("Full name")
        right.addWidget(self.full_name)

        self.email = QLineEdit()
        self.email.setPlaceholderText("Email")
        right.addWidget(self.email)

        self.phone = QLineEdit()
        self.phone.setPlaceholderText("Phone")
        right.addWidget(self.phone)

        self.office_country = QLineEdit()
        self.office_country.setPlaceholderText("Office country")
        right.addWidget(self.office_country)

        self.position = QLineEdit()
        self.position.setPlaceholderText("Position")
        right.addWidget(self.position)

        self.role = QComboBox()
        self.role.addItems(["employee", "hr", "admin"])
        right.addWidget(self.role)

        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(True)
        right.addWidget(self.active_checkbox)

        btns1 = QHBoxLayout()
        self.create_btn = QPushButton("Create account")
        self.update_btn = QPushButton("Update employee")
        btns1.addWidget(self.create_btn)
        btns1.addWidget(self.update_btn)
        right.addLayout(btns1)

        btns2 = QHBoxLayout()
        self.regen_btn = QPushButton("Regenerate key + send email")
        btns2.addWidget(self.regen_btn)
        right.addLayout(btns2)

        content.addWidget(right_box, 1)

        self.refresh_btn.clicked.connect(self.load_employees)
        self.list.currentItemChanged.connect(self.on_select_employee)
        self.create_btn.clicked.connect(self.on_create)
        self.update_btn.clicked.connect(self.on_update)
        self.regen_btn.clicked.connect(self.on_regenerate)

        self.load_employees()

    def load_employees(self):
        self.list.clear()
        try:
            items = self.api.list_employees()
        except Exception as e:
            show_error(self, "HR", str(e))
            return

        for emp in items:
            label = f'{emp["full_name"]} | {emp.get("email") or "-"} | {emp["role"]}'
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, emp)
            self.list.addItem(it)

    def on_select_employee(self, current, previous):
        if not current:
            return
        emp = current.data(Qt.UserRole)
        if not isinstance(emp, dict):
            return

        self.full_name.setText(emp.get("full_name") or "")
        self.email.setText(emp.get("email") or "")
        self.phone.setText(emp.get("phone") or "")
        self.office_country.setText(emp.get("office_country") or "")
        self.position.setText(emp.get("position") or "")

        role = emp.get("role") or "employee"
        idx = self.role.findText(role)
        if idx >= 0:
            self.role.setCurrentIndex(idx)

        self.active_checkbox.setChecked(bool(emp.get("is_active")))

    def on_create(self):
        try:
            result = self.api.create_employee(
                full_name=self.full_name.text().strip(),
                email=self.email.text().strip() or None,
                phone=self.phone.text().strip() or None,
                office_country=self.office_country.text().strip(),
                position=self.position.text().strip(),
                role=self.role.currentText(),
            )
        except Exception as e:
            show_error(self, "Create account failed", str(e))
            return

        msg = (
            f'Employee created.\n\n'
            f'ID: {result.get("id")}\n'
            f'Key: {result.get("employee_key")}\n\n'
            f'This key is also sent by email if SMTP is configured.'
        )
        show_info(self, "Create account", msg)
        self.load_employees()

    def on_update(self):
        item = self.list.currentItem()
        if not item:
            show_info(self, "Update", "Select an employee first.")
            return

        emp = item.data(Qt.UserRole)
        try:
            self.api.update_employee(
                employee_id=int(emp["id"]),
                full_name=self.full_name.text().strip() or None,
                email=self.email.text().strip() or None,
                phone=self.phone.text().strip() or None,
                office_country=self.office_country.text().strip() or None,
                position=self.position.text().strip() or None,
                is_active=1 if self.active_checkbox.isChecked() else 0,
                role=self.role.currentText(),
            )
        except Exception as e:
            show_error(self, "Update failed", str(e))
            return

        show_info(self, "Update", "Employee updated.")
        self.load_employees()

    def on_regenerate(self):
        item = self.list.currentItem()
        if not item:
            show_info(self, "Regenerate key", "Select an employee first.")
            return

        emp = item.data(Qt.UserRole)
        try:
            result = self.api.regenerate_employee_key(int(emp["id"]))
        except Exception as e:
            show_error(self, "Regenerate key failed", str(e))
            return

        show_info(
            self,
            "Regenerate key",
            f'New key generated.\n\nID: {result.get("id")}\nKey: {result.get("employee_key")}\n\nEmail was sent if SMTP is configured.'
        )
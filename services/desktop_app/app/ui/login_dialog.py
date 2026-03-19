from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from app.api_client import ApiClient
from app.ui.widgets import show_error

class LoginDialog(QDialog):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self.setWindowTitle("Employee Login")
        self.setModal(True)
        self.resize(420, 160)

        root = QVBoxLayout(self)
        root.addWidget(QLabel("Enter your employee key (X-Employee-Key):"))

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("paste key here...")
        root.addWidget(self.key_input)

        self.btn = QPushButton("Login")
        self.btn.clicked.connect(self.on_login)
        root.addWidget(self.btn)

        self.me_data = None

    def on_login(self):
        key = self.key_input.text().strip()
        if not key:
            show_error(self, "Login", "Key is required")
            return

        try:
            self.api.set_employee_key(key)
            self.me_data = self.api.me()
            self.accept()
        except Exception as e:
            show_error(self, "Login failed", str(e))
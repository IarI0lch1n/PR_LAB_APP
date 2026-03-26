from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QToolBar, QLabel, QWidget, QSizePolicy,
    QMessageBox
)

from app.api_client import ApiClient
from app.theme import ThemeManager

from app.ui.chats_window import ChatsWindow
from app.ui.files_page import FilesPage
from app.ui.publics_page import PublicsPage
from app.ui.hr_page import HRPage
from app.ui.todo_page import ToDoPage


class MainWindow(QMainWindow):
    logout_requested = Signal()

    def __init__(self, api: ApiClient, theme_manager: ThemeManager, qt_app):
        super().__init__()
        self.api = api
        self.theme_manager = theme_manager
        self.qt_app = qt_app

        self.setWindowTitle("PR Messenger")
        self.resize(1100, 760)

        tb = QToolBar("Main")
        self.addToolBar(tb)

        self.theme_action = QAction("🌙", self)
        self.theme_action.setToolTip("Toggle theme")
        self.theme_action.triggered.connect(self.on_toggle_theme)
        tb.addAction(self.theme_action)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        self.user_label = QLabel("User: -")
        self.user_label.setStyleSheet("padding: 0 10px;")
        tb.addWidget(self.user_label)

        self.logout_action = QAction("Logout", self)
        self.logout_action.setToolTip("Logout from current account")
        self.logout_action.triggered.connect(self.on_logout)
        tb.addAction(self.logout_action)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tabs.addTab(ChatsWindow(api), "Chat")
        self.tabs.addTab(PublicsPage(), "Publics")
        self.tabs.addTab(FilesPage(api), "Files")
        self.tabs.addTab(ToDoPage(api), "ToDo")

        self._load_me_and_hr_tab()
        self._apply_theme()

    def _load_me_and_hr_tab(self):
        try:
            me = self.api.me()
            full_name = me.get("full_name") or "Unknown"
            role = me.get("role") or "employee"
            email = me.get("email") or "-"
            self.user_label.setText(f"{full_name} | {role} | {email}")

            role_l = str(role).lower()
            if role_l in ("admin", "hr"):
                self.tabs.addTab(HRPage(self.api), "HR")
        except Exception:
            self.user_label.setText("User: unknown")

    def on_toggle_theme(self):
        self.theme_manager.toggle()
        self._apply_theme()

    def _apply_theme(self):
        self.theme_manager.apply(self.qt_app)

    def on_logout(self):
        reply = QMessageBox.question(
            self,
            "Logout",
            "Do you want to logout from current account?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.api.logout()
        self.logout_requested.emit()
        self.close()
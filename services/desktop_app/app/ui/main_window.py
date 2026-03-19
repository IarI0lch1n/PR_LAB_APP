from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from app.api_client import ApiClient
from app.theme import ThemeManager

from app.ui.chats_window import ChatsWindow
from app.ui.files_page import FilesPage
from app.ui.publics_page import PublicsPage


class MainWindow(QMainWindow):
    def __init__(self, api: ApiClient, theme_manager: ThemeManager, qt_app):
        super().__init__()
        self.api = api
        self.theme_manager = theme_manager
        self.qt_app = qt_app

        self.setWindowTitle("PR Messenger — " + (getattr(api, "current_user_name", "") or ""))
        self.resize(1000, 700)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # ✅ Вместо старого ChatPage — новый чат (диалоги)
        self.tabs.addTab(ChatsWindow(api), "Chat")

        # Остальные вкладки как раньше
        self.tabs.addTab(PublicsPage(), "Publics")
        self.tabs.addTab(FilesPage(api), "Files")

        self.theme_manager.apply(self.qt_app)
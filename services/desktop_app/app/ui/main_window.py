from __future__ import annotations

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QTabWidget, QToolBar

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

        self.setWindowTitle("PR Messenger")
        self.resize(1000, 700)

        tb = QToolBar("Main")
        self.addToolBar(tb)

        self.theme_action = QAction("🌙", self)
        self.theme_action.setToolTip("Toggle theme")
        self.theme_action.triggered.connect(self.on_toggle_theme)
        tb.addAction(self.theme_action)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tabs.addTab(ChatsWindow(api), "Chat")
        self.tabs.addTab(PublicsPage(), "Publics")
        self.tabs.addTab(FilesPage(api), "Files")

        self._apply_theme()

    def on_toggle_theme(self):
        if hasattr(self.theme_manager, "toggle"):
            self.theme_manager.toggle()
        elif hasattr(self.theme_manager, "is_dark"):
            self.theme_manager.is_dark = not self.theme_manager.is_dark
        self._apply_theme()

    def _apply_theme(self):
        try:
            self.theme_manager.apply(self.qt_app)
        except TypeError:
            self.theme_manager.apply()
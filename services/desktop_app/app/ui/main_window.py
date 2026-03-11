from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget, QToolBar
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from app.api_client import ApiClient
from app.theme import ThemeManager
from app.ui.chat_page import ChatPage
from app.ui.files_page import FilesPage
from app.ui.publics_page import PublicsPage


class MainWindow(QMainWindow):
    def __init__(self, api: ApiClient, theme: ThemeManager, qt_app):
        super().__init__()
        self.api = api
        self.theme = theme
        self.qt_app = qt_app

        self.setWindowTitle("PR Desktop App (Chat + Publics + Files)")
        self.resize(1000, 650)

        self.tabs = QTabWidget()
        self.tabs.addTab(ChatPage(api), "Chat")
        self.tabs.addTab(PublicsPage(), "Publics")
        self.tabs.addTab(FilesPage(api), "Files")
        self.setCentralWidget(self.tabs)

        self.toolbar = QToolBar("Main")
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self.theme_action = QAction(self.theme.current.make_toggle_icon(), "Toggle theme", self)
        self.theme_action.triggered.connect(self.on_toggle_theme)
        self.toolbar.addAction(self.theme_action)

    def on_toggle_theme(self) -> None:
        self.theme.toggle()
        self.theme.apply(self.qt_app)

        self.theme_action.setIcon(self.theme.current.make_toggle_icon())

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        self.tabs.update()

    def closeEvent(self, event):
        try:
            self.api.close()
        except Exception:
            pass
        super().closeEvent(event)
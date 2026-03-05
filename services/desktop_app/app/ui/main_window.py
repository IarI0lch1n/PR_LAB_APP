from __future__ import annotations
from PySide6.QtWidgets import QMainWindow, QTabWidget
from app.api_client import ApiClient
from app.ui.chat_page import ChatPage
from app.ui.files_page import FilesPage
from app.ui.publics_page import PublicsPage

class MainWindow(QMainWindow):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

        self.setWindowTitle("PR Desktop App (Chat + Publics + Files)")
        self.resize(1000, 650)

        tabs = QTabWidget()
        tabs.addTab(ChatPage(api), "Chat")
        tabs.addTab(PublicsPage(), "Publics")
        tabs.addTab(FilesPage(api), "Files")

        self.setCentralWidget(tabs)

    def closeEvent(self, event):
        # close http client cleanly
        try:
            self.api.close()
        except Exception:
            pass
        super().closeEvent(event)
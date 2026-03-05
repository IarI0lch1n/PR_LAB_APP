from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt

class PublicsPage(QWidget):
    """
    Placeholder for "Telegram-like publics/channels".
    We'll implement it in later labs (DB + roles + subscriptions).
    """
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)

        title = QLabel("Publics")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        info = QLabel(
            "Заготовка.\n"
            "В следующих лабах тут будут: создание паблика, подписки, список постов, модерация.\n"
            "Пока что для примера тут будут вставки того, что якобы будет здесь."
        )
        info.setStyleSheet("color: #555;")
        root.addWidget(info)

        self.list = QListWidget()
        root.addWidget(self.list, 1)

        # demo items
        for name in ["Announcements", "GameDev", "University"]:
            it = QListWidgetItem(f"#{name} (stub)")
            it.setFlags(Qt.ItemIsEnabled)
            self.list.addItem(it)
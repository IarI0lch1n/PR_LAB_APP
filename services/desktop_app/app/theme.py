from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from PySide6.QtGui import (
    QPalette, QColor, QIcon, QPixmap, QPainter, QPen, QBrush
)
from PySide6.QtCore import Qt


class ThemeFactory(ABC):
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def make_palette(self) -> QPalette: ...

    @abstractmethod
    def make_toggle_icon(self) -> QIcon:
        """Icon shown on the toggle button when THIS theme is active."""
        ...

    @abstractmethod
    def make_stylesheet(self) -> str:
        """Qt stylesheet for the theme."""
        ...


class LightThemeFactory(ThemeFactory):
    def name(self) -> str:
        return "light"

    def make_palette(self) -> QPalette:
        p = QPalette()
        p.setColor(QPalette.Window, QColor("#f5f5f5"))
        p.setColor(QPalette.WindowText, QColor("#111111"))
        p.setColor(QPalette.Base, QColor("#ffffff"))
        p.setColor(QPalette.AlternateBase, QColor("#f0f0f0"))
        p.setColor(QPalette.Text, QColor("#111111"))
        p.setColor(QPalette.Button, QColor("#e6e6e6"))
        p.setColor(QPalette.ButtonText, QColor("#111111"))
        p.setColor(QPalette.Highlight, QColor("#2f6fff"))
        p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        return p

    def make_toggle_icon(self) -> QIcon:
        return _make_moon_icon()

    def make_stylesheet(self) -> str:
        return """
        QTabBar::tab {
            padding: 6px 10px;
        }
        """


class DarkThemeFactory(ThemeFactory):
    def name(self) -> str:
        return "dark"

    def make_palette(self) -> QPalette:
        p = QPalette()
        p.setColor(QPalette.Window, QColor("#121212"))
        p.setColor(QPalette.WindowText, QColor("#f0f0f0"))
        p.setColor(QPalette.Base, QColor("#1b1b1b"))
        p.setColor(QPalette.AlternateBase, QColor("#202020"))
        p.setColor(QPalette.Text, QColor("#f0f0f0"))
        p.setColor(QPalette.Button, QColor("#242424"))
        p.setColor(QPalette.ButtonText, QColor("#f0f0f0"))
        p.setColor(QPalette.Highlight, QColor("#3d7eff"))
        p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        return p

    def make_toggle_icon(self) -> QIcon:
        return _make_sun_icon()

    def make_stylesheet(self) -> str:
        return """
        QMainWindow, QWidget {
            background-color: #121212;
            color: #f0f0f0;
        }

        QToolBar {
            background: #1b1b1b;
            border: 0px;
            spacing: 6px;
        }

        QTabWidget {
            background: #121212;
            color: #f0f0f0;
        }

        QTabWidget::pane {
            border: 0px;
        }

        QTabBar::tab {
            background: #1b1b1b;
            color: #dcdcdc;
            padding: 6px 10px;
            border: 1px solid #2a2a2a;
            border-bottom: 0px;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background: #242424;
            color: #ffffff;
        }

        QPushButton {
            background-color: #242424;
            color: #f0f0f0;
            border: 1px solid #2f2f2f;
            padding: 5px 10px;
            border-radius: 4px;
        }

        QPushButton:hover {
            background-color: #2c2c2c;
        }

        QLineEdit {
            background-color: #1b1b1b;
            color: #f0f0f0;
            border: 1px solid #2f2f2f;
            padding: 5px;
            border-radius: 4px;
        }

        QListWidget {
            background-color: #1b1b1b;
            color: #f0f0f0;
            border: 1px solid #2f2f2f;
        }

        QGroupBox {
            border: 1px solid #2f2f2f;
            margin-top: 8px;
            padding: 8px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
        }
        """


@dataclass
class ThemeManager:
    light: ThemeFactory
    dark: ThemeFactory
    current: ThemeFactory

    def toggle(self) -> ThemeFactory:
        self.current = self.dark if self.current.name() == "light" else self.light
        return self.current

    def apply(self, app) -> None:
        app.setPalette(self.current.make_palette())
        app.setStyleSheet(self.current.make_stylesheet())


def _make_sun_icon(size: int = 24) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)

    center = size // 2
    radius = size * 0.22

    painter.setBrush(QBrush(QColor("#ffcc33")))
    painter.setPen(QPen(QColor("#ffcc33"), 2))
    painter.drawEllipse(int(center - radius), int(center - radius), int(radius * 2), int(radius * 2))

    painter.setPen(QPen(QColor("#ffcc33"), 2))
    for angle in range(0, 360, 45):
        painter.save()
        painter.translate(center, center)
        painter.rotate(angle)
        painter.drawLine(0, int(-size * 0.42), 0, int(-size * 0.32))
        painter.restore()

    painter.end()
    return QIcon(pm)


def _make_moon_icon(size: int = 24) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)

    center = size // 2
    radius = size * 0.28

    painter.setBrush(QBrush(QColor("#cfd8ff")))
    painter.setPen(QPen(QColor("#cfd8ff"), 2))
    painter.drawEllipse(int(center - radius), int(center - radius), int(radius * 2), int(radius * 2))

    painter.setCompositionMode(QPainter.CompositionMode_Clear)
    painter.setBrush(Qt.transparent)
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(int(center - radius * 0.3), int(center - radius), int(radius * 2), int(radius * 2))

    painter.end()
    return QIcon(pm)
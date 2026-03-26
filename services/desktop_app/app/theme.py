from __future__ import annotations

from PySide6.QtGui import QColor, QPalette


class LightThemeFactory:
    def name(self) -> str:
        return "light"

    def make_palette(self) -> QPalette:
        palette = QPalette()

        palette.setColor(QPalette.Window, QColor(245, 245, 245))
        palette.setColor(QPalette.WindowText, QColor(20, 20, 20))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ToolTipText, QColor(20, 20, 20))
        palette.setColor(QPalette.Text, QColor(20, 20, 20))
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, QColor(20, 20, 20))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Highlight, QColor(76, 163, 224))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        return palette

    def make_stylesheet(self) -> str:
        return """
        QMainWindow, QWidget {
            background-color: #f5f5f5;
            color: #141414;
        }

        QTabWidget::pane {
            border: 1px solid #cfcfcf;
            background: #f5f5f5;
        }

        QTabBar::tab {
            background: #e9e9e9;
            color: #141414;
            padding: 8px 14px;
            border: 1px solid #cfcfcf;
            border-bottom: none;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background: #ffffff;
            color: #141414;
        }

        QGroupBox {
            border: 1px solid #cfcfcf;
            margin-top: 10px;
            padding-top: 10px;
            color: #141414;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }

        QListWidget, QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
            background: #ffffff;
            color: #141414;
            border: 1px solid #bfbfbf;
            selection-background-color: #4ca3e0;
            selection-color: white;
        }

        QPushButton {
            background: #e9e9e9;
            color: #141414;
            border: 1px solid #bfbfbf;
            padding: 6px 10px;
        }

        QPushButton:hover {
            background: #dddddd;
        }

        QPushButton:disabled {
            background: #efefef;
            color: #8a8a8a;
        }

        QLabel {
            color: #141414;
        }
        """


class DarkThemeFactory:
    def name(self) -> str:
        return "dark"

    def make_palette(self) -> QPalette:
        palette = QPalette()

        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, QColor(230, 230, 230))
        palette.setColor(QPalette.Base, QColor(37, 37, 38))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 48))
        palette.setColor(QPalette.ToolTipBase, QColor(45, 45, 48))
        palette.setColor(QPalette.ToolTipText, QColor(230, 230, 230))
        palette.setColor(QPalette.Text, QColor(230, 230, 230))
        palette.setColor(QPalette.Button, QColor(45, 45, 48))
        palette.setColor(QPalette.ButtonText, QColor(230, 230, 230))
        palette.setColor(QPalette.BrightText, QColor(255, 85, 85))
        palette.setColor(QPalette.Highlight, QColor(14, 99, 156))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        return palette

    def make_stylesheet(self) -> str:
        return """
        QMainWindow, QWidget {
            background-color: #1e1e1e;
            color: #e6e6e6;
        }

        QTabWidget::pane {
            border: 1px solid #3c3c3c;
            background: #1e1e1e;
        }

        QTabBar::tab {
            background: #252526;
            color: #e6e6e6;
            padding: 8px 14px;
            border: 1px solid #3c3c3c;
            border-bottom: none;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background: #2d2d30;
            color: #ffffff;
        }

        QGroupBox {
            border: 1px solid #3c3c3c;
            margin-top: 10px;
            padding-top: 10px;
            color: #e6e6e6;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }

        QListWidget, QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
            background: #252526;
            color: #e6e6e6;
            border: 1px solid #3c3c3c;
            selection-background-color: #0e639c;
            selection-color: white;
        }

        QPushButton {
            background: #2d2d30;
            color: #e6e6e6;
            border: 1px solid #3c3c3c;
            padding: 6px 10px;
        }

        QPushButton:hover {
            background: #3a3a3d;
        }

        QPushButton:disabled {
            background: #252526;
            color: #7a7a7a;
        }

        QLabel {
            color: #e6e6e6;
        }
        """


class ThemeManager:
    def __init__(self, app, light, dark):
        self.app = app
        self.light = light
        self.dark = dark
        self.current = self.light

    def toggle(self) -> None:
        self.current = self.dark if self.current.name() == "light" else self.light

    def apply(self, app=None) -> None:
        target_app = app or self.app
        target_app.setPalette(self.current.make_palette())
        target_app.setStyleSheet(self.current.make_stylesheet())
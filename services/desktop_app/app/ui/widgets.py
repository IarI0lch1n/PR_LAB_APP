from PySide6.QtWidgets import QMessageBox, QWidget

def show_info(parent: QWidget, title: str, text: str) -> None:
    QMessageBox.information(parent, title, text)

def show_error(parent: QWidget, title: str, text: str) -> None:
    QMessageBox.critical(parent, title, text)
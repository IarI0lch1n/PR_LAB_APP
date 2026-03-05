from __future__ import annotations
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QPushButton,
    QFileDialog, QLineEdit, QGroupBox
)

from app.api_client import ApiClient
from app.ui.widgets import show_error, show_info


class FilesPage(QWidget):
    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api

        root = QVBoxLayout(self)

        title = QLabel("Files")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        # Controls
        controls = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.upload_btn = QPushButton("Upload...")
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.upload_btn)
        controls.addStretch(1)
        root.addLayout(controls)

        # List
        root.addWidget(QLabel("Files in cloud:"))
        self.list = QListWidget()
        root.addWidget(self.list, 1)

        # Download section
        dl_box = QGroupBox("Download selected")
        dl = QHBoxLayout(dl_box)
        self.save_as = QLineEdit()
        self.save_as.setPlaceholderText("Choose where to save...")
        self.choose_btn = QPushButton("Save as...")
        self.download_btn = QPushButton("Download")
        dl.addWidget(self.save_as, 1)
        dl.addWidget(self.choose_btn)
        dl.addWidget(self.download_btn)
        root.addWidget(dl_box)

        # Events
        self.refresh_btn.clicked.connect(self.load_files)
        self.upload_btn.clicked.connect(self.on_upload)
        self.choose_btn.clicked.connect(self.on_choose_path)
        self.download_btn.clicked.connect(self.on_download)

        self.load_files()

    def load_files(self) -> None:
        self.list.clear()
        try:
            files = self.api.list_files()
        except Exception as e:
            show_error(self, "File API error", str(e))
            return

        if not files:
            self.list.addItem("(no files)")
            return

        for f in files:
            self.list.addItem(f)

    def on_upload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select file to upload")
        if not path:
            return

        try:
            self.api.upload_file(path)
        except Exception as e:
            show_error(self, "Upload failed", str(e))
            return

        show_info(self, "Upload", "Uploaded successfully.")
        self.load_files()

    def on_choose_path(self) -> None:
        filename = self.current_filename()
        if not filename:
            show_info(self, "Download", "Select a file first.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save file as", filename)
        if save_path:
            self.save_as.setText(save_path)

    def on_download(self) -> None:
        filename = self.current_filename()
        if not filename:
            show_info(self, "Download", "Select a file first.")
            return

        save_path = self.save_as.text().strip()
        if not save_path:
            # default to downloads
            downloads = os.path.join(os.path.expanduser("~"), "Downloads")
            save_path = os.path.join(downloads, filename)
            self.save_as.setText(save_path)

        try:
            self.api.download_file(filename, save_path)
        except Exception as e:
            show_error(self, "Download failed", str(e))
            return

        show_info(self, "Download", f"Saved to:\n{save_path}")

    def current_filename(self) -> str | None:
        item = self.list.currentItem()
        if not item:
            return None
        name = item.text().strip()
        if name in ("(no files)", ""):
            return None
        return name
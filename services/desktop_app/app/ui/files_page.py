from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QFileDialog, QGroupBox
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

        controls = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.upload_btn = QPushButton("Upload...")
        self.delete_btn = QPushButton("Delete")

        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.upload_btn)
        controls.addWidget(self.delete_btn)
        controls.addStretch(1)
        root.addLayout(controls)

        root.addWidget(QLabel("Files in cloud:"))

        self.list = QListWidget()
        root.addWidget(self.list, 1)

        dl_box = QGroupBox("Download selected")
        dl = QHBoxLayout(dl_box)

        self.save_path = QLineEdit()
        self.save_path.setPlaceholderText("Choose where to save...")
        self.choose_btn = QPushButton("Save as...")
        self.download_btn = QPushButton("Download")

        dl.addWidget(self.save_path, 1)
        dl.addWidget(self.choose_btn)
        dl.addWidget(self.download_btn)

        root.addWidget(dl_box)

        self.refresh_btn.clicked.connect(self.load_files)
        self.upload_btn.clicked.connect(self.on_upload)
        self.delete_btn.clicked.connect(self.on_delete)
        self.choose_btn.clicked.connect(self.on_choose_save)
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
            it = QListWidgetItem("(no files)")
            it.setFlags(Qt.NoItemFlags)
            self.list.addItem(it)
            return

        for f in files:
            fid = f.get("id")
            name = f.get("filename")
            if fid is None or not name:
                continue
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, int(fid))  
            self.list.addItem(item)

    def current_file(self):
        item = self.list.currentItem()
        if not item:
            return None, None
        fid = item.data(Qt.UserRole)
        name = item.text()
        if fid in (None, "") or name.startswith("("):
            return None, None
        return int(fid), name

    def on_upload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select file to upload")
        if not path:
            return
        try:
            self.api.upload_file(path)
        except Exception as e:
            show_error(self, "Upload failed", str(e))
            return
        self.load_files()

    def on_delete(self) -> None:
        fid, name = self.current_file()
        if fid is None:
            show_info(self, "Delete", "Select a file first.")
            return
        try:
            self.api.delete_file(fid)
        except Exception as e:
            show_error(self, "Delete failed", str(e))
            return
        show_info(self, "Delete", f"Deleted:\n{name}")
        self.load_files()

    def on_choose_save(self) -> None:
        fid, name = self.current_file()
        if fid is None:
            show_info(self, "Download", "Select a file first.")
            return

        default_name = name
        out_path, _ = QFileDialog.getSaveFileName(self, "Save file as", default_name)
        if out_path:
            self.save_path.setText(out_path)

    def on_download(self) -> None:
        fid, name = self.current_file()
        if fid is None:
            show_info(self, "Download", "Select a file first.")
            return

        out_path = self.save_path.text().strip()
        if not out_path:
            downloads = Path.home() / "Downloads"
            out_path = str(downloads / name)
            self.save_path.setText(out_path)

        try:
            self.api.download_file(fid, out_path)
        except Exception as e:
            show_error(self, "Download failed", str(e))
            return

        show_info(self, "Download", f"Saved:\n{out_path}")
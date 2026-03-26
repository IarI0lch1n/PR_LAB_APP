from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QFileDialog, QGroupBox,
    QCheckBox
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
        self.replace_btn = QPushButton("Replace file...")
        self.delete_btn = QPushButton("Delete")
        controls.addWidget(self.refresh_btn)
        controls.addWidget(self.upload_btn)
        controls.addWidget(self.replace_btn)
        controls.addWidget(self.delete_btn)
        controls.addStretch(1)
        root.addLayout(controls)

        root.addWidget(QLabel("Files in cloud:"))

        self.list = QListWidget()
        root.addWidget(self.list, 1)

        access_box = QGroupBox("Access")
        access_layout = QHBoxLayout(access_box)

        self.public_checkbox = QCheckBox("Allow public download")
        self.save_access_btn = QPushButton("Save access")
        access_layout.addWidget(self.public_checkbox)
        access_layout.addWidget(self.save_access_btn)
        access_layout.addStretch(1)

        root.addWidget(access_box)

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
        self.replace_btn.clicked.connect(self.on_replace)
        self.delete_btn.clicked.connect(self.on_delete)
        self.save_access_btn.clicked.connect(self.on_save_access)
        self.choose_btn.clicked.connect(self.on_choose_save)
        self.download_btn.clicked.connect(self.on_download)
        self.list.currentItemChanged.connect(self.on_selection_changed)

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
            self._set_access_controls_enabled(False)
            return

        for f in files:
            fid = f.get("id")
            if fid is None:
                continue

            filename = f.get("filename") or f"file #{fid}"
            owner_name = f.get("owner_name") or "unknown"
            owner_id = f.get("owner_employee_id")
            shared = bool(f.get("shared"))

            raw_public = f.get("is_public_download", 0)
            is_public = str(raw_public).strip().lower() in ("1", "true", "yes")

            tag = "shared" if shared else "mine"
            access = "public" if is_public else "private"
            label = f"{filename} | author: {owner_name} | {tag} | {access}"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, {
                "id": int(fid),
                "filename": filename,
                "owner_name": owner_name,
                "owner_employee_id": owner_id,
                "shared": shared,
                "is_public_download": is_public,
            })
            self.list.addItem(item)

        self.on_selection_changed(self.list.currentItem(), None)

    def current_file(self) -> dict | None:
        item = self.list.currentItem()
        if not item:
            return None
        data = item.data(Qt.UserRole)
        if not isinstance(data, dict):
            return None
        return data

    def on_selection_changed(self, current, previous) -> None:
        f = self.current_file()
        if not f:
            self._set_access_controls_enabled(False)
            return

        self.public_checkbox.setChecked(bool(f.get("is_public_download")))
        editable = not bool(f.get("shared"))
        self._set_access_controls_enabled(editable)

    def _set_access_controls_enabled(self, enabled: bool) -> None:
        self.public_checkbox.setEnabled(enabled)
        self.save_access_btn.setEnabled(enabled)
        self.replace_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)

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

    def on_replace(self) -> None:
        f = self.current_file()
        if not f:
            show_info(self, "Replace", "Select a file first.")
            return

        if f.get("shared"):
            show_info(self, "Replace", "You can replace only your own files.")
            return

        path, _ = QFileDialog.getOpenFileName(self, "Select replacement file")
        if not path:
            return

        try:
            self.api.update_file(int(f["id"]), file_path=path, is_public_download=None)
        except Exception as e:
            show_error(self, "Replace failed", str(e))
            return

        show_info(self, "Replace", "File updated successfully.")
        self.load_files()

    def on_save_access(self) -> None:
        f = self.current_file()
        if not f:
            show_info(self, "Access", "Select a file first.")
            return

        if f.get("shared"):
            show_info(self, "Access", "You can change access only for your own files.")
            return

        val = 1 if self.public_checkbox.isChecked() else 0

        try:
            self.api.update_file(int(f["id"]), file_path=None, is_public_download=val)
        except Exception as e:
            show_error(self, "Access update failed", str(e))
            return

        show_info(self, "Access", "Access updated successfully.")
        self.load_files()

    def on_delete(self) -> None:
        f = self.current_file()
        if not f:
            show_info(self, "Delete", "Select a file first.")
            return

        if f.get("shared"):
            show_info(self, "Delete", "You can delete only your own files.")
            return

        try:
            self.api.delete_file(int(f["id"]))
        except Exception as e:
            show_error(self, "Delete failed", str(e))
            return

        show_info(self, "Delete", f"Deleted:\n{f['filename']}")
        self.load_files()

    def on_choose_save(self) -> None:
        f = self.current_file()
        if not f:
            show_info(self, "Download", "Select a file first.")
            return

        default_name = f["filename"]
        out_path, _ = QFileDialog.getSaveFileName(self, "Save file as", default_name)
        if out_path:
            self.save_path.setText(out_path)

    def on_download(self) -> None:
        f = self.current_file()
        if not f:
            show_info(self, "Download", "Select a file first.")
            return

        out_path = self.save_path.text().strip()
        if not out_path:
            downloads = Path.home() / "Downloads"
            out_path = str(downloads / f["filename"])
            self.save_path.setText(out_path)

        try:
            self.api.download_file(int(f["id"]), out_path)
        except Exception as e:
            show_error(self, "Download failed", str(e))
            return

        show_info(self, "Download", f"Saved:\n{out_path}")
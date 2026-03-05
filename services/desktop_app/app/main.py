import sys
print("PY:", sys.executable)
print("VER:", sys.version)

import sys
from PySide6.QtWidgets import QApplication
from app.config import get_config
from app.api_client import ApiClient
from app.ui.main_window import MainWindow

def main() -> int:
    cfg = get_config()

    api = ApiClient(
        chat_api_url=cfg.chat_api_url,
        file_api_url=cfg.file_api_url
    )

    app = QApplication(sys.argv)
    win = MainWindow(api)
    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
import sys
from PySide6.QtWidgets import QApplication, QDialog

from app.config import get_config
from app.api_client import ApiClient
from app.theme import ThemeManager, LightThemeFactory, DarkThemeFactory
from app.ui.main_window import MainWindow
from app.ui.login_dialog import LoginDialog


def main() -> int:
    cfg = get_config()

    api = ApiClient(
        chat_api_url=cfg.chat_api_url,
        file_api_url=cfg.file_api_url,
        account_api_url=cfg.account_api_url,
        todo_api_url=cfg.todo_api_url,
    )

    app = QApplication(sys.argv)

    theme_manager = ThemeManager(
        app,
        LightThemeFactory(),
        DarkThemeFactory(),
    )

    while True:
        dlg = LoginDialog(api)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            api.close()
            return 0

        win = MainWindow(api, theme_manager, app)
        win.logout_requested.connect(app.quit)
        win.show()

        app.exec()

        if api.employee_key is None:
            continue

        break

    api.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
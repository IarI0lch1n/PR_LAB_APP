import sys
from PySide6.QtWidgets import QApplication, QDialog

from app.config import get_config
from app.api_client import ApiClient
from app.theme import ThemeManager, LightThemeFactory, DarkThemeFactory
from app.ui.login_dialog import LoginDialog
from app.ui.main_window import MainWindow


def main() -> int:
    cfg = get_config()

    api = ApiClient(
        chat_api_url=cfg.chat_api_url,
        file_api_url=cfg.file_api_url,
        account_api_url=cfg.account_api_url,
    )

    app = QApplication(sys.argv)

    theme_manager = ThemeManager(
        light=LightThemeFactory(),
        dark=DarkThemeFactory(),
        current=LightThemeFactory()
    )
    theme_manager.apply(app)

    # Login first
    dlg = LoginDialog(api)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return 0

    win = MainWindow(api, theme_manager, app)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
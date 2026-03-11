import sys
from PySide6.QtWidgets import QApplication

from app.config import get_config
from app.api_client import ApiClient
from app.ui.main_window import MainWindow
from app.theme import ThemeManager, LightThemeFactory, DarkThemeFactory


def main() -> int:
    cfg = get_config()

    api = ApiClient(
        chat_api_url=cfg.chat_api_url,
        file_api_url=cfg.file_api_url
    )

    app = QApplication(sys.argv)

    # Theme (Abstract Factory)
    theme_manager = ThemeManager(
        light=LightThemeFactory(),
        dark=DarkThemeFactory(),
        current=LightThemeFactory()  # default
    )
    theme_manager.apply(app)

    win = MainWindow(api, theme_manager, app)
    win.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
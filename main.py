import argparse
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from game_timer import APP_DISPLAY_NAME, APP_NAME
from game_timer.config import Config
from game_timer.lock_screen import LockScreen
from game_timer.setup_window import SetupWindow
from game_timer.sound import ChimePlayer
from game_timer.timer_overlay import TimerOverlay

UI_FONT_FAMILIES = ["Microsoft JhengHei UI", "Microsoft JhengHei", "PingFang TC", "Noto Sans CJK TC"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_DISPLAY_NAME)
    parser.add_argument(
        "--minutes-as-seconds",
        action="store_true",
        help="開發測試用：把每一「分鐘」當成一秒，方便快速測試提醒和擋板",
    )
    return parser.parse_args()


class Controller:
    def __init__(self, app: QApplication, config: Config, seconds_per_minute: int):
        self.app = app
        self.config = config
        self.seconds_per_minute = seconds_per_minute
        self.chime = ChimePlayer()
        self.overlay: TimerOverlay | None = None
        self.lock: LockScreen | None = None

        self.setup = SetupWindow(config)
        self.setup.start_requested.connect(self.start_session)
        self.setup.quit_requested.connect(app.quit)

    def show_setup(self) -> None:
        self.setup.reset()
        self.setup.show()
        self.setup.raise_()
        self.setup.activateWindow()

    def start_session(self, minutes: int) -> None:
        self.setup.hide()
        total = minutes * self.seconds_per_minute
        five_minutes = 5 * self.seconds_per_minute
        one_minute = 1 * self.seconds_per_minute

        warnings = []
        if total > five_minutes:
            warnings.append((five_minutes, True))
        else:
            warnings.append((total / 2, True))
        if total > 2 * one_minute:
            warnings.append((one_minute, False))

        self.overlay = TimerOverlay(total, warnings, self.chime)
        self.overlay.finished.connect(self.on_time_up)
        self.overlay.start()

    def on_time_up(self) -> None:
        if self.overlay is not None:
            self.overlay.close()
            self.overlay.deleteLater()
            self.overlay = None
        self.chime.play(strong=True)
        self.lock = LockScreen(self.config)
        self.lock.unlocked.connect(self.on_unlocked)
        self.lock.show_all()

    def on_unlocked(self) -> None:
        self.lock = None
        self.show_setup()


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setQuitOnLastWindowClosed(False)

    font = QFont()
    font.setFamilies(UI_FONT_FAMILIES)
    app.setFont(font)

    config = Config()
    controller = Controller(app, config, seconds_per_minute=1 if args.minutes_as_seconds else 60)
    controller.show_setup()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

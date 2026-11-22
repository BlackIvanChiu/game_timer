import argparse
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget

from game_timer import APP_DISPLAY_NAME, APP_NAME
from game_timer.body_break import BodyBreakWindow
from game_timer.config import REST_MINUTES, Config
from game_timer.gifts import Gift, pick_gift
from game_timer.home_window import HomeWindow
from game_timer.lock_screen import LockScreen
from game_timer.setup_window import SetupWindow
from game_timer.sound import ChimePlayer
from game_timer.timer_overlay import TimerOverlay
from game_timer.work_round_end import AfterRestWindow, WorkRoundEndWindow
from game_timer.work_setup import WorkSetupWindow

UI_FONT_FAMILIES = ["Microsoft JhengHei UI", "Microsoft JhengHei", "PingFang TC", "Noto Sans CJK TC"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_DISPLAY_NAME)
    parser.add_argument(
        "--minutes-as-seconds",
        action="store_true",
        help="開發測試用：把每一「分鐘」當成一秒，方便快速測試提醒和擋板",
    )
    return parser.parse_args()


def build_warnings(total: float, seconds_per_minute: int) -> list[tuple[float, bool]]:
    five_minutes = 5 * seconds_per_minute
    one_minute = 1 * seconds_per_minute
    warnings: list[tuple[float, bool]] = []
    if total > five_minutes:
        warnings.append((five_minutes, True))
    else:
        warnings.append((total / 2, True))
    if total > 2 * one_minute:
        warnings.append((one_minute, False))
    return warnings


class AppController:
    def __init__(self, app: QApplication, config: Config, seconds_per_minute: int):
        self.app = app
        self.config = config
        self.seconds_per_minute = seconds_per_minute
        self.chime = ChimePlayer()

        self.overlay: TimerOverlay | None = None
        self.lock: LockScreen | None = None
        self.session_gifts: list[Gift] = []

        self.home = HomeWindow()
        self.game_setup = SetupWindow(config)
        self.work_setup = WorkSetupWindow(config)
        self.round_end = WorkRoundEndWindow()
        self.body_break = BodyBreakWindow()
        self.after_rest = AfterRestWindow()

        self.home.game_requested.connect(self.open_game)
        self.home.work_requested.connect(self.open_work)
        self.home.quit_requested.connect(app.quit)

        self.game_setup.start_requested.connect(self.start_game_session)
        self.game_setup.home_requested.connect(self.show_home)

        self.work_setup.start_requested.connect(self.start_work_session)
        self.work_setup.home_requested.connect(self.show_home)

        self.round_end.extend_requested.connect(self.extend_work)
        self.round_end.rest_requested.connect(self.begin_body_break)
        self.round_end.done_requested.connect(self.finish_work_to_home)

        self.body_break.start_rest_requested.connect(self.start_rest_session)
        self.body_break.skipped.connect(self.start_rest_session)

        self.after_rest.another_round_requested.connect(self.open_work)
        self.after_rest.home_requested.connect(self.show_home)

    def _show(self, window: QWidget) -> None:
        window.show()
        window.raise_()
        window.activateWindow()

    def _hide_all_panels(self) -> None:
        for window in (
            self.home,
            self.game_setup,
            self.work_setup,
            self.round_end,
            self.body_break,
            self.after_rest,
        ):
            window.hide()

    def _close_overlay(self) -> None:
        if self.overlay is not None:
            self.overlay.close()
            self.overlay.deleteLater()
            self.overlay = None

    def show_home(self) -> None:
        self.session_gifts.clear()
        self.chime.stop_repeating()
        self._close_overlay()
        self._hide_all_panels()
        self._show(self.home)

    def open_game(self) -> None:
        self._hide_all_panels()
        self.game_setup.reset()
        self._show(self.game_setup)

    def open_work(self) -> None:
        self.chime.stop_repeating()
        self._close_overlay()
        self._hide_all_panels()
        self.work_setup.reset()
        self._show(self.work_setup)

    def start_game_session(self, minutes: int) -> None:
        self.game_setup.hide()
        total = minutes * self.seconds_per_minute
        self.overlay = TimerOverlay(total, build_warnings(total, self.seconds_per_minute), self.chime, mode="work")
        self.overlay.finished.connect(self.on_game_time_up)
        self.overlay.start()

    def on_game_time_up(self) -> None:
        self._close_overlay()
        self.chime.play(strong=True)
        self.lock = LockScreen(self.config)
        self.lock.unlocked.connect(self.on_game_unlocked)
        self.lock.show_all()

    def on_game_unlocked(self) -> None:
        self.lock = None
        self.open_game()

    def start_work_session(self, minutes: int) -> None:
        self.chime.stop_repeating()
        self._hide_all_panels()
        total = minutes * self.seconds_per_minute
        self.overlay = TimerOverlay(total, build_warnings(total, self.seconds_per_minute), self.chime, mode="work")
        self.overlay.finished.connect(self.on_work_time_up)
        self.overlay.start()

    def on_work_time_up(self) -> None:
        self._close_overlay()
        self.chime.start_repeating(strong=True)
        self.session_gifts.append(pick_gift())
        self.round_end.show_gifts(self.session_gifts)

    def extend_work(self, minutes: int) -> None:
        self.chime.stop_repeating()
        self.start_work_session(minutes)

    def finish_work_to_home(self) -> None:
        self.chime.stop_repeating()
        self.show_home()

    def begin_body_break(self) -> None:
        self.chime.stop_repeating()
        self.body_break.present()

    def start_rest_session(self) -> None:
        self.chime.stop_repeating()
        total = REST_MINUTES * self.seconds_per_minute
        self.overlay = TimerOverlay(total, build_warnings(total, self.seconds_per_minute), self.chime, mode="rest")
        self.overlay.finished.connect(self.on_rest_time_up)
        self.overlay.start()

    def on_rest_time_up(self) -> None:
        self._close_overlay()
        self.chime.start_repeating(strong=False)
        self.after_rest.present()


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
    controller = AppController(app, config, seconds_per_minute=1 if args.minutes_as_seconds else 60)
    controller.show_home()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

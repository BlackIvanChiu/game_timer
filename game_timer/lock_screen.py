from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QGuiApplication, QKeyEvent, QScreen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from game_timer.config import Config
from game_timer.effects import shake

RAISE_INTERVAL_MS = 1000

STYLE_SHEET = """
QWidget#lock {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2C3E50, stop:1 #1B2631);
}
QLabel { color: #ECF0F1; background: transparent; }
QLabel#icon { font-size: 96px; }
QLabel#title { font-size: 56px; font-weight: bold; }
QLabel#subtitle { font-size: 26px; color: #BFC9CA; }
QLabel#error { font-size: 18px; color: #F1948A; }
QLineEdit {
    font-size: 24px; padding: 12px 16px; border: 2px solid #5D6D7E;
    border-radius: 14px; background: #FDFEFE; color: #2C3E50; min-width: 280px;
}
QLineEdit:focus { border-color: #5DADE2; }
QPushButton {
    font-size: 22px; font-weight: bold; color: white; background: #5DADE2;
    border: none; border-radius: 14px; padding: 12px 22px;
}
QPushButton:hover { background: #3498DB; }
"""


class LockWindow(QWidget):
    unlock_attempted = Signal(str)

    def __init__(self, screen: QScreen, with_password: bool):
        super().__init__(
            None,
            Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setObjectName("lock")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(STYLE_SHEET)
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self._allow_close = False
        self.password: QLineEdit | None = None
        self.error: QLabel | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.addStretch()
        for text, name in (("🌙", "icon"), ("時間到了！", "title"), ("今天辛苦了，去休息一下吧", "subtitle")):
            label = QLabel(text)
            label.setObjectName(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

        if with_password:
            layout.addSpacing(36)
            self.password = QLineEdit()
            self.password.setEchoMode(QLineEdit.EchoMode.Password)
            self.password.setPlaceholderText("爸爸媽媽的密碼")
            button = QPushButton("解鎖")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            row = QHBoxLayout()
            row.addStretch()
            row.addWidget(self.password)
            row.addWidget(button)
            row.addStretch()
            layout.addLayout(row)

            self.error = QLabel("")
            self.error.setObjectName("error")
            self.error.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.error)

            button.clicked.connect(self._submit)
            self.password.returnPressed.connect(self._submit)
        layout.addStretch()

    def _submit(self) -> None:
        self.unlock_attempted.emit(self.password.text())

    def show_error(self) -> None:
        self.error.setText("密碼不對喔")
        self.password.selectAll()
        self.password.setFocus()
        shake(self.password)

    def bring_to_front(self) -> None:
        self.raise_()
        if self.password is not None:
            if not self.isActiveWindow():
                self.activateWindow()
            if not self.password.hasFocus():
                self.password.setFocus()

    def release(self) -> None:
        self._allow_close = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._allow_close:
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)


class LockScreen(QObject):
    unlocked = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.windows: list[LockWindow] = []
        self.main_window: LockWindow | None = None
        self._raise_timer = QTimer(self)
        self._raise_timer.setInterval(RAISE_INTERVAL_MS)
        self._raise_timer.timeout.connect(self._bring_to_front)

    def show_all(self) -> None:
        primary = QGuiApplication.primaryScreen()
        screens = QGuiApplication.screens()
        if primary not in screens:
            primary = screens[0]
        for screen in screens:
            window = LockWindow(screen, with_password=screen == primary)
            if screen == primary:
                self.main_window = window
                window.unlock_attempted.connect(self._try_unlock)
            self.windows.append(window)
            window.show()
        self._bring_to_front()
        self._raise_timer.start()

    def _bring_to_front(self) -> None:
        for window in self.windows:
            if window is not self.main_window:
                window.raise_()
        if self.main_window is not None:
            self.main_window.bring_to_front()

    def _try_unlock(self, password: str) -> None:
        if not self.config.check_password(password):
            self.main_window.show_error()
            return
        self._raise_timer.stop()
        for window in self.windows:
            window.release()
            window.deleteLater()
        self.windows.clear()
        self.main_window = None
        self.unlocked.emit()

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from game_timer import APP_DISPLAY_NAME
from game_timer.config import MAX_MINUTES, MIN_MINUTES, Config
from game_timer.effects import shake

PRESET_MINUTES = (15, 30, 45, 60)
MIN_PASSWORD_LENGTH = 4

STYLE_SHEET = """
QWidget#root { background: #FFF8EC; }
QLabel { color: #34495E; }
QLabel#title { font-size: 30px; font-weight: bold; }
QLabel#minutes { font-size: 72px; font-weight: bold; color: #27AE60; }
QLabel#hint { font-size: 16px; color: #7F8C8D; }
QLabel#error { font-size: 16px; color: #E74C3C; }
QLabel#fieldLabel { font-size: 18px; }
QPushButton {
    font-size: 22px; font-weight: bold; color: white;
    background: #5DADE2; border: none; border-radius: 16px;
    padding: 12px 18px; min-height: 36px;
}
QPushButton:hover { background: #3498DB; }
QPushButton:pressed { background: #2E86C1; }
QPushButton#preset:checked { background: #27AE60; }
QPushButton#adjust { background: #F5B041; min-width: 70px; }
QPushButton#adjust:hover { background: #F39C12; }
QPushButton#primary { background: #27AE60; font-size: 26px; }
QPushButton#primary:hover { background: #229954; }
QPushButton#link {
    background: transparent; color: #7F8C8D; font-size: 14px;
    font-weight: normal; text-decoration: underline; padding: 4px; min-height: 0;
}
QPushButton#secondary { background: #BDC3C7; }
QPushButton#secondary:hover { background: #A6ACAF; }
QLineEdit {
    font-size: 22px; padding: 10px 14px; border: 2px solid #D5DBDB;
    border-radius: 12px; background: white; color: #2C3E50;
}
QLineEdit:focus { border-color: #5DADE2; }
"""


def _label(text: str, name: str = "", align=Qt.AlignmentFlag.AlignCenter) -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setAlignment(align)
    label.setWordWrap(True)
    return label


def _password_field(placeholder: str) -> QLineEdit:
    field = QLineEdit()
    field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setPlaceholderText(placeholder)
    return field


def _button(text: str, name: str = "") -> QPushButton:
    button = QPushButton(text)
    if name:
        button.setObjectName(name)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return button


class FirstPasswordPage(QWidget):
    done = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config

        self.password = _password_field("輸入家長密碼")
        self.confirm = _password_field("再輸入一次")
        self.error = _label("", "error")
        save_button = _button("儲存密碼", "primary")

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addWidget(_label("歡迎使用遊戲計時器", "title"))
        layout.addWidget(_label(f"請爸爸媽媽先設定一組家長密碼（至少 {MIN_PASSWORD_LENGTH} 個字）", "hint"))
        layout.addSpacing(12)
        layout.addWidget(self.password)
        layout.addWidget(self.confirm)
        layout.addWidget(self.error)
        layout.addWidget(save_button)
        layout.addStretch()

        save_button.clicked.connect(self._save)
        self.confirm.returnPressed.connect(self._save)
        self.password.returnPressed.connect(self.confirm.setFocus)

    def reset(self) -> None:
        self.password.clear()
        self.confirm.clear()
        self.error.clear()
        self.password.setFocus()

    def _save(self) -> None:
        pw = self.password.text()
        if len(pw) < MIN_PASSWORD_LENGTH:
            self._fail(f"密碼至少要 {MIN_PASSWORD_LENGTH} 個字", self.password)
            return
        if pw != self.confirm.text():
            self._fail("兩次輸入的密碼不一樣", self.confirm)
            return
        self.config.set_password(pw)
        self.done.emit()

    def _fail(self, message: str, field: QLineEdit) -> None:
        self.error.setText(message)
        field.selectAll()
        field.setFocus()
        shake(field)


class ChangePasswordPage(QWidget):
    done = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config

        self.old = _password_field("目前的密碼")
        self.new = _password_field("新密碼")
        self.confirm = _password_field("再輸入一次新密碼")
        self.error = _label("", "error")
        save_button = _button("儲存", "primary")
        back_button = _button("返回", "secondary")

        buttons = QHBoxLayout()
        buttons.addWidget(back_button)
        buttons.addWidget(save_button)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addWidget(_label("更改家長密碼", "title"))
        layout.addSpacing(12)
        layout.addWidget(self.old)
        layout.addWidget(self.new)
        layout.addWidget(self.confirm)
        layout.addWidget(self.error)
        layout.addLayout(buttons)
        layout.addStretch()

        save_button.clicked.connect(self._save)
        back_button.clicked.connect(self.done.emit)
        self.old.returnPressed.connect(self.new.setFocus)
        self.new.returnPressed.connect(self.confirm.setFocus)
        self.confirm.returnPressed.connect(self._save)

    def reset(self) -> None:
        for field in (self.old, self.new, self.confirm):
            field.clear()
        self.error.clear()
        self.old.setFocus()

    def _save(self) -> None:
        if not self.config.check_password(self.old.text()):
            self._fail("目前的密碼不對", self.old)
            return
        pw = self.new.text()
        if len(pw) < MIN_PASSWORD_LENGTH:
            self._fail(f"新密碼至少要 {MIN_PASSWORD_LENGTH} 個字", self.new)
            return
        if pw != self.confirm.text():
            self._fail("兩次輸入的新密碼不一樣", self.confirm)
            return
        self.config.set_password(pw)
        self.done.emit()

    def _fail(self, message: str, field: QLineEdit) -> None:
        self.error.setText(message)
        field.selectAll()
        field.setFocus()
        shake(field)


class StartPage(QWidget):
    start_requested = Signal(int)
    change_password_requested = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.minutes = config.last_minutes

        self.minutes_label = _label("", "minutes")
        self.preset_buttons: dict[int, QPushButton] = {}
        presets = QHBoxLayout()
        presets.setSpacing(12)
        for value in PRESET_MINUTES:
            button = _button(f"{value} 分", "preset")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked, v=value: self._set_minutes(v))
            presets.addWidget(button)
            self.preset_buttons[value] = button

        minus_button = _button("−5", "adjust")
        plus_button = _button("+5", "adjust")
        minus_button.clicked.connect(lambda: self._set_minutes(self.minutes - 5))
        plus_button.clicked.connect(lambda: self._set_minutes(self.minutes + 5))
        adjust = QHBoxLayout()
        adjust.addStretch()
        adjust.addWidget(minus_button)
        adjust.addWidget(self.minutes_label)
        adjust.addWidget(plus_button)
        adjust.addStretch()

        self.password = _password_field("爸爸媽媽輸入密碼")
        self.error = _label("", "error")
        start_button = _button("開始！", "primary")
        start_row = QHBoxLayout()
        start_row.addWidget(self.password, 3)
        start_row.addWidget(start_button, 2)

        change_button = _button("更改密碼", "link")
        quit_button = _button("離開程式", "link")
        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(change_button)
        footer.addWidget(quit_button)
        self.quit_button = quit_button

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addWidget(_label("今天要玩多久呢？", "title"))
        layout.addLayout(adjust)
        layout.addLayout(presets)
        layout.addSpacing(16)
        layout.addWidget(_label("時間到了就要休息喔！請爸爸媽媽輸入密碼後按開始", "hint"))
        layout.addLayout(start_row)
        layout.addWidget(self.error)
        layout.addStretch()
        layout.addLayout(footer)

        start_button.clicked.connect(self._start)
        self.password.returnPressed.connect(self._start)
        change_button.clicked.connect(self.change_password_requested.emit)

        self._set_minutes(self.minutes)

    def reset(self) -> None:
        self.password.clear()
        self.error.clear()
        self._set_minutes(self.config.last_minutes)
        self.password.setFocus()

    def _set_minutes(self, minutes: int) -> None:
        self.minutes = max(MIN_MINUTES, min(MAX_MINUTES, minutes))
        self.minutes_label.setText(f"{self.minutes} 分鐘")
        for value, button in self.preset_buttons.items():
            button.setChecked(value == self.minutes)

    def _start(self) -> None:
        if not self.config.check_password(self.password.text()):
            self.error.setText("密碼不對喔，請爸爸媽媽再試一次")
            self.password.selectAll()
            self.password.setFocus()
            shake(self.password)
            return
        self.config.last_minutes = self.minutes
        self.start_requested.emit(self.minutes)


class SetupWindow(QWidget):
    start_requested = Signal(int)
    quit_requested = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.setStyleSheet(STYLE_SHEET)
        self.resize(640, 520)

        self.first_page = FirstPasswordPage(config)
        self.start_page = StartPage(config)
        self.change_page = ChangePasswordPage(config)

        self.stack = QStackedWidget()
        for page in (self.first_page, self.start_page, self.change_page):
            self.stack.addWidget(page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 20)
        layout.addWidget(self.stack)

        self.first_page.done.connect(self._show_start)
        self.change_page.done.connect(self._show_start)
        self.start_page.change_password_requested.connect(self._show_change)
        self.start_page.start_requested.connect(self.start_requested.emit)
        self.start_page.quit_button.clicked.connect(self.quit_requested.emit)

    def reset(self) -> None:
        if self.config.has_password():
            self._show_start()
        else:
            self.stack.setCurrentWidget(self.first_page)
            self.first_page.reset()

    def _show_start(self) -> None:
        self.stack.setCurrentWidget(self.start_page)
        self.start_page.reset()

    def _show_change(self) -> None:
        self.stack.setCurrentWidget(self.change_page)
        self.change_page.reset()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
        self.quit_requested.emit()

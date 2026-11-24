from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from game_timer import APP_DISPLAY_NAME
from game_timer.config import MAX_MINUTES, MIN_MINUTES, Config

PRESET_MINUTES = (10, 15, 20, 25)

STYLE_SHEET = """
QWidget#root { background: #FFF8EC; }
QLabel { color: #2C3E50; }
QLabel#title { font-size: 30px; font-weight: bold; }
QLabel#minutes { font-size: 72px; font-weight: bold; color: #5DADE2; }
QLabel#hint { font-size: 18px; color: #5D6D7E; }
QPushButton {
    font-size: 22px; font-weight: bold; color: white;
    background: #5DADE2; border: none; border-radius: 16px;
    padding: 12px 18px; min-height: 44px;
}
QPushButton:hover { background: #3498DB; }
QPushButton:pressed { background: #2E86C1; }
QPushButton#preset:checked { background: #1ABC9C; }
QPushButton#adjust { background: #F5B041; min-width: 70px; }
QPushButton#adjust:hover { background: #F39C12; }
QPushButton#primary { background: #1ABC9C; font-size: 26px; }
QPushButton#primary:hover { background: #17A589; }
QPushButton#nav {
    background: #D6EAF8; color: #1A5276; font-size: 18px;
    min-height: 40px; padding: 10px 14px;
}
QPushButton#nav:hover { background: #AED6F1; }
"""


def _label(text: str, name: str = "") -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setWordWrap(True)
    return label


def _button(text: str, name: str = "") -> QPushButton:
    button = QPushButton(text)
    if name:
        button.setObjectName(name)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return button


class WorkSetupWindow(QWidget):
    start_requested = Signal(int)
    home_requested = Signal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.minutes = config.last_work_minutes
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} · 唸書計時")
        self.setStyleSheet(STYLE_SHEET)
        self.resize(640, 480)

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

        start_button = _button("🍅 開始", "primary")
        home_button = _button("🏠 主頁", "nav")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 20)
        layout.setSpacing(16)
        layout.addWidget(_label("🍅 唸多久？", "title"))
        layout.addLayout(adjust)
        layout.addLayout(presets)
        layout.addSpacing(12)
        layout.addWidget(_label("時間到會叮咚提醒", "hint"))
        layout.addWidget(start_button)
        layout.addStretch()
        layout.addWidget(home_button, alignment=Qt.AlignmentFlag.AlignLeft)

        start_button.clicked.connect(self._start)
        home_button.clicked.connect(self.home_requested.emit)
        self._set_minutes(self.minutes)

    def reset(self) -> None:
        self._set_minutes(self.config.last_work_minutes)

    def _set_minutes(self, minutes: int) -> None:
        self.minutes = max(MIN_MINUTES, min(MAX_MINUTES, minutes))
        self.minutes_label.setText(f"{self.minutes} 分鐘")
        for value, button in self.preset_buttons.items():
            button.setChecked(value == self.minutes)

    def _start(self) -> None:
        self.config.last_work_minutes = self.minutes
        self.start_requested.emit(self.minutes)

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
        self.home_requested.emit()

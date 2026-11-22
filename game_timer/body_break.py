from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from game_timer import APP_DISPLAY_NAME
from game_timer.break_prompts import pick_break_prompt

STYLE_SHEET = """
QWidget#root { background: #FFF8EC; }
QLabel { color: #34495E; }
QLabel#title { font-size: 28px; font-weight: bold; }
QLabel#task { font-size: 26px; font-weight: bold; color: #1ABC9C; }
QLabel#hint { font-size: 16px; color: #7F8C8D; }
QPushButton {
    font-size: 20px; font-weight: bold; color: white;
    background: #5DADE2; border: none; border-radius: 16px;
    padding: 14px 18px; min-height: 40px;
}
QPushButton:hover { background: #3498DB; }
QPushButton#primary { background: #1ABC9C; }
QPushButton#primary:hover { background: #17A589; }
QPushButton#secondary { background: #BDC3C7; }
QPushButton#secondary:hover { background: #A6ACAF; }
"""


def _button(text: str, name: str = "") -> QPushButton:
    button = QPushButton(text)
    if name:
        button.setObjectName(name)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return button


class BodyBreakWindow(QWidget):
    start_rest_requested = Signal()
    skipped = Signal()

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} · 身體休息")
        self.setStyleSheet(STYLE_SHEET)
        self.resize(520, 400)
        self.prompt = ""

        title = QLabel("休息前，先做一件小事")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.task_label = QLabel("")
        self.task_label.setObjectName("task")
        self.task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.task_label.setWordWrap(True)

        hint = QLabel("做完再開始休息計時也可以；不想做的話可以跳過")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)

        swap = _button("換一個", "secondary")
        skip = _button("跳過", "secondary")
        start = _button("開始休息", "primary")

        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(swap)
        row.addWidget(skip)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(self.task_label)
        layout.addWidget(hint)
        layout.addSpacing(12)
        layout.addLayout(row)
        layout.addWidget(start)
        layout.addStretch()

        swap.clicked.connect(self._swap)
        skip.clicked.connect(self._skip)
        start.clicked.connect(self._start)
        self._resolved = False

    def present(self) -> None:
        self._resolved = False
        self.prompt = pick_break_prompt()
        self.task_label.setText(self.prompt)
        self.show()
        self.raise_()
        self.activateWindow()

    def _swap(self) -> None:
        self.prompt = pick_break_prompt(exclude=self.prompt)
        self.task_label.setText(self.prompt)

    def _skip(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self.hide()
        self.skipped.emit()

    def _start(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self.hide()
        self.start_rest_requested.emit()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
        if not self._resolved:
            self._resolved = True
            self.skipped.emit()

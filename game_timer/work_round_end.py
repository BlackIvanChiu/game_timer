from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from game_timer import APP_DISPLAY_NAME
from game_timer.gifts import Gift

MAX_VISIBLE_STICKERS = 8

STYLE_SHEET = """
QWidget#root { background: #FFF8EC; }
QLabel { color: #2C3E50; }
QLabel#title { font-size: 28px; font-weight: bold; }
QLabel#giftEmoji { font-size: 72px; }
QLabel#giftLabel { font-size: 24px; font-weight: bold; color: #148F77; }
QLabel#hint { font-size: 18px; color: #5D6D7E; }
QLabel#sticker { font-size: 36px; }
QLabel#stickerMore { font-size: 18px; color: #5D6D7E; font-weight: bold; }
QPushButton {
    font-size: 22px; font-weight: bold; color: white;
    background: #5DADE2; border: none; border-radius: 16px;
    padding: 14px 18px; min-height: 48px;
}
QPushButton:hover { background: #3498DB; }
QPushButton#extend { background: #27AE60; }
QPushButton#extend:hover { background: #229954; }
QPushButton#rest { background: #1ABC9C; }
QPushButton#rest:hover { background: #17A589; }
QPushButton#done { background: #BDC3C7; }
QPushButton#done:hover { background: #A6ACAF; }
"""


def _button(text: str, name: str = "") -> QPushButton:
    button = QPushButton(text)
    if name:
        button.setObjectName(name)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return button


class WorkRoundEndWindow(QWidget):
    extend_requested = Signal(int)
    rest_requested = Signal()
    done_requested = Signal()

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} · 這一輪完成了")
        self.setStyleSheet(STYLE_SHEET)
        self.resize(520, 520)

        self.gift_emoji = QLabel("")
        self.gift_emoji.setObjectName("giftEmoji")
        self.gift_emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.gift_label = QLabel("")
        self.gift_label.setObjectName("giftLabel")
        self.gift_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.collection_row = QHBoxLayout()
        self.collection_row.setSpacing(6)
        self.collection_row.addStretch()
        self.collection_row.addStretch()

        title = QLabel("🎉 完成一輪")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.hint = QLabel("接下來？")
        self.hint.setObjectName("hint")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setWordWrap(True)

        extend5 = _button("➕ 5分", "extend")
        extend10 = _button("➕ 10分", "extend")
        rest = _button("☕ 休息", "rest")
        done = _button("🏁 結束", "done")

        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(extend5)
        row.addWidget(extend10)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(14)
        layout.addStretch()
        layout.addWidget(self.gift_emoji)
        layout.addWidget(self.gift_label)
        layout.addLayout(self.collection_row)
        layout.addSpacing(8)
        layout.addWidget(title)
        layout.addWidget(self.hint)
        layout.addSpacing(12)
        layout.addLayout(row)
        layout.addWidget(rest)
        layout.addWidget(done)
        layout.addStretch()

        extend5.clicked.connect(lambda: self._choose_extend(5))
        extend10.clicked.connect(lambda: self._choose_extend(10))
        rest.clicked.connect(self._choose_rest)
        done.clicked.connect(self._choose_done)
        self._resolved = False

    def show_gifts(self, gifts: list[Gift]) -> None:
        self._resolved = False
        if not gifts:
            return
        latest = gifts[-1]
        self.gift_emoji.setText(latest.emoji)
        self.gift_label.setText(latest.label)
        count = len(gifts)
        self.hint.setText(f"🎁 × {count}" if count > 1 else "接下來？")
        self._fill_collection(gifts)
        self.show()
        self.raise_()
        self.activateWindow()

    def _clear_collection(self) -> None:
        while self.collection_row.count():
            item = self.collection_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _fill_collection(self, gifts: list[Gift]) -> None:
        self._clear_collection()
        self.collection_row.addStretch()
        overflow = max(0, len(gifts) - MAX_VISIBLE_STICKERS)
        visible = gifts[-MAX_VISIBLE_STICKERS:]
        for gift in visible:
            sticker = QLabel(gift.emoji)
            sticker.setObjectName("sticker")
            sticker.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sticker.setToolTip(gift.label)
            self.collection_row.addWidget(sticker)
        if overflow:
            more = QLabel(f"還有 {overflow} 張")
            more.setObjectName("stickerMore")
            more.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.collection_row.addWidget(more)
        self.collection_row.addStretch()

    def _choose_extend(self, minutes: int) -> None:
        if self._resolved:
            return
        self._resolved = True
        self.hide()
        self.extend_requested.emit(minutes)

    def _choose_rest(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self.hide()
        self.rest_requested.emit()

    def _choose_done(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self.hide()
        self.done_requested.emit()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
        if not self._resolved:
            self._resolved = True
            self.done_requested.emit()


class AfterRestWindow(QWidget):
    another_round_requested = Signal()
    home_requested = Signal()

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle(f"{APP_DISPLAY_NAME} · 休息結束")
        self.setStyleSheet(STYLE_SHEET)
        self.resize(480, 360)

        title = QLabel("☕ 休息結束")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("再來一輪？")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        again = _button("🍅 再一輪", "extend")
        home = _button("🏠 主頁", "done")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addSpacing(12)
        layout.addWidget(again)
        layout.addWidget(home)
        layout.addStretch()

        again.clicked.connect(self._choose_again)
        home.clicked.connect(self._choose_home)
        self._resolved = False

    def present(self) -> None:
        self._resolved = False
        self.show()
        self.raise_()
        self.activateWindow()

    def _choose_again(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self.hide()
        self.another_round_requested.emit()

    def _choose_home(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        self.hide()
        self.home_requested.emit()

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
        if not self._resolved:
            self._resolved = True
            self.home_requested.emit()

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from game_timer import APP_DISPLAY_NAME

STYLE_SHEET = """
QWidget#root { background: #FFF8EC; }
QLabel { color: #34495E; }
QLabel#title { font-size: 34px; font-weight: bold; }
QLabel#hint { font-size: 16px; color: #7F8C8D; }
QPushButton {
    font-size: 22px; font-weight: bold; color: white;
    background: #5DADE2; border: none; border-radius: 18px;
    padding: 20px 22px; min-height: 48px; text-align: left;
}
QPushButton:hover { background: #3498DB; }
QPushButton:pressed { background: #2E86C1; }
QPushButton#game { background: #27AE60; }
QPushButton#game:hover { background: #229954; }
QPushButton#work { background: #5DADE2; }
QPushButton#work:hover { background: #3498DB; }
QPushButton#checklist { background: #F5B041; }
QPushButton#checklist:hover { background: #F39C12; }
QPushButton#link {
    background: transparent; color: #7F8C8D; font-size: 14px;
    font-weight: normal; text-decoration: underline; padding: 4px; min-height: 0;
}
"""


class HomeWindow(QWidget):
    game_requested = Signal()
    work_requested = Signal()
    checklist_requested = Signal()
    quit_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.setStyleSheet(STYLE_SHEET)
        self.resize(640, 560)

        title = QLabel(APP_DISPLAY_NAME)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("今天想用哪一個呢？")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        game_button = QPushButton("遊戲計時\n玩之前設好時間，時間到會請爸爸媽媽解鎖")
        game_button.setObjectName("game")
        game_button.setCursor(Qt.CursorShape.PointingHandCursor)
        game_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        work_button = QPushButton("唸書計時\n自己設蕃茄鐘，時間到可以休息或再延長")
        work_button.setObjectName("work")
        work_button.setCursor(Qt.CursorShape.PointingHandCursor)
        work_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        checklist_button = QPushButton("今日清單\n一次只做一件事，完成可以得貼紙")
        checklist_button.setObjectName("checklist")
        checklist_button.setCursor(Qt.CursorShape.PointingHandCursor)
        checklist_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        quit_button = QPushButton("離開程式")
        quit_button.setObjectName("link")
        quit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 24)
        layout.setSpacing(14)
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addSpacing(16)
        layout.addWidget(game_button)
        layout.addWidget(work_button)
        layout.addWidget(checklist_button)
        layout.addStretch()
        layout.addWidget(quit_button, alignment=Qt.AlignmentFlag.AlignRight)

        game_button.clicked.connect(self.game_requested.emit)
        work_button.clicked.connect(self.work_requested.emit)
        checklist_button.clicked.connect(self.checklist_requested.emit)
        quit_button.clicked.connect(self.quit_requested.emit)

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
        self.quit_requested.emit()

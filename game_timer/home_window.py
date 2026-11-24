from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from game_timer import APP_DISPLAY_NAME

STYLE_SHEET = """
QWidget#root { background: #FFF8EC; }
QLabel { color: #2C3E50; }
QLabel#title { font-size: 36px; font-weight: bold; }
QLabel#hint { font-size: 20px; color: #5D6D7E; }
QPushButton {
    font-size: 28px; font-weight: bold; color: white;
    background: #5DADE2; border: none; border-radius: 18px;
    padding: 22px 24px; min-height: 64px; text-align: center;
}
QPushButton:hover { background: #3498DB; }
QPushButton:pressed { background: #2E86C1; }
QPushButton#game { background: #27AE60; }
QPushButton#game:hover { background: #229954; }
QPushButton#work { background: #5DADE2; }
QPushButton#work:hover { background: #3498DB; }
QPushButton#checklist { background: #F5B041; }
QPushButton#checklist:hover { background: #F39C12; }
QPushButton#nav {
    background: #D6EAF8; color: #1A5276; font-size: 18px;
    min-height: 40px; padding: 10px 14px;
}
QPushButton#nav:hover { background: #AED6F1; }
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

        hint = QLabel("選一個開始")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        game_button = QPushButton("🎮  遊戲")
        game_button.setObjectName("game")
        game_button.setCursor(Qt.CursorShape.PointingHandCursor)
        game_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        game_button.setToolTip("玩之前設時間，時間到請家長解鎖")

        work_button = QPushButton("🍅  唸書")
        work_button.setObjectName("work")
        work_button.setCursor(Qt.CursorShape.PointingHandCursor)
        work_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        work_button.setToolTip("蕃茄鐘陪伴唸書")

        checklist_button = QPushButton("✅  清單")
        checklist_button.setObjectName("checklist")
        checklist_button.setCursor(Qt.CursorShape.PointingHandCursor)
        checklist_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        checklist_button.setToolTip("一次只做一件事")

        quit_button = QPushButton("🚪 離開")
        quit_button.setObjectName("nav")
        quit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 24)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addSpacing(20)
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

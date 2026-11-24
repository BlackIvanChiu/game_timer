import math
import time

from PySide6.QtCore import QLineF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from game_timer.effects import shake
from game_timer.sound import ChimePlayer

GREEN = QColor("#2ECC71")
YELLOW = QColor("#F1C40F")
RED = QColor("#E74C3C")
TEAL = QColor("#1ABC9C")
SKY = QColor("#5DADE2")
REST_END = QColor("#48C9B0")

DIAL_SIZE = 160
MARGIN = 10
BUBBLE_HEIGHT = 40
SCREEN_OFFSET = 16
TICK_MS = 200
RAISE_EVERY_TICKS = 10
MESSAGE_MS = 10_000
CORNER_COOLDOWN_SEC = 2.5


def _lerp_color(a: QColor, b: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
    )


def color_for_fraction(fraction: float, mode: str = "work") -> QColor:
    """Work: green→yellow→red. Rest: teal→sky throughout."""
    if mode == "rest":
        return _lerp_color(SKY, TEAL, fraction)
    if fraction >= 0.5:
        return _lerp_color(YELLOW, GREEN, (fraction - 0.5) / 0.5)
    return _lerp_color(RED, YELLOW, fraction / 0.5)


def format_remaining(seconds: float) -> tuple[str, str]:
    whole_seconds = math.ceil(seconds)
    if whole_seconds >= 60:
        return str(math.ceil(whole_seconds / 60)), "分"
    return str(whole_seconds), "秒"


class TimerOverlay(QWidget):
    finished = Signal()

    def __init__(
        self,
        total_seconds: float,
        warnings: list[tuple[float, bool]],
        chime: ChimePlayer,
        mode: str = "work",
    ):
        """`warnings` is a list of (remaining_seconds, strong) thresholds that trigger a reminder."""
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(DIAL_SIZE + 2 * MARGIN, DIAL_SIZE + 2 * MARGIN + BUBBLE_HEIGHT)

        self.mode = mode if mode in ("work", "rest") else "work"
        self.total_seconds = max(1.0, float(total_seconds))
        self.remaining = self.total_seconds
        self.pending_warnings = sorted(warnings, key=lambda w: w[0], reverse=True)
        self.chime = chime
        self.message = "休息中" if self.mode == "rest" else ""
        self._end_time = 0.0
        self._tick_count = 0
        self._corner = "left"
        self._last_flip_time = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)
        self._message_timer = QTimer(self)
        self._message_timer.setSingleShot(True)
        self._message_timer.timeout.connect(self._clear_message)

    def start(self) -> None:
        self._corner = "left"
        self._last_flip_time = 0.0
        self._apply_corner()
        self._end_time = time.monotonic() + self.total_seconds
        self.show()
        self._timer.start()

    def _apply_corner(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        y = screen.top() + SCREEN_OFFSET
        if self._corner == "right":
            x = screen.left() + screen.width() - self.width() - SCREEN_OFFSET
        else:
            x = screen.left() + SCREEN_OFFSET
        self.move(x, y)

    def _maybe_flip_corner(self) -> None:
        """If the cursor is over the dial, toggle top-left / top-right (with cooldown)."""
        now = time.monotonic()
        if now - self._last_flip_time < CORNER_COOLDOWN_SEC:
            return
        if not self.geometry().contains(QCursor.pos()):
            return
        self._corner = "right" if self._corner == "left" else "left"
        self._last_flip_time = now
        self._apply_corner()

    def _tick(self) -> None:
        self.remaining = max(0.0, self._end_time - time.monotonic())

        while self.pending_warnings and self.remaining <= self.pending_warnings[0][0]:
            _, strong = self.pending_warnings.pop(0)
            if self.remaining > 0:
                self._warn(strong)

        self._tick_count += 1
        if self._tick_count % RAISE_EVERY_TICKS == 0:
            self.raise_()

        if self.remaining > 0:
            self._maybe_flip_corner()

        self.update()
        if self.remaining <= 0:
            self._timer.stop()
            self.finished.emit()

    def _warn(self, strong: bool) -> None:
        self.chime.play(strong=strong)
        if self.mode == "rest":
            self.message = "休息快結束囉！" if strong else "還有 1 分鐘"
            shake(self, amplitude=8 if strong else 6, duration_ms=800 if strong else 600, cycles=5)
        elif strong:
            self.message = "快收尾囉！"
            shake(self, amplitude=14, duration_ms=1500, cycles=10)
        else:
            self.message = "最後 1 分鐘！"
            shake(self, amplitude=8, duration_ms=800, cycles=5)
        self._message_timer.start(MESSAGE_MS)

    def _clear_message(self) -> None:
        self.message = "休息中" if self.mode == "rest" else ""
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        fraction = self.remaining / self.total_seconds
        color = color_for_fraction(fraction, self.mode)
        dial = QRectF(MARGIN, MARGIN, DIAL_SIZE, DIAL_SIZE)

        painter.setPen(QPen(QColor(0, 0, 0, 60), 3))
        painter.setBrush(QColor(255, 255, 255, 225))
        painter.drawEllipse(dial)

        if fraction > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            pie = dial.adjusted(6, 6, -6, -6)
            painter.drawPie(pie, 90 * 16, -round(fraction * 360 * 16))

        center = dial.center()
        radius = DIAL_SIZE / 2
        painter.setPen(QPen(QColor(0, 0, 0, 90), 2))
        for i in range(12):
            angle = math.radians(i * 30)
            outer = radius - 2
            inner = radius - (10 if i % 3 == 0 else 6)
            painter.drawLine(
                QLineF(
                    center.x() + inner * math.sin(angle),
                    center.y() - inner * math.cos(angle),
                    center.x() + outer * math.sin(angle),
                    center.y() - outer * math.cos(angle),
                )
            )

        hub_radius = 34
        painter.setPen(QPen(QColor(0, 0, 0, 40), 2))
        painter.setBrush(QColor(255, 255, 255, 245))
        painter.drawEllipse(center, hub_radius, hub_radius)

        number, unit = format_remaining(self.remaining)
        painter.setPen(QColor("#2C3E50"))
        font = QFont(self.font())
        font.setBold(True)
        font.setPixelSize(26)
        painter.setFont(font)
        painter.drawText(
            QRectF(center.x() - hub_radius, center.y() - hub_radius, hub_radius * 2, hub_radius * 1.25),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
            number,
        )
        font.setPixelSize(13)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(
            QRectF(center.x() - hub_radius, center.y() + hub_radius * 0.25, hub_radius * 2, hub_radius * 0.6),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            unit,
        )

        if self.message:
            bubble = QRectF(MARGIN, MARGIN + DIAL_SIZE + 6, DIAL_SIZE, BUBBLE_HEIGHT - 8)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(REST_END if self.mode == "rest" else QColor("#E67E22"))
            painter.drawRoundedRect(bubble, 14, 14)
            painter.setPen(QColor("white"))
            font.setPixelSize(17)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(bubble, Qt.AlignmentFlag.AlignCenter, self.message)

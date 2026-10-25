from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation
from PySide6.QtWidgets import QWidget


def shake(widget: QWidget, amplitude: int = 10, duration_ms: int = 400, cycles: int = 4) -> QPropertyAnimation:
    """Shake a widget horizontally and return it to its original position."""
    previous = getattr(widget, "_shake_animation", None)
    if previous is not None:
        previous.stop()
        widget.move(widget._shake_origin)

    origin = widget.pos()
    animation = QPropertyAnimation(widget, b"pos", widget)
    animation.setDuration(duration_ms)
    animation.setEasingCurve(QEasingCurve.Type.Linear)
    steps = cycles * 2
    for i in range(1, steps):
        decay = 1 - i / steps
        offset = int(amplitude * decay) * (1 if i % 2 else -1)
        animation.setKeyValueAt(i / steps, origin + QPoint(offset, 0))
    animation.setStartValue(origin)
    animation.setEndValue(origin)

    widget._shake_animation = animation
    widget._shake_origin = origin
    animation.start()
    return animation

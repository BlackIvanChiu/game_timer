import math
import struct
import wave
from pathlib import Path

from PySide6.QtCore import QObject, QStandardPaths, QTimer, QUrl
from PySide6.QtWidgets import QApplication

try:
    from PySide6.QtMultimedia import QSoundEffect
except ImportError:
    QSoundEffect = None

SAMPLE_RATE = 44100
CHIME_FILENAME = "chime_v1.wav"
REPEAT_INTERVAL_MS = 18_000


def _tone(frequency: float, duration: float, volume: float) -> list[float]:
    samples = []
    count = int(SAMPLE_RATE * duration)
    attack = int(SAMPLE_RATE * 0.01)
    for i in range(count):
        t = i / SAMPLE_RATE
        envelope = min(1.0, i / attack) * math.exp(-3.5 * t)
        wave_value = math.sin(2 * math.pi * frequency * t) + 0.3 * math.sin(2 * math.pi * frequency * 2 * t)
        samples.append(volume * envelope * wave_value / 1.3)
    return samples


def generate_chime(path: Path) -> None:
    """Write a soft two-note "ding-dong" chime as 16-bit mono PCM."""
    samples = _tone(880.0, 0.6, 0.6) + _tone(659.25, 0.9, 0.6)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples))


class ChimePlayer(QObject):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._effect = None
        self._repeat_timer = QTimer(self)
        self._repeat_timer.setInterval(REPEAT_INTERVAL_MS)
        self._repeat_timer.timeout.connect(lambda: self.play(strong=True))
        if QSoundEffect is None:
            return
        cache_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
        path = cache_dir / CHIME_FILENAME
        try:
            if not path.exists():
                generate_chime(path)
        except OSError:
            return
        self._effect = QSoundEffect()
        self._effect.setSource(QUrl.fromLocalFile(str(path)))

    def play(self, strong: bool = True) -> None:
        if self._effect is None:
            QApplication.beep()
            return
        self._effect.stop()
        self._effect.setVolume(1.0 if strong else 0.5)
        self._effect.setLoopCount(2 if strong else 1)
        self._effect.play()

    def start_repeating(self, strong: bool = True) -> None:
        self.play(strong=strong)
        self._repeat_timer.start()

    def stop_repeating(self) -> None:
        self._repeat_timer.stop()
        if self._effect is not None:
            self._effect.stop()

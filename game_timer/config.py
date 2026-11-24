import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from PySide6.QtCore import QStandardPaths

PBKDF2_ITERATIONS = 200_000
DEFAULT_MINUTES = 30
DEFAULT_WORK_MINUTES = 15
MIN_MINUTES = 5
MAX_MINUTES = 180
REST_MINUTES = 5


def default_config_dir() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    return Path(location)


def _hash_password(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


class Config:
    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or default_config_dir()
        self.path = self.config_dir / "config.json"
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        try:
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self._data = {}

    def save(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        os.replace(tmp_path, self.path)

    def has_password(self) -> bool:
        return "password" in self._data

    def set_password(self, password: str) -> None:
        salt = secrets.token_bytes(16)
        digest = _hash_password(password, salt, PBKDF2_ITERATIONS)
        self._data["password"] = {
            "salt": salt.hex(),
            "hash": digest.hex(),
            "iterations": PBKDF2_ITERATIONS,
        }
        self.save()

    def check_password(self, password: str) -> bool:
        stored = self._data.get("password")
        if not stored:
            return False
        digest = _hash_password(password, bytes.fromhex(stored["salt"]), stored["iterations"])
        return hmac.compare_digest(digest.hex(), stored["hash"])

    @property
    def last_minutes(self) -> int:
        minutes = self._data.get("last_minutes", DEFAULT_MINUTES)
        return max(MIN_MINUTES, min(MAX_MINUTES, int(minutes)))

    @last_minutes.setter
    def last_minutes(self, minutes: int) -> None:
        self._data["last_minutes"] = int(minutes)
        self.save()

    @property
    def last_work_minutes(self) -> int:
        minutes = self._data.get("last_work_minutes", DEFAULT_WORK_MINUTES)
        return max(MIN_MINUTES, min(MAX_MINUTES, int(minutes)))

    @last_work_minutes.setter
    def last_work_minutes(self, minutes: int) -> None:
        self._data["last_work_minutes"] = int(minutes)
        self.save()

    def get_checklist(self) -> dict | None:
        data = self._data.get("checklist")
        return data if isinstance(data, dict) else None

    def set_checklist(self, checklist: dict) -> None:
        self._data["checklist"] = checklist
        self.save()

    def get_checklist_templates(self) -> list[dict]:
        templates = self._data.get("checklist_templates")
        if not isinstance(templates, list):
            return []
        return [t for t in templates if isinstance(t, dict)]

    def set_checklist_templates(self, templates: list[dict]) -> None:
        self._data["checklist_templates"] = templates
        self.save()

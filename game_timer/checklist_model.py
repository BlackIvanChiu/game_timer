from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import date
from typing import Literal

from game_timer.config import Config

Bucket = Literal["now", "later"]

BUILTIN_TEMPLATES: list[dict] = [
    {
        "name": "平日放學",
        "builtin": True,
        "items": [
            {"text": "把書包放定位、拿出聯絡簿", "minutes": 5, "bucket": "now"},
            {"text": "喝水、上廁所", "minutes": None, "bucket": "now"},
            {"text": "寫今天第一科作業", "minutes": 15, "bucket": "now"},
            {"text": "寫下一科或複習", "minutes": 15, "bucket": "later"},
            {"text": "整理書包給明天", "minutes": 10, "bucket": "later"},
        ],
    },
    {
        "name": "週末整理",
        "builtin": True,
        "items": [
            {"text": "整理書桌，只留今天要用的", "minutes": 10, "bucket": "now"},
            {"text": "檢查本週作業有沒有漏交", "minutes": 10, "bucket": "now"},
            {"text": "複習一科 15 分鐘", "minutes": 15, "bucket": "now"},
            {"text": "準備下週要帶的東西", "minutes": 10, "bucket": "later"},
        ],
    },
]


@dataclass
class ChecklistItem:
    id: str
    text: str
    minutes: int | None
    bucket: Bucket
    done: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "minutes": self.minutes,
            "bucket": self.bucket,
            "done": self.done,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ChecklistItem:
        minutes = data.get("minutes")
        if minutes is not None:
            minutes = int(minutes)
        bucket = data.get("bucket", "now")
        if bucket not in ("now", "later"):
            bucket = "now"
        return cls(
            id=str(data.get("id") or secrets.token_hex(8)),
            text=str(data.get("text", "")).strip() or "未命名項目",
            minutes=minutes,
            bucket=bucket,  # type: ignore[arg-type]
            done=bool(data.get("done", False)),
        )


def _new_id() -> str:
    return secrets.token_hex(8)


def _today() -> str:
    return date.today().isoformat()


class ChecklistModel:
    def __init__(self, config: Config):
        self.config = config
        self._ensure_templates()
        self.reload()

    def _ensure_templates(self) -> None:
        templates = self.config.get_checklist_templates()
        if templates:
            return
        self.config.set_checklist_templates(BUILTIN_TEMPLATES)

    def reload(self) -> None:
        raw = self.config.get_checklist()
        today = _today()
        if not raw or raw.get("date") != today:
            items = [ChecklistItem.from_dict({**item, "done": False}) for item in (raw or {}).get("items", [])]
            self.date = today
            self.started = False
            self.items = items
            self._persist()
        else:
            self.date = today
            self.started = bool(raw.get("started", False))
            self.items = [ChecklistItem.from_dict(item) for item in raw.get("items", [])]

    def _persist(self) -> None:
        self.config.set_checklist(
            {
                "date": self.date,
                "started": self.started,
                "items": [item.to_dict() for item in self.items],
            }
        )

    def start_today(self) -> None:
        self.started = True
        self._persist()

    def active_item(self) -> ChecklistItem | None:
        for item in self.items:
            if item.bucket == "now" and not item.done:
                return item
        return None

    def now_items(self, include_done: bool = False) -> list[ChecklistItem]:
        return [i for i in self.items if i.bucket == "now" and (include_done or not i.done)]

    def later_items(self) -> list[ChecklistItem]:
        return [i for i in self.items if i.bucket == "later" and not i.done]

    def done_items(self) -> list[ChecklistItem]:
        return [i for i in self.items if i.done]

    def done_count(self) -> int:
        return len(self.done_items())

    def find(self, item_id: str) -> ChecklistItem | None:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def mark_done(self, item_id: str) -> ChecklistItem | None:
        item = self.find(item_id)
        if item is None or item.done:
            return None
        item.done = True
        self._persist()
        return item

    def skip_active(self) -> None:
        item = self.active_item()
        if item is None:
            return
        item.bucket = "later"
        self._persist()

    def move_bucket(self, item_id: str, bucket: Bucket) -> None:
        item = self.find(item_id)
        if item is None:
            return
        item.bucket = bucket
        self._persist()

    def move_now_order(self, item_id: str, direction: int) -> None:
        """Move an unfinished now-item up (-1) or down (+1) among now unfinished items."""
        indices = [idx for idx, item in enumerate(self.items) if item.bucket == "now" and not item.done]
        now_ids = [self.items[idx].id for idx in indices]
        if item_id not in now_ids:
            return
        seq = now_ids.index(item_id)
        new_seq = seq + direction
        if new_seq < 0 or new_seq >= len(now_ids):
            return
        now_ids[seq], now_ids[new_seq] = now_ids[new_seq], now_ids[seq]
        id_to_item = {item.id: item for item in self.items}
        pointer = 0
        rebuilt: list[ChecklistItem] = []
        for item in self.items:
            if item.bucket == "now" and not item.done:
                rebuilt.append(id_to_item[now_ids[pointer]])
                pointer += 1
            else:
                rebuilt.append(item)
        self.items = rebuilt
        self._persist()

    def add_item(self, text: str, minutes: int | None, bucket: Bucket) -> ChecklistItem:
        item = ChecklistItem(id=_new_id(), text=text.strip() or "未命名項目", minutes=minutes, bucket=bucket)
        self.items.append(item)
        self._persist()
        return item

    def delete_item(self, item_id: str) -> None:
        self.items = [i for i in self.items if i.id != item_id]
        self._persist()

    def templates(self) -> list[dict]:
        return self.config.get_checklist_templates()

    def apply_template(self, name: str) -> bool:
        match = next((t for t in self.templates() if t.get("name") == name), None)
        if match is None:
            return False
        self.items = [
            ChecklistItem(
                id=_new_id(),
                text=str(raw.get("text", "")).strip() or "未命名項目",
                minutes=int(raw["minutes"]) if raw.get("minutes") is not None else None,
                bucket="later" if raw.get("bucket") == "later" else "now",
                done=False,
            )
            for raw in match.get("items", [])
        ]
        self.started = False
        self.date = _today()
        self._persist()
        return True

    def save_as_template(self, name: str) -> None:
        name = name.strip() or "我的模板"
        source = [i for i in self.items if not i.done] or list(self.items)
        payload = {
            "name": name,
            "builtin": False,
            "items": [{"text": i.text, "minutes": i.minutes, "bucket": i.bucket} for i in source],
        }
        templates = [t for t in self.templates() if not (t.get("name") == name and not t.get("builtin"))]
        templates.append(payload)
        self.config.set_checklist_templates(templates)

    def delete_template(self, name: str) -> bool:
        templates = self.templates()
        target = next((t for t in templates if t.get("name") == name), None)
        if target is None or target.get("builtin"):
            return False
        self.config.set_checklist_templates([t for t in templates if t.get("name") != name])
        return True

    def all_now_done(self) -> bool:
        now = [i for i in self.items if i.bucket == "now"]
        return bool(now) and all(i.done for i in now)

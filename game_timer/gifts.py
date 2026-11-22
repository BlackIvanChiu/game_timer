import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Gift:
    emoji: str
    label: str


GIFTS = (
    Gift("⭐", "亮晶晶星星"),
    Gift("🌟", "閃亮小星星"),
    Gift("🌈", "彩虹貼紙"),
    Gift("🦊", "小狐狸徽章"),
    Gift("🐼", "熊貓貼紙"),
    Gift("🐰", "兔子徽章"),
    Gift("🦄", "獨角獸貼紙"),
    Gift("🎈", "氣球徽章"),
    Gift("🍀", "幸運草"),
    Gift("🎯", "專心飛鏢"),
    Gift("📚", "書本徽章"),
    Gift("🧩", "拼圖貼紙"),
)


def pick_gift() -> Gift:
    return random.choice(GIFTS)

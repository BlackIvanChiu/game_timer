import random

BREAK_PROMPTS = (
    "喝一小口水",
    "站起來走一圈",
    "伸個懶腰，轉轉肩膀",
    "開合跳 10 下",
    "伏地挺身 10 下",
    "看看遠方 20 秒，讓眼睛休息",
    "深呼吸三次，慢慢吐氣",
    "蹲下再站起來 8 次",
)


def pick_break_prompt(exclude: str | None = None) -> str:
    choices = [prompt for prompt in BREAK_PROMPTS if prompt != exclude]
    if not choices:
        choices = list(BREAK_PROMPTS)
    return random.choice(choices)

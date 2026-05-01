"""手势识别: 手指数量 → 含义"""

GESTURE_MAP = {
    0: "握拳 ✊",
    1: "食指 ☝",
    2: "胜利 ✌",
    3: "三指",
    4: "四指",
    5: "张开 🖐",
}


def name_of(raised_count: int) -> str:
    return GESTURE_MAP.get(raised_count, f"{raised_count}指")

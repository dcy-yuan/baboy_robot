"""渲染模块 — 自绘 landmarks + HUD"""

import cv2
import numpy as np
from typing import List

from .hand_detector import HandResult
from .gesture_recognizer import name_of

FINGER_COLORS = [
    (180, 100, 255),  # 小指 - 粉
    (0, 180, 255),    # 无名指 - 橙
    (0, 255, 200),    # 中指 - 青
    (0, 200, 100),    # 食指 - 绿
    (255, 200, 0),    # 拇指 - 蓝
]
ALPHA = 0.35


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class UI:
    def __init__(self, config: dict):
        self.win = config.get("window_name", "Finger Recognition")
        self.show_fps = config.get("show_fps", True)
        self.show_handedness = config.get("show_handedness", True)
        style = config.get("landmark_style", {})
        self.tip_r_ratio = style.get("tip_radius_ratio", 0.025)
        self.joint_r_ratio = style.get("joint_radius_ratio", 0.012)
        self.conn_thick = style.get("connection_thickness", 4)
        self.joint_color = tuple(style.get("joint_color", [0, 220, 255]))
        self.conn_color = tuple(style.get("connection_color", [0, 200, 0]))
        self.tip_color = tuple(style.get("tip_color", [0, 0, 255]))
        self.outline_thick = style.get("outline_thickness", 2)
        self.outline_color = tuple(style.get("outline_color", [255, 255, 255]))
        self._prev_t = 0
        self._fps = 0

    # ── Landmark 绘制 ─────────────────────────────────

    def draw_hand(self, frame, hand: HandResult):
        hw = int(hand.hand_size())
        tip_r = max(int(hw * self.tip_r_ratio), 5)
        joint_r = max(int(hw * self.joint_r_ratio), 3)
        overlay = frame.copy()

        self._draw_palm_outline(overlay, hand)
        self._draw_finger_connections(overlay, hand)
        self._draw_joints(overlay, hand, joint_r)
        self._draw_fingertips(overlay, hand, tip_r)

        cv2.addWeighted(overlay, ALPHA, frame, 1 - ALPHA, 0, frame)

    def _draw_palm_outline(self, frame, hand):
        outline = hand.pts[hand.PALM_OUTLINE]
        cv2.polylines(frame, [outline.astype(np.int32)], True,
                       self.outline_color, self.outline_thick, cv2.LINE_AA)

    def _draw_finger_connections(self, frame, hand):
        pts = hand.pts
        for fi, chain in enumerate(hand.FINGER_CHAINS):
            for i in range(len(chain) - 1):
                p1 = tuple(pts[chain[i]])
                p2 = tuple(pts[chain[i + 1]])
                t = i / max(len(chain) - 2, 1)
                cv2.line(frame, p1, p2, _lerp(self.conn_color, FINGER_COLORS[fi], t),
                         self.conn_thick, cv2.LINE_AA)

    def _draw_joints(self, frame, hand, r):
        for idx in range(21):
            if idx in hand.TIPS:
                continue
            x, y = hand.pts[idx]
            cv2.circle(frame, (x, y), r + 1, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, (x, y), r, self.joint_color, -1, cv2.LINE_AA)

    def _draw_fingertips(self, frame, hand, r):
        for fi, tip_idx in enumerate(hand.TIPS):
            x, y = hand.pts[tip_idx]
            color = FINGER_COLORS[fi]
            cv2.circle(frame, (x, y), r + 3, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.circle(frame, (x, y), r, color, -1, cv2.LINE_AA)
            cv2.circle(frame, (int(x - r * 0.25), int(y - r * 0.3)),
                       max(r // 3, 2), (255, 255, 255), -1, cv2.LINE_AA)

    # ── HUD ──────────────────────────────────────────

    def draw_fps(self, frame):
        if self.show_fps:
            cv2.putText(frame, f"FPS:{self._fps:.0f}", (frame.shape[1] - 100, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)

    def draw_hud(self, frame, hands: List[HandResult]):
        h = frame.shape[0]
        if not hands:
            cv2.putText(frame, "未检测到手", (20, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 100, 255), 2, cv2.LINE_AA)
            return

        for i, hand in enumerate(hands):
            n = hand.count_raised()
            side = "右手" if hand.handedness == "Right" else "左手"
            color = (0, 255, 0) if hand.handedness == "Right" else (255, 160, 0)
            text = f"{side}  {n}指  {name_of(n)}"

            y = h - 15 - i * 50
            x1, y1, x2, y2 = 10, y - 36, 270, y + 8
            sub = frame[max(0, y1):y2, x1:x2]
            if sub.size:
                bg = np.full_like(sub, (35, 35, 35))
                cv2.addWeighted(bg, 0.5, sub, 0.5, 0, sub)

            cv2.putText(frame, text, (18, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)

    # ── 窗口 ──────────────────────────────────────────

    def update_fps(self, t):
        if self._prev_t > 0:
            self._fps = 1.0 / max(t - self._prev_t, 0.001)
        self._prev_t = t

    def show(self, frame):
        cv2.imshow(self.win, frame)

    @staticmethod
    def wait_key(delay=1):
        return cv2.waitKey(delay) & 0xFF

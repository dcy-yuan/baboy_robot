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
        self.display_scale = config.get("display_scale", 1.5)
        self._win_ready = False

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
            cv2.putText(frame, f"FPS:{self._fps:.0f}", (frame.shape[1] - 140, 38),
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)

    def draw_hud(self, frame, hands: List[HandResult]):
        h = frame.shape[0]
        if not hands:
            # 大字提示
            text = "未检测到手"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, 1.2, 3)
            cx = (frame.shape[1] - tw) // 2
            cy = h - 40
            cv2.putText(frame, text, (cx, cy),
                        cv2.FONT_HERSHEY_DUPLEX, 1.2, (80, 120, 255), 3, cv2.LINE_AA)
            return

        for i, hand in enumerate(hands):
            n = hand.count_raised()
            side = "右手" if hand.handedness == "Right" else "左手"
            color = (0, 255, 0) if hand.handedness == "Right" else (255, 160, 0)
            gesture = name_of(n)
            text = f"{side}  竖起 {n} 指  {gesture}"

            y = h - 20 - i * 65
            # 加宽背景条
            x1, y1, x2, y2 = 10, y - 42, 340, y + 12
            sub = frame[max(0, y1):y2, x1:x2]
            if sub.size:
                bg = np.full_like(sub, (30, 30, 30))
                cv2.addWeighted(bg, 0.55, sub, 0.45, 0, sub)

            cv2.putText(frame, text, (18, y),
                        cv2.FONT_HERSHEY_DUPLEX, 0.85, color, 2, cv2.LINE_AA)

    # ── 舵机状态 ──────────────────────────────────────

    def draw_servo_status(self, frame, angles, active_fingers, enabled):
        """在左下角绘制舵机角度状态条"""
        if not enabled:
            return

        fh, fw = frame.shape[0], frame.shape[1]
        x0, y0 = 12, fh - 50
        bar_w, bar_h = 60, 8
        gap = 12

        pins = [6, 9, 10, 11]
        finger_names = ["食指", "中指", "无名指", "拇指"]

        for i in range(4):
            x = x0 + i * (bar_w + gap)
            y = y0

            bg = np.zeros((bar_h + 22, bar_w + 6, 3), dtype=np.uint8)
            bg[:] = (40, 40, 40)
            roi = frame[y - 22:y + bar_h + 6, x - 3:x + bar_w + 3]
            if roi.shape == bg.shape:
                cv2.addWeighted(bg, 0.6, roi, 0.4, 0, roi)

            filled = int(bar_w * angles[i] / 180)
            cv2.rectangle(frame, (x, y), (x + bar_w, y + bar_h), (60, 60, 60), 1)
            if filled > 0:
                cv2.rectangle(frame, (x, y), (x + filled, y + bar_h),
                              (0, 220, 150), -1)

            cv2.putText(frame, f"{pins[i]}", (x, y - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1, cv2.LINE_AA)
            cv2.putText(frame, f"{angles[i]}", (x + 2, y + bar_h + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                        (0, 255, 180) if active_fingers[i] else (120, 120, 120),
                        1, cv2.LINE_AA)

    # ── 窗口 ──────────────────────────────────────────

    def update_fps(self, t):
        if self._prev_t > 0:
            self._fps = 1.0 / max(t - self._prev_t, 0.001)
        self._prev_t = t

    def show(self, frame):
        if not self._win_ready:
            # 首次创建可拖拽缩放大窗口
            cv2.namedWindow(self.win, cv2.WINDOW_NORMAL)
            w = int(frame.shape[1] * self.display_scale)
            h = int(frame.shape[0] * self.display_scale)
            cv2.resizeWindow(self.win, w, h)
            self._win_ready = True
        cv2.imshow(self.win, frame)

    @staticmethod
    def wait_key(delay=1):
        return cv2.waitKey(delay) & 0xFF

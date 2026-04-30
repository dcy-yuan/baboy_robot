"""MediaPipe 手部检测 + 手指竖起判定"""

import cv2
import mediapipe as mp
import numpy as np
from typing import List, Tuple


class HandDetector:
    def __init__(self, model_complexity: int = 1, min_detection_confidence: float = 0.7,
                 min_tracking_confidence: float = 0.5, max_hands: int = 2):
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            model_complexity=model_complexity,
            max_num_hands=max_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def detect(self, frame: np.ndarray) -> List["HandResult"]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._hands.process(rgb)
        hands = []
        if results.multi_hand_landmarks:
            for i, lm in enumerate(results.multi_hand_landmarks):
                label = results.multi_handedness[i].classification[0].label
                hands.append(HandResult(lm, label, frame.shape[1], frame.shape[0]))
        return hands

    def close(self):
        self._hands.close()


class HandResult:
    """单只手 21 个关键点 + 手指判定"""

    # MediaPipe 手部关键点索引
    TIPS  = [4,  8,  12, 16, 20]   # 指尖
    PIPs  = [3,  6,  10, 14, 18]   # 近端指间关节
    MCPs  = [2,  5,  9,  13, 17]   # 掌指关节
    WRIST = 0
    NAMES = ["拇指", "食指", "中指", "无名指", "小指"]

    # 连线: 按手指分组 (指尖 → DIP → PIP → MCP)
    FINGER_CHAINS = [
        [4, 3, 2, 1],       # 拇指
        [8, 7, 6, 5],       # 食指
        [12, 11, 10, 9],    # 中指
        [16, 15, 14, 13],   # 无名指
        [20, 19, 18, 17],   # 小指
    ]

    # 手掌轮廓
    PALM_OUTLINE = [0, 1, 2, 5, 9, 13, 17, 0]

    def __init__(self, landmarks, handedness: str, frame_w: int, frame_h: int):
        self.landmarks = landmarks          # NormalizedLandmarkList
        self.handedness = handedness        # "Left" / "Right"
        self.frame_w = frame_w
        self.frame_h = frame_h

    @property
    def pts(self):
        """返回 N×2 像素坐标数组"""
        return np.array([[lm.x * self.frame_w, lm.y * self.frame_h]
                          for lm in self.landmarks.landmark], dtype=np.int32)

    def pixel(self, idx: int) -> Tuple[int, int]:
        lm = self.landmarks.landmark[idx]
        return int(lm.x * self.frame_w), int(lm.y * self.frame_h)

    def hand_size(self) -> float:
        w = self.landmarks.landmark[0]
        m = self.landmarks.landmark[9]
        return np.sqrt((w.x - m.x) ** 2 + (w.y - m.y) ** 2) * max(self.frame_w, self.frame_h)

    def is_finger_raised(self, finger_idx: int, threshold: float = 0.02) -> bool:
        lm = self.landmarks.landmark
        if finger_idx == 0:  # 拇指: 水平外展
            sz = self.hand_size() or 1
            return abs(lm[4].x - lm[3].x) * self.frame_w / sz > threshold * 0.4
        else:
            return (lm[self.PIPs[finger_idx]].y - lm[self.TIPS[finger_idx]].y) > threshold

    def count_raised(self, threshold: float = 0.02) -> int:
        return sum(1 for i in range(5) if self.is_finger_raised(i, threshold))

    def raised_mask(self, threshold: float = 0.02) -> List[bool]:
        return [self.is_finger_raised(i, threshold) for i in range(5)]

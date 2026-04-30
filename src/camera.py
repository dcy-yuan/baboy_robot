"""摄像头捕获 — 支持多后端自动探测"""

import cv2
import os
import glob
import logging
from typing import Tuple, Optional, List

log = logging.getLogger(__name__)


def list_cameras() -> List[str]:
    """列出系统所有视频设备"""
    devices = []
    for pat in ["/dev/video*", "/dev/v4l/by-id/*"]:
        for p in sorted(glob.glob(pat)):
            if os.path.exists(p):
                devices.append(p)
    return devices


def probe_camera(max_id: int = 4) -> Optional[int]:
    """依次尝试 device_id=0~N, 返回第一个可用的"""
    for dev in range(max_id + 1):
        cap = cv2.VideoCapture(dev, cv2.CAP_V4L2)
        if cap.isOpened():
            cap.release()
            return dev
        cap.release()
    # 回退: 不指定后端
    for dev in range(max_id + 1):
        cap = cv2.VideoCapture(dev)
        if cap.isOpened():
            cap.release()
            return dev
        cap.release()
    return None


class Camera:
    def __init__(self, device_id: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        self.device_id = device_id
        self.width = width
        self.height = height
        self.fps = fps
        self._cap: Optional[cv2.VideoCapture] = None
        self._opened = False

    @property
    def is_opened(self) -> bool:
        return self._opened and self._cap is not None and self._cap.isOpened()

    def open(self) -> bool:
        # 诊断信息
        devices = list_cameras()
        if devices:
            log.info(f"发现视频设备: {', '.join(devices)}")
        else:
            log.warning("未发现 /dev/video* 设备, 检查摄像头直通或驱动")

        # 尝试 V4L2 后端
        log.info(f"尝试打开摄像头 V4L2 device={self.device_id}...")
        self._cap = cv2.VideoCapture(self.device_id, cv2.CAP_V4L2)

        if not self._cap.isOpened():
            # 回退: 默认后端
            log.warning(f"V4L2 失败, 尝试默认后端 device={self.device_id}...")
            self._cap = cv2.VideoCapture(self.device_id)

        if not self._cap.isOpened():
            # 自动探测
            log.warning(f"device={self.device_id} 不可用, 自动探测...")
            found = probe_camera()
            if found is not None:
                self.device_id = found
                log.info(f"自动选择 device={found}")
                self._cap = cv2.VideoCapture(found, cv2.CAP_V4L2)
                if not self._cap.isOpened():
                    self._cap = cv2.VideoCapture(found)
            if not self._cap.isOpened():
                log.error("所有摄像头尝试失败")
                return False

        # 设置参数
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        # 预热: 丢弃前几帧 (摄像头刚打开时曝光未稳定)
        for _ in range(5):
            self._cap.read()

        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        log.info(f"摄像头就绪: /dev/video{self.device_id} {actual_w}x{actual_h}")
        self._opened = True
        return True

    def read(self) -> Tuple[bool, Optional["cv2.Mat"]]:
        if not self.is_opened:
            return False, None
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return False, None
        # 丢弃全黑/全白帧
        if frame.size > 0 and frame.mean() < 3:
            return False, None
        return True, frame

    def release(self):
        self._opened = False
        if self._cap is not None:
            self._cap.release()
        cv2.destroyAllWindows()

    def __enter__(self):
        if not self.open():
            raise RuntimeError(f"无法打开摄像头 /dev/video{self.device_id}")
        return self

    def __exit__(self, *args):
        self.release()

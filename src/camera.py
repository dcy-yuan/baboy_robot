"""摄像头捕获 — Linux/Windows 自动适配"""

import cv2
import os
import sys
import glob
import logging
from typing import Tuple, Optional, List

log = logging.getLogger(__name__)

IS_WIN = sys.platform == "win32"


def list_cameras() -> List[str]:
    """列出系统所有视频设备"""
    devices = []
    if IS_WIN:
        for dev in range(4):
            cap = cv2.VideoCapture(dev)
            if cap.isOpened():
                devices.append(f"device={dev}")
                cap.release()
    else:
        for pat in ["/dev/video*", "/dev/v4l/by-id/*"]:
            for p in sorted(glob.glob(pat)):
                if os.path.exists(p):
                    devices.append(p)
    return devices


def probe_camera(max_id: int = 4) -> Optional[int]:
    """依次尝试 device_id=0~N, 返回第一个可用的"""
    # Windows: DirectShow, Linux: V4L2
    backend = cv2.CAP_DSHOW if IS_WIN else cv2.CAP_V4L2

    for dev in range(max_id + 1):
        cap = cv2.VideoCapture(dev, backend)
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
            if IS_WIN:
                log.warning("未发现摄像头, 请确认笔记本摄像头未被其他应用占用")
            else:
                log.warning("未发现 /dev/video* 设备, 检查摄像头直通或驱动")

        # 选择后端: Windows=DirectShow, Linux=V4L2
        if IS_WIN:
            backend = cv2.CAP_DSHOW
            be_name = "DirectShow"
        else:
            backend = cv2.CAP_V4L2
            be_name = "V4L2"

        log.info(f"尝试 {be_name} device={self.device_id}...")
        self._cap = cv2.VideoCapture(self.device_id, backend)

        if not self._cap.isOpened():
            log.warning(f"{be_name} 失败, 尝试默认后端...")
            self._cap = cv2.VideoCapture(self.device_id)

        if not self._cap.isOpened():
            log.warning(f"device={self.device_id} 不可用, 自动探测...")
            found = probe_camera()
            if found is not None:
                self.device_id = found
                log.info(f"自动选择 device={found}")
                backend2 = cv2.CAP_DSHOW if IS_WIN else cv2.CAP_V4L2
                self._cap = cv2.VideoCapture(found, backend2)
                if not self._cap.isOpened():
                    self._cap = cv2.VideoCapture(found)
            if not self._cap.isOpened():
                log.error("所有摄像头尝试失败")
                return False

        # 设置参数
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        # 预热: 丢弃前几帧
        for _ in range(5):
            self._cap.read()

        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        info = f"device={self.device_id}" if IS_WIN else f"/dev/video{self.device_id}"
        log.info(f"摄像头就绪: {info} {actual_w}x{actual_h}")
        self._opened = True
        return True

    def read(self) -> Tuple[bool, Optional["cv2.Mat"]]:
        if not self.is_opened:
            return False, None
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return False, None
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
            dev = self.device_id if IS_WIN else f"/dev/video{self.device_id}"
            raise RuntimeError(f"无法打开摄像头 {dev}")
        return self

    def __exit__(self, *args):
        self.release()

"""主入口 — 手指视觉识别"""

import sys
import time
import logging
import cv2
import yaml
from pathlib import Path

from .camera import Camera
from .hand_detector import HandDetector
from .ui import UI
from .gesture_recognizer import name_of

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("main")


def load_config() -> dict:
    for p in [Path("config.yaml"), Path(__file__).parent.parent / "config.yaml"]:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    raise FileNotFoundError("config.yaml not found")


def main():
    cfg = load_config()
    cam_cfg = cfg.get("camera", {})
    hand_cfg = cfg.get("hand_detection", {})
    disp_cfg = cfg.get("display", {})

    threshold = cfg.get("finger", {}).get("raised_threshold", 0.02)
    mirror = disp_cfg.get("mirror", True)
    ui = UI(disp_cfg)

    # ── 1/3: MediaPipe ──────────────────────────────
    log.info("[1/3] 加载 MediaPipe 手部模型...")
    detector = HandDetector(
        model_complexity=hand_cfg.get("model_complexity", 0),
        min_detection_confidence=hand_cfg.get("min_detection_confidence", 0.7),
        min_tracking_confidence=hand_cfg.get("min_tracking_confidence", 0.5),
        max_hands=hand_cfg.get("max_hands", 2),
    )

    # ── 2/3: 摄像头 ─────────────────────────────────
    log.info("[2/3] 打开摄像头...")
    cam = Camera(
        device_id=cam_cfg.get("device_id", 0),
        width=cam_cfg.get("width", 640),
        height=cam_cfg.get("height", 480),
        fps=cam_cfg.get("fps", 30),
    )
    try:
        cam.open()
    except Exception as e:
        log.error(f"摄像头异常: {e}")
        sys.exit(1)

    if not cam.is_opened:
        log.error("无法打开摄像头, 请检查:")
        log.error("  1. 虚拟机 USB 设置是否直通了摄像头")
        log.error("  2. 终端: ls /dev/video*")
        log.error("  3. 终端: cheese (测试摄像头)")
        log.error("  4. 虚拟机 → 设备 → USB → 勾选摄像头")
        sys.exit(1)

    # ── 3/3: 主循环 ─────────────────────────────────
    log.info("[3/3] 启动主循环...")
    log.info("按键: q/ESC=退出  s=截图  m=切换镜像")
    print("-" * 40)

    screenshot_count = 0
    frame_drop_count = 0

    try:
        while True:
            ok, frame = cam.read()
            if not ok or frame is None:
                frame_drop_count += 1
                if frame_drop_count > 200:
                    log.error("连续丢帧过多, 摄像头断开")
                    break
                time.sleep(0.005)
                continue
            frame_drop_count = 0

            if mirror:
                frame = cv2.flip(frame, 1)

            hands = detector.detect(frame)

            for hand in hands:
                ui.draw_hand(frame, hand)

            ui.draw_fps(frame)
            ui.draw_hud(frame, hands)
            ui.update_fps(time.time())
            ui.show(frame)

            key = ui.wait_key(1)
            if key == ord("q") or key == 27:
                break
            if key == ord("m"):
                mirror = not mirror
                log.info(f"镜像={'开' if mirror else '关'}")
            if key == ord("s"):
                screenshot_count += 1
                name = f"screenshot_{screenshot_count:03d}.png"
                cv2.imwrite(str(Path(__file__).parent.parent / name), frame)
                log.info(f"截图: {name}")

    except KeyboardInterrupt:
        log.info("用户中断")
    finally:
        cam.release()
        detector.close()
        log.info("程序已退出")


if __name__ == "__main__":
    main()

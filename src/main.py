"""主入口 — 手指视觉识别 + 舵机控制"""

import sys
import time
import logging
import cv2
import yaml
from pathlib import Path

from .camera import Camera, IS_WIN
from .hand_detector import HandDetector
from .ui import UI
from .gesture_recognizer import name_of
from .servo_controller import ServoController

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("main")


def load_config() -> dict:
    for p in [Path("config.yaml"), Path(__file__).parent.parent / "config.yaml"]:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    raise FileNotFoundError("config.yaml not found")


def compute_servo_angles(hand, cfg: dict) -> list:
    """根据手部关键点计算 4 个舵机目标角度"""
    sv_cfg = cfg.get("servo", {})
    fingers = sv_cfg.get("fingers", [1, 2, 3, 4])
    min_a = sv_cfg.get("min_angle", 0)
    max_a = sv_cfg.get("max_angle", 180)
    proportional = sv_cfg.get("proportional", False)
    threshold = cfg.get("finger", {}).get("raised_threshold", 0.02)

    angles = [min_a] * 4

    if proportional:
        sz = hand.hand_size() or 1
        for i, fi in enumerate(fingers):
            if i >= 4:
                break
            tip = hand.landmarks.landmark[hand.TIPS[fi]]
            mcp = hand.landmarks.landmark[hand.MCPs[fi]]
            raw = (mcp.y - tip.y) * hand.frame_h / sz
            t = max(0.0, min(1.0, raw * 3.0))
            angles[i] = int(min_a + (max_a - min_a) * t)
    else:
        for i, fi in enumerate(fingers):
            if i >= 4:
                break
            if hand.is_finger_raised(fi, threshold):
                angles[i] = max_a

    return angles


def main():
    cfg = load_config()
    cam_cfg = cfg.get("camera", {})
    hand_cfg = cfg.get("hand_detection", {})
    disp_cfg = cfg.get("display", {})
    sv_cfg = cfg.get("servo", {})

    threshold = cfg.get("finger", {}).get("raised_threshold", 0.02)
    mirror = disp_cfg.get("mirror", True)
    ui = UI(disp_cfg)

    # ── 1/4: MediaPipe ──────────────────────────────
    log.info("[1/4] 加载 MediaPipe 手部模型...")
    detector = HandDetector(
        model_complexity=hand_cfg.get("model_complexity", 0),
        min_detection_confidence=hand_cfg.get("min_detection_confidence", 0.7),
        min_tracking_confidence=hand_cfg.get("min_tracking_confidence", 0.5),
        max_hands=hand_cfg.get("max_hands", 2),
    )

    # ── 2/4: 摄像头 ─────────────────────────────────
    log.info("[2/4] 打开摄像头...")
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
        if IS_WIN:
            log.error("  1. 摄像头是否被其他应用占用 (关闭其他视频软件)")
            log.error("  2. Windows 隐私设置是否允许应用访问摄像头")
            log.error("  3. 笔记本快捷键是否禁用了摄像头 (Fn+F8 等)")
        else:
            log.error("  1. 虚拟机 USB 设置是否直通了摄像头")
            log.error("  2. 终端: ls /dev/video*")
            log.error("  3. 终端: cheese (测试摄像头)")
            log.error("  4. 虚拟机 → 设备 → USB → 勾选摄像头")
        sys.exit(1)

    # ── 3/4: 舵机串口 ───────────────────────────────
    log.info("[3/4] 连接舵机控制器...")
    servo = None
    servo_enabled = sv_cfg.get("enabled", True)
    if servo_enabled:
        servo = ServoController(
            port=sv_cfg.get("port", "/dev/ttyUSB0"),
            baud_rate=sv_cfg.get("baud_rate", 115200),
            num_servos=4,
        )
        servo.connect()
        servo_enabled = servo.is_connected
    else:
        log.info("舵机控制已禁用 (servo.enabled=false)")

    if not servo_enabled and sv_cfg.get("enabled", True):
        log.info("提示: Ubuntu 虚拟机需在 虚拟机→设备→USB 中直通 Arduino")
        log.info("      ls /dev/ttyACM* 或 /dev/ttyUSB* 查看串口")

    # ── 4/4: 主循环 ─────────────────────────────────
    log.info("[4/4] 启动主循环...")
    log.info("按键: q/ESC=退出  s=截图  m=切换镜像  d=切换比例控制")
    print("-" * 40)

    screenshot_count = 0
    frame_drop_count = 0
    servo_angles = [90, 90, 90, 90]
    no_hand_angle = sv_cfg.get("no_hand_angle", 90)
    proportional = sv_cfg.get("proportional", False)

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

            # ── 计算舵机角度 ──
            if hands and servo_enabled:
                sv_cfg["proportional"] = proportional
                servo_angles = compute_servo_angles(hands[0], cfg)
            elif not hands and servo_enabled:
                servo_angles = [no_hand_angle] * 4

            if servo_enabled and servo:
                servo.send_angles(servo_angles)

            # ── 舵机在 HUD 上的手指状态标记 ──
            active_fingers = [a > (sv_cfg.get("min_angle", 0) + sv_cfg.get("max_angle", 180)) // 2
                              for a in servo_angles]

            ui.draw_fps(frame)
            ui.draw_hud(frame, hands)
            ui.draw_servo_status(frame, servo_angles, active_fingers, servo_enabled)
            ui.update_fps(time.time())
            ui.show(frame)

            key = ui.wait_key(1)
            if key == ord("q") or key == 27:
                break
            if key == ord("m"):
                mirror = not mirror
                log.info(f"镜像={'开' if mirror else '关'}")
            if key == ord("d"):
                proportional = not proportional
                log.info(f"比例控制={'开' if proportional else '关'}")
            if key == ord("s"):
                screenshot_count += 1
                name = f"screenshot_{screenshot_count:03d}.png"
                cv2.imwrite(str(Path(__file__).parent.parent / name), frame)
                log.info(f"截图: {name}")

    except KeyboardInterrupt:
        log.info("用户中断")
    finally:
        if servo:
            servo.send_angles([90, 90, 90, 90])
            servo.close()
        cam.release()
        detector.close()
        log.info("程序已退出")


if __name__ == "__main__":
    main()

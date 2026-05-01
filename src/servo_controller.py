"""舵机控制 — 串口通信发送角度命令到 Arduino"""

import logging
from typing import Optional, List

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

log = logging.getLogger("servo")


class ServoController:
    def __init__(self, port: str, baud_rate: int = 115200, num_servos: int = 4):
        self.port = port
        self.baud_rate = baud_rate
        self.num_servos = num_servos
        self._ser: Optional["serial.Serial"] = None
        self._connected = False
        self._last_angles = [90] * num_servos

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ser is not None and self._ser.is_open

    def connect(self) -> bool:
        if not HAS_SERIAL:
            log.warning("pyserial 未安装, 舵机控制禁用. pip install pyserial")
            return False

        try:
            self._ser = serial.Serial(self.port, self.baud_rate, timeout=1)
            self._connected = True
            log.info(f"串口已连接: {self.port} @ {self.baud_rate}")
            return True
        except serial.SerialException as e:
            log.warning(f"无法连接串口 {self.port}: {e}")
            log.warning("舵机控制已禁用, 仅运行手势识别")
            self._connected = False
            return False

    def send_angles(self, angles: List[int]):
        if not self.is_connected:
            return

        a = list(angles[:self.num_servos])
        while len(a) < self.num_servos:
            a.append(0)
        a = [max(0, min(180, int(v))) for v in a]

        if a == self._last_angles:
            return
        self._last_angles = a

        cmd = ",".join(str(v) for v in a) + "\n"
        try:
            self._ser.write(cmd.encode())
            self._ser.flush()
        except serial.SerialException as e:
            log.warning(f"串口写入失败: {e}")
            self._connected = False

    def close(self):
        if self._ser and self._ser.is_open:
            self._ser.close()
        self._connected = False
        log.info("串口已关闭")

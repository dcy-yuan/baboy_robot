# Finger Recognition — 手指视觉识别 (Linux Ubuntu / VSCode / conda)

用笔记本摄像头识别手指数量并控制舵机，在 VSCode 中运行。

---

## 一、环境准备

### 1.1 安装 conda

已安装则跳过。未安装推荐 Miniconda：

```bash
# 下载并安装 Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# 重启终端或 source ~/.bashrc
```

### 1.2 安装 VSCode 扩展

```
VSCode 左侧 Extensions (Ctrl+Shift+X) → 搜索安装:
  - Python (ms-python.python)
  - Python Debugger (ms-python.debugpy)
```

### 1.3 安装系统依赖 (摄像头/OpenGL)

```bash
sudo apt-get update
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0 libegl1-mesa libgomp1
```

---

## 二、创建 conda 虚拟环境 + 安装依赖

### 方式一: 一键脚本 (推荐)

```bash
cd ~/Desktop/cv_gesture
bash setup.sh
```

### 方式二: 手动创建

```bash
cd ~/Desktop/cv_gesture
conda env create -f environment.yml
```

### 验证安装

```bash
conda activate cv_gesture
python -m src.main
```

如果弹出摄像头窗口显示画面，即为成功。

---

## 三、VSCode 配置

### 3.1 选择 Python 解释器

```
VSCode 打开项目:
  File → Open Folder → 选择 cv_gesture 文件夹

选择 conda 环境:
  Ctrl+Shift+P → Python: Select Interpreter
  → 选择 cv_gesture (conda) 或输入路径
     ~/anaconda3/envs/cv_gesture/bin/python
     或 ~/miniconda3/envs/cv_gesture/bin/python
```

选择后 VSCode 底部状态栏应显示 `Python 3.10 ('cv_gesture': conda)`。

### 3.2 运行

```
方式一: 按 F5 调试运行
方式二: 按 Ctrl+F5 直接运行
方式三: VSCode 终端:
  conda activate cv_gesture
  bash run.sh
```

---

## 四、配置说明 (`config.yaml`)

```yaml
camera:
  device_id: 0         # 笔记本摄像头=0, USB外接=1
  width: 640
  height: 480
  fps: 30

hand_detection:
  model_complexity: 1  # 0=快 1=均衡(推荐) 2=高精
  max_hands: 2

display:
  mirror: true         # 镜像翻转 (自拍模式)

servo:
  enabled: true
  port: "/dev/ttyACM0" # Arduino 串口; 终端 ls /dev/ttyACM* 查看
```

### 首次运行

首次运行 MediaPipe 会自动下载手部模型 (约 10MB)，终端会卡在 `[1/4]` 约 10-30 秒，等待即可。

---

## 五、按键操作

| 按键 | 功能 |
|-----|------|
| **Q** 或 **ESC** | 退出程序 |
| **S** | 截图保存到项目根目录 |
| **M** | 切换镜像模式 |
| **D** | 切换比例控制 (二值/比例) |

### 窗口说明

- 画面下方半透明条显示检测结果
- 每只手显示: 左右手 / 竖起几指 / 手势名称
- 左下角舵机状态条: 引脚号 / 角度值 / 填充条
- 右上角显示 FPS
- 手指关节点和连线用渐变彩色绘制

---

## 六、手势对照

| 手指数量 | 手势 | 画面显示 |
|---------|------|---------|
| 0 | 握拳 | 左手/右手 竖起 0 指 握拳 |
| 1 | 食指 | 左手/右手 竖起 1 指 食指 |
| 2 | 胜利 | 左手/右手 竖起 2 指 胜利 |
| 3 | 三指 | 左手/右手 竖起 3 指 三指 |
| 4 | 四指 | 左手/右手 竖起 4 指 四指 |
| 5 | 张开 | 左手/右手 竖起 5 指 张开 |

---

## 七、项目结构

```
cv_gesture/
├── .vscode/
│   ├── settings.json            # VSCode 工作区设置
│   └── launch.json              # F5 调试配置
├── config.yaml                  # 配置文件
├── environment.yml              # conda 环境定义
├── requirements.txt             # pip 依赖 (备选)
├── setup.sh                     # 一键安装脚本
├── run.sh                       # 启动脚本
├── arduino/
│   └── servo_control/
│       └── servo_control.ino    # Arduino 舵机固件
└── src/
    ├── __init__.py
    ├── main.py                  # 主入口
    ├── camera.py                # 摄像头 (V4L2)
    ├── hand_detector.py         # MediaPipe 手部 21 点检测
    ├── gesture_recognizer.py    # 手指数量 → 手势名称
    ├── servo_controller.py      # 串口舵机控制
    └── ui.py                    # 自绘 landmarks + HUD
```

---

## 八、Arduino 舵机 (可选)

如果不使用舵机，在 `config.yaml` 中设置 `servo.enabled: false`。

使用舵机时:

1. 将 `arduino/servo_control/servo_control.ino` 上传到 Arduino
2. USB 连接 Arduino，终端确认串口:
   ```bash
   ls /dev/ttyACM*    # Arduino Uno/Mega
   ls /dev/ttyUSB*    # Arduino Nano 等
   ```
3. 在 `config.yaml` 中填入正确的 `servo.port`
4. 如遇权限问题:
   ```bash
   sudo usermod -a -G dialout $USER
   # 注销重新登录后生效
   ```

---

## 九、常见问题

| 现象 | 原因 | 解决 |
|-----|------|------|
| 无法打开摄像头 | 设备节点不存在 | `ls /dev/video*` 检查，笔记本快捷键 Fn+F8/F10 |
| `No module named 'xxx'` | conda 环境未激活 | VSCode 检查底部状态栏解释器路径 |
| 识别不准/延迟 | 光照不足或背景杂乱 | 面向光源，使用纯色背景 |
| 首次运行很久 | 下载 MediaPipe 模型 | 等待 10-30 秒 |
| 舵机不响应 | 串口权限/端口不对 | `ls /dev/tty*` 查看, 执行 `sudo usermod -a -G dialout $USER` |
| VSCode 终端未激活 conda | conda 未初始化 | 终端输入 `conda init bash` 后重启 VSCode |
| conda 命令找不到 | PATH 未设置 | `source ~/anaconda3/etc/profile.d/conda.sh` |

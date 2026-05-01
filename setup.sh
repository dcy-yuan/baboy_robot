#!/usr/bin/env bash
set -e

echo "============================================"
echo "  Finger Recognition — Conda 环境安装"
echo "============================================"
echo ""

# ── 检查 conda ──────────────────────────────────
if ! command -v conda &>/dev/null; then
    echo "[ERROR] 未找到 conda，请先安装 Anaconda 或 Miniconda"
    echo "  Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi
echo "[INFO] conda: $(conda --version)"

# ── 系统依赖 ────────────────────────────────────
if [ -f /etc/lsb-release ] || [ -f /etc/debian_version ]; then
    echo "[INFO] 安装系统依赖 (摄像头/OpenGL)..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq libgl1-mesa-glx libglib2.0-0 libegl1-mesa libgomp1
elif [ -f /etc/redhat-release ]; then
    echo "[INFO] 安装系统依赖 (摄像头/OpenGL)..."
    sudo dnf install -y mesa-libGL glib2 libglvnd-glx
fi

# ── 创建 conda 环境 ──────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/environment.yml"
ENV_NAME="cv_gesture"

if conda env list | grep -q "^${ENV_NAME} "; then
    echo "[INFO] conda 环境 '${ENV_NAME}' 已存在，更新依赖..."
    conda env update -f "$ENV_FILE" -n "$ENV_NAME"
else
    echo "[INFO] 创建 conda 环境 '${ENV_NAME}'..."
    conda env create -f "$ENV_FILE"
fi

echo ""
echo "============================================"
echo "  安装完成!"
echo "============================================"
echo ""
echo "VSCode 配置步骤:"
echo "  1. Ctrl+Shift+P → Python: Select Interpreter"
echo "  2. 选择 cv_gesture (conda)"
echo "  3. Ctrl+F5 运行, F5 调试"
echo ""
echo "终端运行:"
echo "  conda activate cv_gesture"
echo "  bash run.sh"
echo ""

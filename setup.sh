#!/usr/bin/env bash
set -e
echo "=== Finger Recognition 安装 ==="

PYTHON=python3
if ! command -v $PYTHON &>/dev/null; then
    echo "[ERROR] 未找到 python3"
    exit 1
fi
echo "[INFO] $($PYTHON --version)"

# 系统依赖
if [ -f /etc/lsb-release ] || [ -f /etc/debian_version ]; then
    echo "[INFO] 安装系统库..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3-pip libgl1-mesa-glx libglib2.0-0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "=== 安装完成, 运行: bash run.sh ==="

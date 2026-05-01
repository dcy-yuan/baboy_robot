#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── 激活 conda 环境 ──────────────────────────────
ENV_NAME="cv_gesture"

# 尝试多种方式定位 conda
if [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
    source "/opt/conda/etc/profile.d/conda.sh"
elif command -v conda &>/dev/null; then
    eval "$(conda shell.bash hook)"
fi

conda activate "$ENV_NAME" 2>/dev/null || {
    echo "[WARN] 无法激活 conda 环境 '$ENV_NAME'，尝试直接运行..."
}

python -m src.main "$@"

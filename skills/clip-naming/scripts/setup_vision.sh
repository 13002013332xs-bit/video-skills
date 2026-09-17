#!/bin/bash
# 一次性安装：本机视觉模型环境 + 模型权重 + 两个命令（在你自己的终端里跑）
set -euo pipefail

ENV_DIR="$HOME/.local/opt/clip-naming"
PIP_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple"
export HF_ENDPOINT="https://hf-mirror.com"      # 国内加速；不需要可删掉这行
export HF_HUB_DISABLE_XET=1                     # hf-mirror 不支持 xet，必须关
MODEL="mlx-community/Qwen2.5-VL-3B-Instruct-4bit"

python3 -m venv "$ENV_DIR/venv"
"$ENV_DIR/venv/bin/pip" install -q -U pip -i "$PIP_MIRROR"
"$ENV_DIR/venv/bin/pip" install -i "$PIP_MIRROR" mlx-vlm pillow

echo "下载视觉模型（约 2GB，支持断点续传）…"
"$ENV_DIR/venv/bin/python" - <<PY
from huggingface_hub import snapshot_download
print(snapshot_download("$MODEL"))
PY

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/clip-caption" <<EOF
#!/bin/bash
exec "$ENV_DIR/venv/bin/python" "$SKILL_DIR/scripts/caption_clip.py" "\$@"
EOF
cat > "$HOME/.local/bin/clip-name" <<EOF
#!/bin/bash
exec "$ENV_DIR/venv/bin/python" "$SKILL_DIR/scripts/name_and_file.py" "\$@"
EOF
chmod +x "$HOME/.local/bin/clip-caption" "$HOME/.local/bin/clip-name"
echo "完成：clip-caption / clip-name 已可用"

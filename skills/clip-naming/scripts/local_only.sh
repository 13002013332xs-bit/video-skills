#!/bin/bash
# 只跑本机模型（Qwen2.5-VL 3B），结果带 [本机] 后缀，方便与云端对比
# 用法: local_only.sh [产品类型，默认 磁吸灯]
set -uo pipefail

PRODUCT="${1:-磁吸灯}"
ROOT="$HOME/Desktop/短视频素材"
VENV="$HOME/.local/opt/clip-naming/venv/bin/python"
SKILL="$HOME/.codex/skills/clip-naming/scripts"

found=0
for inbox in "$ROOT"/*/未命名上传; do
  [ -d "$inbox" ] || continue
  count=$(find "$inbox" -maxdepth 1 -type f \( -name "*.MOV" -o -name "*.mov" -o -name "*.MP4" -o -name "*.mp4" \) | wc -l | tr -d ' ')
  [ "$count" -eq 0 ] && continue
  found=1
  parent="$(dirname "$inbox")"
  echo "=== 本機模型處理 $inbox （$count 條）==="
  CLIP_PRODUCT="$PRODUCT" "$VENV" "$SKILL/caption_clip.py" "$inbox" \
      --backend local --out "$parent/_描述_本机" \
    && "$VENV" "$SKILL/name_and_file.py" "$parent/_描述_本机" \
         --product "$PRODUCT" --suffix "[本机]" --archive "$parent/_原片存档" --dest "$ROOT" --date "$(basename "$parent")"
done
[ "$found" -eq 0 ] && echo "沒找到收件夾"
echo
echo "完成。按回車關閉窗口。"

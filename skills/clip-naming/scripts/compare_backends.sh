#!/bin/bash
# 同一批素材，两种引擎各跑一遍：云端（百炼）vs 本机（Qwen2.5-VL）
# 结果文件名分别带 [云端] / [本机] 后缀，方便对比。
# 用法: compare_backends.sh [产品类型，默认 磁吸灯]
set -uo pipefail

PRODUCT="${1:-磁吸灯}"
ROOT="$HOME/Desktop/短视频素材"
INBOX="未命名上传"
VENV="$HOME/.local/opt/clip-naming/venv/bin/python"
SKILL="$HOME/.codex/skills/clip-naming/scripts"

found=0
for inbox in "$ROOT"/*/"$INBOX"; do
  [ -d "$inbox" ] || continue
  count=$(find "$inbox" -maxdepth 1 -type f \( -name "*.MOV" -o -name "*.mov" -o -name "*.MP4" -o -name "*.mp4" \) | wc -l | tr -d ' ')
  [ "$count" -eq 0 ] && continue
  found=1
  parent="$(dirname "$inbox")"
  echo "==================================================="
  echo "素材: $inbox （$count 条）"

  echo "--- ① 云端（百炼 qwen3-vl-plus）---"
  CLIP_VLM_API_MODEL="${CLIP_VLM_API_MODEL:-qwen3-vl-plus}" CLIP_PRODUCT="$PRODUCT" \
    "$VENV" "$SKILL/caption_clip.py" "$inbox" --backend dashscope --out "$parent/_描述_云端" \
    && "$VENV" "$SKILL/name_and_file.py" "$parent/_描述_云端" --product "$PRODUCT" --suffix "[云端]" --archive "$parent/_原片存档"

  echo "--- ② 本机（Qwen2.5-VL 3B）---"
  CLIP_PRODUCT="$PRODUCT" \
    "$VENV" "$SKILL/caption_clip.py" "$inbox" --backend local --out "$parent/_描述_本机" \
    && "$VENV" "$SKILL/name_and_file.py" "$parent/_描述_本机" --product "$PRODUCT" --suffix "[本机]" --archive "$parent/_原片存档"

  echo
  echo "对比结果看 $parent/_命名确认清单.md（云端最后一次覆盖，逐条对比看文件名后缀）"
done

if [ "$found" -eq 0 ]; then
  echo "没找到收件夹：$ROOT/<日期>/$INBOX"
fi
echo
echo "完成。按回车关闭窗口。"

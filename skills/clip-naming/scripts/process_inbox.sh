#!/bin/bash
# 处理「未命名上传」里的新素材：看片 → 起名 → 分类 → 原片移出收件夹 → 出确认清单
# 默认走云端（百炼）；用法: process_inbox.sh [产品类型，默认 磁吸灯]
set -uo pipefail

PRODUCT="${1:-磁吸灯}"
INBOX_NAME="未命名上传"
ROOT="$HOME/Desktop/短视频素材"
VENV="$HOME/.local/opt/clip-naming/venv/bin/python"
SKILL="$HOME/.codex/skills/clip-naming/scripts"
MODEL="${CLIP_VLM_API_MODEL:-qwen3-vl-plus}"

found=0
for inbox in "$ROOT"/*/"$INBOX_NAME"; do
  [ -d "$inbox" ] || continue
  count=$(find "$inbox" -maxdepth 1 -type f \( -iname "*.mov" -o -iname "*.mp4" \) | wc -l | tr -d ' ')
  [ "$count" -eq 0 ] && continue
  found=1
  parent="$(dirname "$inbox")"
  echo "=== $inbox （$count 个片段）==="

  CLIP_VLM_API_MODEL="$MODEL" CLIP_PRODUCT="$PRODUCT" \
    "$VENV" "$SKILL/caption_clip.py" "$inbox" --backend dashscope --out "$parent/_描述_云端"
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "❌ 看片失败（退出码 $rc），先不分类。"
    continue
  fi
  "$VENV" "$SKILL/name_and_file.py" "$parent/_描述_云端" \
     --product "$PRODUCT" --suffix "[云端]" \
     --dest "$ROOT" --date "$(basename "$parent")" \
     --archive "$parent/_原片存档"
done

[ "$found" -eq 0 ] && echo "没找到有待命名的素材（$ROOT/<日期>/$INBOX_NAME）"
echo
echo "处理完成：分类结果在 <日期>/开头|中间|结尾，原片已移到 <日期>/_原片存档，确认清单是 _命名确认清单.md"
echo "按回车关闭窗口。"

#!/bin/bash
# 只跑本机模型，且只跑收件夹里的前 3 条（按文件名顺序），结果带 [本机] 后缀
set -uo pipefail

PRODUCT="${1:-磁吸灯}"
ROOT="$HOME/Desktop/短视频素材"
VENV="$HOME/.local/opt/clip-naming/venv/bin/python"
SKILL="$HOME/.codex/skills/clip-naming/scripts"

for inbox in "$ROOT"/*/未命名上传; do
  [ -d "$inbox" ] || continue
  parent="$(dirname "$inbox")"
  LOG="$parent/_本机运行日志.txt"
  echo "=== 本機模型（只跑前 3 條）: $inbox ===" | tee "$LOG"
  echo "開始時間: $(date '+%H:%M:%S')" | tee -a "$LOG"
  mkdir -p "$parent/_描述_本机"
  CLIP_PRODUCT="$PRODUCT" "$VENV" "$SKILL/caption_clip.py" "$inbox" \
      --backend local --limit 3 --out "$parent/_描述_本机" 2>&1 | tee -a "$LOG"
  caption_rc=${PIPESTATUS[0]}
  if [ "$caption_rc" -ne 0 ]; then
    echo | tee -a "$LOG"
    echo "❌ 本機模型執行失敗（退出碼 $caption_rc）。上面就是錯誤訊息。" | tee -a "$LOG"
    echo "   把這行訊息發我，我接著修。" | tee -a "$LOG"
    continue
  fi
  "$VENV" "$SKILL/name_and_file.py" "$parent/_描述_本机" \
      --product "$PRODUCT" --suffix "[本机]" --archive "$parent/_原片存档" --dest "$ROOT" --date "$(basename "$parent")" 2>&1 | tee -a "$LOG"
  echo "結束時間: $(date '+%H:%M:%S')" | tee -a "$LOG"
done
echo
echo "全部結束。日誌在 <素材夾>/_本机运行日志.txt"
echo "按回車關閉窗口。"

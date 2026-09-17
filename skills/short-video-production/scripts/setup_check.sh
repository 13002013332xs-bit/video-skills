#!/bin/bash
# 环境自检：跑这个脚本，它会告诉你还缺什么、怎么补。
set -uo pipefail

OK=0; BAD=0
say_ok()   { echo "  ✅ $1"; OK=$((OK+1)); }
say_bad()  { echo "  ❌ $1"; echo "     → $2"; BAD=$((BAD+1)); }
say_warn() { echo "  ⚠️  $1"; echo "     → $2"; }

echo "==============================================="
echo " 短视频技能 · 环境自检"
echo "==============================================="

# 1) 基础工具
for cmd in ffmpeg ffprobe; do
  if command -v "$cmd" >/dev/null 2>&1 || [ -x "$HOME/.local/bin/$cmd" ]; then
    say_ok "$cmd"
  else
    say_bad "$cmd 未安装" "macOS: 下载静态版放到 ~/.local/bin，或 brew install ffmpeg"
  fi
done
if command -v yt-dlp >/dev/null 2>&1 || [ -x "$HOME/.local/bin/yt-dlp" ]; then
  say_ok "yt-dlp"
else
  say_bad "yt-dlp 未安装" "pipx install yt-dlp  或  pip install yt-dlp"
fi
if command -v python3 >/dev/null 2>&1; then say_ok "python3"; else say_bad "python3 未安装" "装 Python 3.10+"; fi

# 2) 眼睛（视觉模型）
KEYFILE="$HOME/.local/opt/clip-naming/dashscope.key"
if [ -n "${DASHSCOPE_API_KEY:-}" ]; then
  say_ok "百炼 API key（环境变量 DASHSCOPE_API_KEY）"
elif [ -f "$KEYFILE" ]; then
  say_ok "百炼 API key（$KEYFILE）"
else
  say_bad "没有视觉模型 key —— 没有它就读不懂画面（等于没有眼睛）" \
          "去 https://bailian.console.aliyun.com/ 开通百炼 → 创建 API-KEY → 存到 $KEYFILE 并 chmod 600"
fi

# 3) 剪映草稿适配层
ADAPTER="$HOME/Developer/capcut-mate/local/plan_to_draft.py"
if [ -f "$ADAPTER" ]; then say_ok "capcut-mate 适配层"; else
  say_bad "capcut-mate 适配层不在默认位置" "见 skills/short-video-production/references/jianying-draft.md，或把 \$GEN 改到你的路径"
fi

# 4) 剪映草稿目录
DRAFTS="$HOME/Movies/JianyingPro/User Data/Projects/com.lveditor.draft"
if [ -d "$DRAFTS" ]; then say_ok "剪映草稿目录"; else
  say_warn "剪映草稿目录不存在（未装剪映或路径不同）" "装剪映专业版；或改脚本里的 DRAFTS/--drafts-dir"
fi

# 5) 素材来源
POOL="$HOME/Desktop/短视频素材"
if [ -d "$POOL" ]; then say_ok "本地素材目录 $POOL"; else
  say_warn "本地素材目录不存在" "建一个，或改脚本里的 ROOT/POOL 到你自己的素材位置"
fi
for p in "$HOME/Documents/Codex"; do :; done
echo "  ℹ️  飞书素材库另有要求：需要你自己的自建应用 + OAuth 授权（见 references/material-sourcing.md）"

# 6) 路径提醒
echo
echo "  ℹ️  脚本里的绝对路径（项目目录/素材池/草稿目录）如果和你机器不一致，要改："
echo "     grep -rn \"/Users/\" <技能目录>/scripts | head"

echo
echo "==============================================="
echo " 通过 $OK 项，待处理 $BAD 项"
[ "$BAD" -eq 0 ] && echo " 🎉 可以开始用了：把素材丢进素材目录，或者说\"照着这个视频剪\"" \
                || echo " 先把上面的 ❌ 补齐，再跑一次本脚本"
echo "==============================================="

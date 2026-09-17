#!/bin/bash
# 双击运行：装好本机视觉模型 + 两个命令（clip-caption / clip-name）
cd "$HOME" || exit 1
bash "$HOME/.codex/skills/clip-naming/scripts/setup_vision.sh"
echo
echo "----------------------------------------"
echo "如果上面出现『完成：clip-caption / clip-name 已可用』就是装好了。"
echo "按回车关闭这个窗口。"
read -r _

#!/bin/bash
# 双击运行：把"未命名上传"里的新素材看片、起名、分类
cd "$HOME" || exit 1
read -r -p "产品类型（磁吸灯/多功能笔/肌理画，直接回车=磁吸灯）: " product
bash "$HOME/.codex/skills/clip-naming/scripts/process_inbox.sh" "${product:-磁吸灯}"
echo
echo "按回车关闭这个窗口。"
read -r _

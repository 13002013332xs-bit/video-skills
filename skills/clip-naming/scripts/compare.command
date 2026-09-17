#!/bin/bash
# 双击运行：同一批素材，云端与本机各跑一遍，文件名带 [云端]/[本机]
cd "$HOME" || exit 1
read -r -p "产品类型（磁吸灯/多功能笔/肌理画，直接回车=磁吸灯）: " product
bash "$HOME/.codex/skills/clip-naming/scripts/compare_backends.sh" "${product:-磁吸灯}"
read -r _

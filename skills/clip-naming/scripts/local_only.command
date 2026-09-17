#!/bin/bash
# 双击运行：只跑本机模型，结果带 [本机] 后缀
cd "$HOME" || exit 1
read -r -p "产品类型（磁吸灯/多功能笔/肌理画，直接回车=磁吸灯）: " product
bash "$HOME/.codex/skills/clip-naming/scripts/local_only.sh" "${product:-磁吸灯}"
read -r _

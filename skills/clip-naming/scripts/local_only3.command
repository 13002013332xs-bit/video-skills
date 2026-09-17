#!/bin/bash
cd "$HOME" || exit 1
read -r -p "产品类型（直接回车=磁吸灯）: " product
bash "$HOME/.codex/skills/clip-naming/scripts/local_only3.sh" "${product:-磁吸灯}"
read -r _

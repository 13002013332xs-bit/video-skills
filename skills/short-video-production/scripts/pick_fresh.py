#!/usr/bin/env python3
"""按镜头需求从素材池选片，**优先挑从没用过的**，并给出分配表。

用法:
    python pick_fresh.py --need "鉤子:下水道|掉.*钥匙" --need "吸出:吸出|吸深处" ...
                        [--pool DIR] [--count N] [--out plan.json]

规则（重要）：
  1. 同一支视频内不重复
  2. 优先从没用过的素材里选（读 ledger）
  3. 没用过的用完了 → 才允许复用，且优先挑"上次用得最久"的
  4. 输出时明确标注每段是【新】还是【复用】
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from pipeline_config import get as cfg_get
except Exception:
    def cfg_get(_k):
        return ""
import ledger as ledger_mod


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--need", action="append", required=True,
                    help='镜头规则，可多次。格式：\n'
                         '  "镜头名:关键词正则"\n'
                         '  "镜头名:c=类别关键词:关键词正则"   ← 先锁定类别再挑（推荐）')
    ap.add_argument("--pool", default=cfg_get("pool") or "")
    ap.add_argument("--source", action="append", default=[],
                    help="额外的素材来源目录（可多次）；里面的视频一起当候选")
    ap.add_argument("--count", type=int, default=1, help="要出几条视频")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    sources = [os.path.expanduser(p) for p in ([args.pool] + args.source) if p]
    sources = [s for s in sources if s and os.path.isdir(s)]
    if not sources:
        sys.exit("没有可用的素材目录（用 --pool/--source 指定，或配置 pipeline_config）")
    files = []
    for s in sources:
        for f in sorted(os.listdir(s)):
            if f.endswith((".mov", ".mp4", ".MOV", ".MP4")) and not f.startswith("."):
                files.append(f)
    led = ledger_mod.load()

    print(f"素材来源 {len(sources)} 个目录，共 {len(files)} 条；台账里用过 {len(led)} 条\n")
    plan, used_in_video = {}, set()
    for spec in args.need:
        parts = spec.split(":", 2)
        if len(parts) == 3 and parts[1].startswith("c="):
            name, cat_key, pat = parts[0], parts[1][2:], parts[2]
        else:
            name, pat = parts[0], (parts[1] if len(parts) > 1 else "")
            cat_key = ""
        rx = re.compile(pat)
        hits = [f for f in files if rx.search(f)]
        if cat_key:                                  # 類別必須先對上
            cats = [c for c in cat_key.split("|") if c]
            hits = [f for f in hits if any(c in f for c in cats)]
        fresh = [f for f in hits if f not in led]
        stale = sorted([f for f in hits if f in led], key=lambda f: len(led[f]))
        picks = [f for f in fresh if f not in used_in_video][: args.count]
        if len(picks) < args.count:
            for f in stale:
                if f not in used_in_video and f not in picks:
                    picks.append(f)
                if len(picks) == args.count:
                    break
        if not hits:
            print(f"【{name}】⚠️ 这个类别的素材已经用尽（或没有匹配）——"
                  f"需要补素材，不要拿别的类别顶替")
            plan[name] = []
            continue
        used_in_video.update(picks)
        plan[name] = picks
        print(f"【{name}】候选 {len(hits)}（新 {len(fresh)}）")
        for f in picks:
            print(f"    {'🆕' if f not in led else '♻️ 复用'} {f}")

    if args.out:
        json.dump(plan, open(args.out, "w"), ensure_ascii=False, indent=1)
        print("\n已写出分配表:", args.out)


if __name__ == "__main__":
    main()

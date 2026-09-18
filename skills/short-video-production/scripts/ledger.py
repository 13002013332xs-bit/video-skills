#!/usr/bin/env python3
"""用片台账：记录"哪条素材用在哪支视频里"，选片时优先挑没用过的。

台账位置：~/.config/clip-pipeline/ledger.json
结构：{"素材文件名": ["视频A", "视频B"], ...}

用法:
    python ledger.py --show                      # 看统计（用了多少、剩多少没用过）
    python ledger.py --unused <素材池目录>        # 列出从没用过的素材
    python ledger.py --add <素材名> --video <视频名>
    python ledger.py --record-plan <plan.json> [--video 名称]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from pipeline_config import get as cfg_get
except Exception:
    def cfg_get(_k):
        return ""

LEDGER = os.path.expanduser("~/.config/clip-pipeline/ledger.json")
VIDEO_EXT = (".mov", ".mp4", ".MOV", ".MP4")


def load() -> dict:
    if os.path.exists(LEDGER):
        try:
            return json.load(open(LEDGER))
        except Exception:
            return {}
    return {}


def save(d: dict) -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(d, open(LEDGER, "w"), ensure_ascii=False, indent=1, sort_keys=True)


def add(clip: str, video: str) -> None:
    d = load()
    vids = d.setdefault(clip, [])
    if video not in vids:
        vids.append(video)
    save(d)


def pool_files(pool: str) -> list[str]:
    out = []
    for f in sorted(os.listdir(pool)):
        if f.endswith(VIDEO_EXT) and not f.startswith("."):
            out.append(os.path.join(pool, f))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--unused", metavar="POOL")
    ap.add_argument("--pool", default=cfg_get("pool") or "")
    ap.add_argument("--add")
    ap.add_argument("--video", default="")
    ap.add_argument("--record-plan", metavar="PLAN_JSON")
    args = ap.parse_args()

    d = load()

    if args.show:
        pool = os.path.expanduser(args.pool) if args.pool else ""
        used = len(d)
        multi = {k: v for k, v in d.items() if len(set(v)) > 1}
        print(f"台账：{LEDGER}")
        print(f"  用过的素材 {used} 个，其中被 2 支以上视频共用的 {len(multi)} 个")
        if pool and os.path.isdir(pool):
            files = [os.path.basename(p) for p in pool_files(pool)]
            unused = [f for f in files if f not in d]
            print(f"  素材池 {len(files)} 条 → 没用过的 {len(unused)} 条")
        for k, v in sorted(multi.items(), key=lambda x: -len(x[1]))[:10]:
            print(f"    {len(v)} 支共用: {k}")
        return

    if args.unused:
        pool = os.path.expanduser(args.unused)
        files = [os.path.basename(p) for p in pool_files(pool)]
        unused = [f for f in files if f not in d]
        print(f"没用过的素材 {len(unused)} 条：")
        for f in unused:
            print("  ", f)
        return

    if args.record_plan:
        plan = json.load(open(args.record_plan))
        video = args.video or plan.get("draft_name", "未命名视频")
        n = 0
        for c in plan.get("clips", []):
            src = os.path.basename(c.get("path", ""))
            # plan 里的 path 是编码后的 01.mp4；真正的素材名看 src_name（若有）
            src = c.get("src_name") or c.get("source") or src
            add(src, video)
            n += 1
        print(f"已登记 {n} 段 → {video}")
        return

    if args.add:
        add(args.add, args.video or "未命名视频")
        print("已登记", args.add)
        return

    ap.print_help()


if __name__ == "__main__":
    main()

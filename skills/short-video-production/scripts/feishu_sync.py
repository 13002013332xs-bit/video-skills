#!/usr/bin/env python3
"""飞书素材「增量同步」：只下载本地没有的新素材，并记录已下载清单。

前提：本机有飞书用户令牌（默认取项目里的 .user_token.json，可用 --token 指定），
以及一份清点清单（由 feishu_media.py inventory 生成）。

用法:
    python feishu_sync.py --inventory <inventory.json> --dest <素材目录> --report   # 只看新增
    python feishu_sync.py --inventory <inventory.json> --dest <素材目录> --limit 60 # 下载最多 60 条

注意：令牌 2 小时过期，过期后需要用户重新授权一次。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_TOKEN = os.path.expanduser(
    "~/Documents/Codex/2026-08-05/qin/work/feishu-dl/.user_token.json")
API = "https://open.feishu.cn/open-apis"
STATE_NAME = "_已下载清单.json"
VIDEO_EXT = (".mov", ".mp4", ".MOV", ".MP4")


def token(path: str) -> str:
    d = json.load(open(os.path.expanduser(path)))
    if d.get("expires_at", 0) < time.time():
        sys.exit("飞书令牌已过期：请重新授权一次（见 references/material-sourcing.md）")
    return d["access_token"]


def fetch(tok: str, file_token: str, out: str) -> None:
    req = urllib.request.Request(f"{API}/drive/v1/medias/{file_token}/download",
                                 headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=180) as r, open(out, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--token", default=DEFAULT_TOKEN)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    inv = json.load(open(args.inventory))
    dest = os.path.expanduser(args.dest)
    os.makedirs(dest, exist_ok=True)
    state_path = os.path.join(dest, STATE_NAME)
    state = json.load(open(state_path)) if os.path.exists(state_path) else {"downloaded": []}
    done = set(state.get("downloaded", []))
    done |= {f for f in os.listdir(dest) if f.endswith(VIDEO_EXT)}

    new = [m for m in inv if m["name"] not in done]
    print(f"清单 {len(inv)} 条；本地已有 {len(done)} 条；新增 {len(new)} 条")
    for m in new[:40]:
        print(f"   🆕 [{m.get('category','')}] {m['name']}  {m.get('size',0)//1048576}MB")
    if len(new) > 40:
        print(f"   … 还有 {len(new)-40} 条")
    if args.report or not new:
        return
    if args.limit:
        new = new[: args.limit]

    tok = token(args.token)
    ok = 0
    for i, m in enumerate(new, 1):
        name = f"{m.get('category','素材').replace('/','_')}__{m['name']}"
        out = os.path.join(dest, name)
        if os.path.exists(out):
            continue
        try:
            fetch(tok, m["fileToken"], out)
            ok += 1
            done.add(m["name"])
            print(f"[{i}/{len(new)}] {name}", flush=True)
        except urllib.error.HTTPError as e:
            print(f"[{i}/{len(new)}] 失败 {name}: HTTP {e.code}")
        except Exception as e:
            print(f"[{i}/{len(new)}] 失败 {name}: {e}")
    state["downloaded"] = sorted(done)
    json.dump(state, open(state_path, "w"), ensure_ascii=False, indent=1)
    print(f"\n完成：新下载 {ok} 条 → {dest}")


if __name__ == "__main__":
    main()

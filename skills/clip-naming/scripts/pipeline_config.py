#!/usr/bin/env python3
"""统一的路径配置：脚本都从这里读目录，不再写死某个人的绝对路径。

配置文件：~/.config/clip-pipeline/config.json
环境变量优先（CLIP_VIDEOS_ROOT / CLIP_JIANYING_DRAFTS / CLIP_CAPCUT_ADAPTER / CLIP_POOL）

命令行用法（给 bash 脚本取单个值）：
    python3 pipeline_config.py videos_root
    python3 pipeline_config.py --init        # 交互式配置（第一次用）
    python3 pipeline_config.py --show
"""
from __future__ import annotations

import json
import os
import sys

CONFIG_PATH = os.path.expanduser("~/.config/clip-pipeline/config.json")

DEFAULTS = {
    "videos_root": "~/Desktop/短视频素材",
    "jianying_drafts": "~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft",
    "capcut_adapter": "~/Developer/capcut-mate/local/plan_to_draft.py",
    "pool": "",          # 素材池（可选）；留空表示用 videos_root
    "project_dir": "",   # 工作目录（可选）；留空表示用系统临时目录
}

ENV = {
    "videos_root": "CLIP_VIDEOS_ROOT",
    "jianying_drafts": "CLIP_JIANYING_DRAFTS",
    "capcut_adapter": "CLIP_CAPCUT_ADAPTER",
    "pool": "CLIP_POOL",
    "project_dir": "CLIP_PROJECT_DIR",
}

# 常見位置：先自己找，找不到才問用戶
CANDIDATES = {
    "jianying_drafts": [
        "~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft",
        "~/Movies/JianyingPro/User Data/Projects",
        "~/Movies/剪映/User Data/Projects",
    ],
    "capcut_adapter": [
        "~/Developer/capcut-mate/local/plan_to_draft.py",
        "~/capcut-mate/local/plan_to_draft.py",
        "~/Documents/capcut-mate/local/plan_to_draft.py",
        "~/.local/opt/capcut-mate/local/plan_to_draft.py",
    ],
    "videos_root": [
        "~/Desktop/短视频素材",
        "~/Desktop/素材",
        "~/Movies/短视频素材",
        "~/Desktop/2026-09-16",
    ],
}


def autodetect(key: str) -> str:
    """自動找常見位置；找不到再去找特徵檔（例如 plan_to_draft.py）。"""
    for cand in CANDIDATES.get(key, []):
        p = os.path.expanduser(cand)
        if os.path.exists(p):
            return p
    if key == "capcut_adapter":
        for root in ("~/Developer", "~/Documents", "~/.local/opt", "~"):
            base = os.path.expanduser(root)
            if not os.path.isdir(base):
                continue
            for cur, dirs, files in os.walk(base):
                if cur.count(os.sep) - base.count(os.sep) > 4:
                    dirs[:] = []
                    continue
                if "plan_to_draft.py" in files:
                    return os.path.join(cur, "plan_to_draft.py")
    return ""


def load() -> dict:
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            cfg.update(json.load(open(CONFIG_PATH)))
        except Exception:
            pass
    for key, env in ENV.items():
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    out = {}
    for k, v in cfg.items():
        v = os.path.expanduser(v) if isinstance(v, str) else v
        if not v or not os.path.exists(v):        # 沒配或配的路徑不存在 → 自己找找看
            found = autodetect(k)
            if found:
                v = found
        out[k] = v
    return out


def get(key: str) -> str:
    return load().get(key, "")


def save(cfg: dict) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    json.dump(cfg, open(CONFIG_PATH, "w"), ensure_ascii=False, indent=1)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(json.dumps(load(), ensure_ascii=False, indent=1))
        return
    if args[0] == "--show":
        cfg = load()
        for k, v in cfg.items():
            exists = "✅" if v and os.path.exists(v) else ("—" if not v else "❌")
            print(f"{exists} {k:<16} {v or '(未设置)'}")
        print(f"\n配置文件：{CONFIG_PATH}")
        return
    if args[0] == "--init":
        cfg = load()
        prompts = {
            "videos_root": "素材根目录（里面放 开头/中间/结尾 和 未命名上传）",
            "jianying_drafts": "剪映草稿目录（找不到就回车跳过）",
            "capcut_adapter": "capcut-mate 的 plan_to_draft.py 路径（没有就回车跳过）",
            "pool": "素材池目录（可选，回车跳过）",
            "project_dir": "工作目录（可选，回车跳过）",
        }
        for k, q in prompts.items():
            cur = cfg.get(k, "")
            val = input(f"{q}\n  当前：{cur or '(未设置)'}\n  新的（回车保持不变）: ").strip()
            if val:
                cfg[k] = val
        save(cfg)
        print("\n已保存到", CONFIG_PATH)
        return
    print(get(args[0]))


if __name__ == "__main__":
    main()

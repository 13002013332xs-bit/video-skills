#!/usr/bin/env python3
"""Name-driven clip picker: honours the 10-beat structure of the reference video.

Every beat has its own keyword rule (what the shot MUST show and what it must NOT
show). Clips are then handed out so that the videos share as few shots as
possible.
"""
import os
import re
import json
import hashlib
import subprocess

FFPROBE = os.path.expanduser("~/.local/bin/ffprobe")


def clip_len(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    try:
        return float(r)
    except ValueError:
        return 0.0


BEAT_USE = {"掉零件①": 2.8, "掉零件②": 3.7, "展示灯": 2.5, "拉弯吸+展示": 7.0,
            "吸零件特写": 4.5, "再吸发动机": 3.8, "底部吸住+拉长+照亮": 8.0,
            "收起灯吸住照深处": 2.73, "前后吸零件": 4.0, "结尾": 4.74}

BASE = "/Users/wangsi/Documents/Codex/2026-08-05/qin/work/feishu-dl/downloads"
FOLDERS = [os.path.join(BASE, d) for d in ("开头", "中间", "结尾", "pool")]

BEATS = [
    ("掉零件①", r"(搞掉|打掉|推掉|拔掉).*(零件|扳手|套筒|钉子|物品)|手推掉|扳手捏", r"下水道", "开头"),
    ("掉零件②", r"(搞掉|打掉|推掉|拔掉|捡不到|捡不起).*(零件|扳手|套筒|钉子|物品)|手推掉|双手打掉|手深入", r"下水道", "开头"),
    ("展示灯", r"(开灯|展灯|展磁吸灯|镜头展示)", r"引下单|伸弯|吸出|吸住|吸上|吸套筒", "灯"),
    ("拉弯吸+展示", r"伸弯.*(吸|照)", r"引下单", "中间"),
    ("吸零件特写", r"特写", r"照深处|照亮|引下单", "中间"),
    ("再吸发动机", r"(发动机|管子|深入)", r"特写|引下单|伸弯", "中间"),
    ("底部吸住+拉长+照亮", r"伸.*照", r"引下单|伸弯", "中间"),
    ("收起灯吸住照深处", r"(照深处|照亮)", r"伸\+|引下单", "中间"),
    ("前后吸零件", r"前吸.*后吸", r"引下单", "中间"),
    ("结尾", r"引下单", None, "结尾"),
]

# 视频（1）已经用过、用户认可的片段，不再复用
USED_BY_V1 = [
    "橙扳手搞掉多个零件进发动机（稍正）",
    "手搞掉零件+努力捡但不行",
    "开灯+展灯",
    "灯伸弯+照掉落钉子+吸+展示",
    "吸扳手（特写）",
    "吸出发动机钉子",
    "后吸住+伸+照深处（正）",
    "弯的灯后吸住（下往上）",
    "前吸后吸扳手+橙扳手（3次）",
    "缩+后吸住+引下单",
]

# 每个镜位里"最像参考视频那一拍"的名字优先排前面
PREFERRED = {
    "掉零件①": ["搞掉零件被爸打1", "搞掉零件被爸打2", "搞掉零件被爸打3", "手搞掉扳手入发动机",
               "扳手搞掉套筒+手捡不到", "手推掉2扳手"],
    "掉零件②": ["扳手搞掉套筒+手捡不到", "双手打掉多个零件+手捡不到+空手", "手搞掉扳手入发动机",
               "拿钳子维修+然后搞掉多个零件", "搞掉零件被爸打2", "搞掉零件被爸打3"],
    "展示灯": ["拿出磁吸灯+开灯", "123展磁吸灯（包装袋）", "321掀开木板展灯", "3长灯一起弯去展灯",
             "多次伸缩&弯曲+展灯", "单灯后吸住镜头展示", "单灯后斜吸住镜头展示"],
    "拉弯吸+展示": ["灯伸弯+吸发动机掉落的钥匙+展示", "伸弯灯+吸带把套筒+展示",
                 "横向伸弯灯+吸套筒+展示（右）", "横向伸弯灯+吸套筒+展示（左）",
                 "照掉落套筒+伸弯灯+吸出+展示（右）", "伸弯+车底假装吸（侧）"],
    "吸零件特写": ["前吸套筒（正+微特写）", "吸出套筒（特写）", "前吸多层套筒（特写）",
                "吸出粗长钉（特写）", "吸出带帽钉子（特写）", "2钉子吸出粗钉子（特写）",
                "吸2细钉子（特写）", "吸出U型钉（特写）"],
    "再吸发动机": ["前深入吸出小钉子", "从管子吸出套筒（发动机）", "从管子吸出套筒+展示（发动机）",
                "前吸出钉子+展（发动机）", "伸+灯深入发动机准备吸", "钥匙深处吸出（特侧写）"],
    "底部吸住+拉长+照亮": ["后吸住+伸+照深处（侧）", "后吸住+伸+照深处（右拍）", "后吸住+伸+照（微仰拍）",
                     "后吸住+伸+照亮", "伸+照亮狭窄"],
    "收起灯吸住照深处": ["后吸住+照深处+特写深处被照亮（俯）", "后吸住+照深处+特写深处被照亮（右侧拍）",
                   "后吸住+照深处（右侧拍）", "底部吸住+照亮", "后吸住+照亮（侧）", "长灯后吸住+照亮"],
    "前后吸零件": ["前吸扳手后吸锤子", "前吸钉套筒后吸钉子（正）", "前吸钉套筒后吸钉子（俯）",
                "前吸钉子后吸锤子", "前吸粗钉+后吸住2"],
    "结尾": ["双手收多灯+引下单", "单手收多灯+引下单", "按顺序关3灯+引下单", "6盒子左右碰上下碰+引下单（厨房）",
           "后吸住+引下单", "后吸细钉子前吸钥匙+引下单（右）", "展灯+引下单"],
}

VIDEOS = ["2", "3", "4", "5", "6"]


def load_clips():
    clips = {}
    seen_content = {}
    aliases = {}
    for folder in FOLDERS:
        if not os.path.isdir(folder):
            continue
        for f in sorted(os.listdir(folder)):
            if f.startswith(".") or not f.lower().endswith((".mov", ".mp4")):
                continue
            path = os.path.join(folder, f)
            # 同一個片段可能被下載過兩次、檔名不同 -> 按內容去重
            with open(path, "rb") as fh:
                key = (os.path.getsize(path), hashlib.md5(fh.read(2_000_000)).hexdigest())
            if key in seen_content:
                aliases[f] = seen_content[key]
                continue
            seen_content[key] = f
            cat = "开头" if (folder.endswith("/开头") or f.startswith("开头_")) else \
                  "结尾" if (folder.endswith("/结尾") or f.startswith("结尾_")) else "中间"
            clips.setdefault(f, (path, cat))
    globals()["ALIASES"] = aliases
    return clips


def match(clips, must, must_not, want_cat):
    out = []
    for name, (path, cat) in clips.items():
        if want_cat == "结尾" and cat != "结尾":
            continue
        if want_cat == "开头" and cat != "开头":
            continue
        if want_cat == "中间" and cat != "中间":
            continue
        if want_cat == "灯" and cat == "结尾":
            continue
        if not re.search(must, name):
            continue
        if must_not and re.search(must_not, name):
            continue
        out.append((name, path, cat))
    return out


def rank(beat, cands):
    order = PREFERRED.get(beat, [])
    need = BEAT_USE.get(beat, 0) + 0.5   # 至少要夠這個長度才不會出現時間軸空洞

    def score(item):
        name, path, _ = item
        too_short = 0 if clip_len(path) >= need else 1
        for i, key in enumerate(order):
            if key in name:
                return (too_short, i)
        return (too_short, len(order) + 1)

    return sorted(cands, key=lambda it: (score(it), len(it[0]), it[0]))


def build_plan(clips):
    plan = {}
    taken = set()
    for beat, must, must_not, cat in BEATS:
        cands = match(clips, must, must_not, cat)
        cands = [c for c in cands if not any(u in c[0] for u in USED_BY_V1)]
        ranked = rank(beat, cands)
        picks = []
        for name, path, c in ranked:
            if name in taken:
                continue
            picks.append((name, path))
            taken.add(name)
            if len(picks) == len(VIDEOS):
                break
        plan[beat] = picks
    return plan


def main():
    clips = load_clips()
    plan = build_plan(clips)
    clean = lambda n: re.sub(r"^(开头_演戏开头__|开头_寻常开头__|中间_中部__|中间_前端__|"
                             r"中间_后端__|结尾__)", "", n)
    print(f"本地素材總數: {len(clips)}   要出 {len(VIDEOS)} 條（2~6）\n")
    for beat in [b[0] for b in BEATS]:
        print(f"【{beat}】")
        for i, v in enumerate(VIDEOS):
            picks = plan[beat]
            if i < len(picks):
                print(f"   视频{v}: {clean(picks[i][0])}")
        print()

    out = {}
    for beat in [b[0] for b in BEATS]:
        for i, v in enumerate(VIDEOS):
            picks = plan[beat]
            if i < len(picks):
                out.setdefault(v, {})[beat] = {"name": picks[i][0], "path": picks[i][1]}
    with open("plan_final.json", "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("已保存 plan_final.json")


if __name__ == "__main__":
    main()

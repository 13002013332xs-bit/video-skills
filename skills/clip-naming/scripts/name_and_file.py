#!/usr/bin/env python3
"""把描述 JSON 变成名字 + 分类 + 归档（复制，不移动原片）。

用法:
    python name_and_file.py <描述json 或 文件夹> [--product 磁吸灯] [--date YYYYMMDD]
                            [--dest 根目录] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys

# 视觉字段 → 用户的写法
ACTION_MAP = [
    ("假吸", "假吸"), ("准备", "准备前吸"), ("指功能", "指功能"), ("指", "指功能"),
    ("后吸住", "后吸住"), ("后吸", "后吸"), ("底部吸", "底部吸"), ("底吸", "底部吸"),
    ("吸出", "吸出"), ("吸住", "吸住"),
    ("伸", "伸"), ("拉长", "伸"), ("弯", "弯"), ("缩", "缩"), ("收回", "缩"),
    ("收起", "收"), ("收", "收"),
    ("开灯", "开灯"), ("照亮", "照亮"), ("照", "照"), ("展示", "展"), ("展", "展"),
    ("搞掉", "搞掉"), ("打掉", "搞掉"), ("敲", "敲"), ("涂水", "涂水"), ("涂色", "涂色"),
    ("拉远", "拉远"), ("拉出", "拉出"), ("入镜", "入镜"), ("不膨胀", "不膨胀"),
    ("滴胶", "滴胶"), ("滴", "滴"), ("拉丝", "拉丝"), ("冒烟", "冒烟"), ("起火", "起火"),
    ("插", "插"), ("触碰", "触碰"), ("按压", "按压"), ("放入", "放入"), ("倒入", "倒入"),
    ("旋转出", "旋转出"), ("吸", "吸"),
]
# 结果里的关键名词：越具体越优先（用户要求写到"细钉子"这种颗粒度）
NOUNS = ("细带把套筒", "带把套筒", "多层套筒", "长套筒", "套筒",
         "粗长钉子", "带帽钉子", "弯长钉子", "细钉子", "粗钉子", "长钉子", "小钉子",
         "U型钉", "钉子", "橙扳手", "短扳手", "长扳手", "车底扳手", "扳手",
         "柜子缝隙钥匙", "钥匙", "锤子", "铁桶", "重物", "螺丝", "圆片", "圆筒",
         "触控笔", "笔头", "刻字", "开瓶器", "螺丝刀", "包装", "车盖")
# 位置提示：补进括号，让名字更准
PLACES = ("车底", "车盖", "发动机", "洗手池", "下水道", "柜子", "沙发底", "缝隙",
          "后备箱", "垃圾桶", "桌面", "盘子")
# 剧情化开场信号（这些基本都归"开头/演戏开头"）
SCRIPTED = ("滴胶", "滴", "冒烟", "烟", "搞掉", "假装", "失手", "撕", "敲", "倒", "洒", "打翻")
# 开场动作信号（从袋/盒里拿出来、拆包装 → 属于开头）
OPENING = ("拿出", "取出", "抽出", "剪开", "拆开", "拆袋", "打开包装", "捧出", "托出", "拿出包装")
# 结束动作信号（收起/关灯/放回 → 才可能是结尾）
ENDING = ("收起", "收回", "关灯", "放回", "装回", "装袋", "合上", "盖上")
VIEW_MAP = {"特写": "（特）", "俯": "（俯）", "侧": "（侧）", "跟随": "（跟随）"}
SUBJECT_KEEP = re.compile(r"单灯|双灯|多灯|\d+只|\d+灯|双支|双色|黄笔|黑笔|触控笔|平面|立体|动物")


def build_name(d: dict) -> str:
    parts: list[str] = []
    # 主角（不是产品本身时也照实写：指甲油瓶/手/扳手/发动机）
    lead = str(d.get("画面主角") or "").strip()
    lead_short = ""
    if lead:
        m0 = re.match(r"^([\u4e00-\u9fa5A-Za-z0-9]{2,6})", lead)
        if m0:
            lead_short = m0.group(1)
    subject = re.sub(r"^(画面里的|画面中|一个|一只|这是)", "", str(d.get("主体") or "").strip())
    if subject in ("单灯", "一只灯", "灯", "磁吸灯", "单支", "一支", "整体"):
        if lead_short and not any(k in lead_short for k in ("灯", "笔")):
            parts.append(lead_short)               # 主角不是产品，就写主角
        pass                                       # 单数默认不写，跟用户习惯一致
    elif subject and len(subject) <= 6:
        parts.append(subject)                     # 例如 "平面小猫""双支"
    else:
        m = SUBJECT_KEEP.search(subject)
        if m:
            parts.append(m.group(0))
    acts = [a for a in (d.get("动作") or []) if isinstance(a, str)]
    mapped: list[str] = []
    for a in acts:
        for key, val in ACTION_MAP:
            if key in a and val not in mapped and not any(val in x or x in val for x in mapped):
                mapped.append(val)
                break
    parts += mapped[:3]
    result = str(d.get("结果") or "").strip()
    # 结果里可能有 "烟雾/小火苗/螺纹杆插入" 这种并列，取最短的一个当对象
    candidates = [x.strip() for x in re.split(r"[/、,，]", result) if x.strip()]
    result_main = min(candidates, key=len) if candidates else result
    # 对象：优先从"结果/一句话/动作"里找最具体的零件词（细钉子 > 钉子）
    haystack = result_main + " " + str(d.get("一句话") or "") + " " + " ".join(acts)
    for noun in NOUNS:
        if noun in haystack and noun not in "".join(parts):
            parts.append(noun)
            break
    else:
        # 没有命中产品词表：就用画面里真实出现的那个东西
        obj = re.sub(r"^(吸出|吸住|吸|取出|拿出)", "", result_main).strip()
        if obj and obj not in ("没吸到", "看不清") and len(obj) <= 6 and obj not in parts:
            parts.append(obj)
    scene = str(d.get("场景") or "").strip()
    if not scene:                            # 没有场景词时，从原文里找位置
        for pl in PLACES:
            if pl in haystack:
                scene = pl
                break
    view = VIEW_MAP.get(str(d.get("视角") or "").strip(), "")
    if d.get("是否引下单") and "引下单" not in parts:
        parts.append("引下单")

    # 模型直接给的短名优先（它知道画面，比事后截断靠谱）
    given = str(d.get("简短命名") or "").strip().rstrip("。.,，")
    tail0 = view or (f"（{scene[:6]}）" if scene else "")
    if given:
        given = re.sub(r"[，,。.;；]", "+", given)
        given = re.sub(r"\+{2,}", "+", given).strip("+")
        if view and view not in given and len(given) + len(view) <= 16:
            given += view
        elif not view and scene and len(given) + len(tail0) <= 16:
            given += tail0
        return given[:18] if given else "待命名"

    # 画面主角不是磁吸灯（指甲油瓶/手/零件…）→ 直接用模型的一句话，最像人话
    lamp_like = any(k in (lead + subject + "".join(acts) + result) for k in ("灯", "吸", "磁"))
    tail = view or (f"（{scene[:6]}）" if scene else "")
    line = str(d.get("一句话") or "").strip()
    if not lamp_like and line:
        short = re.split(r"[，,。；;：:]", line)[0].strip()
        short = re.sub(r"^(画面里的|画面中)", "", short)
        name = (short[:13] + tail)[:18]
        return name or "待命名"

    # 组装：主体 + 动作 + 对象（对象一定要留住），再看长度决定要不要带括号
    def join(items: list[str]) -> str:
        return re.sub(r"\+{2,}", "+", "+".join(x for x in items if x)).strip("+")

    while len(join(parts)) > 18 and len(parts) > 2:   # 太长先砍中间的多余动作
        parts.pop(-2)
    base = join(parts) or "待命名"
    if len(base) + len(tail) > 18:
        tail = ""
    name = (base + tail)[:20]
    if not name or name in ("待命名", "（特）"):
        # 兜底：直接用模型的一句话（截短）
        line = str(d.get("一句话") or "").strip()
        name = (line[:12] + tail) if line else "待命名"
    return name


def classify(d: dict) -> str:
    acts = "".join(d.get("动作") or [])
    text = acts + str(d.get("结果") or "") + str(d.get("一句话") or "") + " ".join(d.get("时间线") or [])
    has_end = any(k in text for k in ENDING)
    # 从袋/盒里取出、拆包装 → 一定是开头（即使画面里举着多支产品展示）
    if any(k in text for k in OPENING) and not has_end:
        return "开头/演戏开头" if (d.get("是否演戏") or any(k in text for k in SCRIPTED)) else "开头/寻常开头"
    if d.get("是否引下单") and has_end:
        return "结尾"
    if d.get("是否演戏") or any(k in text for k in SCRIPTED):
        return "开头/演戏开头"
    if d.get("是否引下单"):
        return "结尾"
    lead = str(d.get("画面主角") or "") + str(d.get("主体") or "")
    # 画面主角不是磁吸灯（例如指甲油瓶/手/道具）→ 属于开场铺垫
    if lead and not any(k in lead for k in ("灯", "笔", "画")):
        return "开头/寻常开头"
    part = str(d.get("部位") or "")
    result = str(d.get("结果") or "")
    if any(k in acts + result for k in ("打开包装", "拿出来", "拿出", "123", "321")):
        return "开头/寻常开头"
    if "后" in part or any(k in acts for k in ("后吸", "后吸住")) or "底部" in part:
        return "中间/后端"
    if "前" in part or any(k in acts for k in ("吸出", "假吸", "指功能", "特写")) \
            or str(d.get("视角")) == "特写":
        return "中间/前端"
    return "中间/中部"


def safe_copy(src: str, folder: str, name: str, suffix: str = "") -> str:
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(src)[1] or ".mov"
    stem = f"{name}{suffix}"
    dst = os.path.join(folder, stem + ext)
    n = 2
    while os.path.exists(dst):
        dst = os.path.join(folder, f"{stem}{n}{ext}")
        n += 1
    shutil.copy2(src, dst)
    return dst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="描述 json 或包含 json 的文件夹")
    ap.add_argument("--product", default="", help="磁吸灯 / 多功能笔 / 肌理画（仅用于提示）")
    ap.add_argument("--date", default=dt.date.today().strftime("%Y%m%d"))
    ap.add_argument("--dest", default=os.path.expanduser("~/Desktop/短视频素材"))
    ap.add_argument("--suffix", default="", help="文件名后缀，例如 [云端] / [本机]")
    ap.add_argument("--archive", default="", help="命名完成后，把原片移到这个目录（不再留在收件夹）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    jsons: list[str] = []
    if os.path.isdir(args.target):
        jsons = [os.path.join(args.target, f) for f in sorted(os.listdir(args.target))
                 if f.endswith(".json")]
    else:
        jsons = [args.target]
    if not jsons:
        sys.exit("没找到描述 json")

    rows = []
    root = os.path.join(args.dest, args.date)
    for j in jsons:
        d = json.load(open(j))
        src = d.get("文件")
        if not src or not os.path.exists(src):
            print(f"⚠️ 跳过（找不到原文件）：{j}")
            continue
        name = build_name(d)
        cat = classify(d)
        conf = float(d.get("把握度") or 0.0)
        folder = os.path.join(root, cat)
        if args.dry_run:
            rows.append((os.path.basename(src), name, cat, conf, "（演练，未复制）"))
        else:
            dst = safe_copy(src, folder, name, args.suffix)
            if args.archive:
                os.makedirs(args.archive, exist_ok=True)
                target = os.path.join(args.archive, os.path.basename(src))
                n = 2
                while os.path.exists(target):
                    stem, ext = os.path.splitext(os.path.basename(src))
                    target = os.path.join(args.archive, f"{stem}_{n}{ext}")
                    n += 1
                shutil.move(src, target)
            rows.append((os.path.basename(src), name, cat, conf, os.path.relpath(dst, root)))

    print(f"\n{'原文件':<34} {'新名字':<18} {'分类':<14} 把握度")
    for src, name, cat, conf, _ in rows:
        flag = " ⚠️需确认" if conf < 0.6 else ""
        print(f"{src[:32]:<34} {name:<18} {cat:<14} {conf:.2f}{flag}")
    out = os.path.join(root, "_命名确认清单.md")
    if not args.dry_run:
        os.makedirs(root, exist_ok=True)
        with open(out, "w") as fh:
            fh.write("| 原文件 | 新名字 | 分类 | 把握度 | 新位置 |\n|---|---|---|---|---|\n")
            for src, name, cat, conf, rel in rows:
                fh.write(f"| {src} | {name} | {cat} | {conf:.2f} | {rel} |\n")
        print(f"\n确认清单：{out}")


if __name__ == "__main__":
    main()

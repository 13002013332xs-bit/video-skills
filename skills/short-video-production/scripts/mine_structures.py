#!/usr/bin/env python3
"""多视频结构挖掘：读若干条参考视频的拆解结果 → 提炼共性 → 出脚本模板。

输入：每个参考视频一份 shots.json（analyze_reference.py 产出）+ 可选转写 JSON
输出：<out>/structure_report.md（共性报告）+ <out>/script_template.json（脚本骨架）

用法:
    python mine_structures.py <目录1> <目录2> ... --out <输出目录>
    目录里应有 ref_analysis/shots.json 与 edit/transcripts/vo.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

KEY_FILE = os.path.expanduser("~/.local/opt/clip-naming/dashscope.key")
BASE = os.environ.get("CLIP_VLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL = os.environ.get("CLIP_VLM_API_MODEL", "qwen3-vl-plus")

NORMALIZE_PROMPT = """下面是一条参考视频的「分镜 + 脚本」。请把它归一化成结构表，只输出 JSON：
{{"segments":[{{"role":"钩子/功能演示/卖点证明/价格/质感/结尾CTA 之一",
  "share":<占整条视频的百分比,整数>,"visual":"这一拍画面要点(15字内)",
  "voice":"这一拍口播要点(15字内)"}}],"hook_type":"提问/反常识/结果前置/故事/其他 之一",
"selling_order":["按出现顺序的卖点关键词"]}}

分镜：
{shots}

脚本：
{script}
"""

REPORT_PROMPT = """下面是我拆解 {n} 条同类参考视频后归一化的结构数据。请提炼共性并给出可直接用的脚本模板。
只输出 Markdown，包含四节：
## 一、这些视频的共同结构（各段占比、顺序）
## 二、最有共性的 3 个钩子写法（各给一句示例）
## 三、共性卖点顺序与对应画面要求
## 四、可直接套用的脚本模板（逐拍：时间 | 画面要求 | 口播要点）

数据：
{data}
"""


def key() -> str:
    k = os.environ.get("DASHSCOPE_API_KEY")
    if not k and os.path.exists(KEY_FILE):
        k = open(KEY_FILE).read().strip()
    if not k:
        sys.exit("没有找到百炼 API key")
    return k


def ask(prompt: str, k: str, max_tokens: int = 2000) -> str:
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens, "temperature": 0.3}
    req = urllib.request.Request(BASE + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + k,
                                          "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=180))
            return r["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt < 2:
                time.sleep(2)
                continue
            raise


def load_one(folder: str) -> tuple[str, str, str]:
    shots_path = os.path.join(folder, "ref_analysis", "shots.json")
    if not os.path.exists(shots_path):
        alt = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".shots.json")]
        if not alt:
            raise SystemExit(f"{folder} 里找不到 shots.json（先跑 analyze_reference.py）")
        shots_path = alt[0]
    d = json.load(open(shots_path))
    shots = d.get("shots", [])
    shots_txt = "\n".join(
        f"- {s['start']:.1f}-{s['end']:.1f}s({s.get('dur', 0):.1f}s) "
        f"{s.get('作用','?')} {s.get('一句话','')}" for s in shots)
    name = os.path.basename(folder.rstrip("/"))
    tr = os.path.join(folder, "edit", "transcripts", "vo.json")
    script = ""
    if os.path.exists(tr):
        script = (json.load(open(tr)).get("text") or "")[:2500]
    return name, shots_txt, script


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    k = key()

    normalized = {}
    for folder in args.folders:
        name, shots_txt, script = load_one(folder)
        print(f"归一化 {name} …", flush=True)
        raw = ask(NORMALIZE_PROMPT.format(shots=shots_txt, script=script or "（无转写）"), k, 1200)
        try:
            data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        except Exception:
            data = {"segments": [], "hook_type": "?", "selling_order": []}
        normalized[name] = data
        segs = data.get("segments", [])
        print("   " + " / ".join(f"{s.get('role','?')}{s.get('share','?')}%" for s in segs))

    json.dump(normalized, open(os.path.join(args.out, "normalized_structures.json"), "w"),
              ensure_ascii=False, indent=1)

    print("\n提炼共性 …", flush=True)
    report = ask(REPORT_PROMPT.format(n=len(normalized),
                                      data=json.dumps(normalized, ensure_ascii=False, indent=1)),
                 k, 2500)
    rp = os.path.join(args.out, "structure_report.md")
    open(rp, "w").write(report)
    print(report[:1500])
    print("\n已写出:", rp)


if __name__ == "__main__":
    main()

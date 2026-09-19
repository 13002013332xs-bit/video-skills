#!/usr/bin/env python3
"""从一段长素材里挑「高光窗口」——自动给出最值得用的 2–6 秒和理由。

思路参考开源的 highlight detection（LLM 病毒性信号 + 去重），按我们的流程重写：
抽帧看画面 + （可选）转写看话术 → 分块评估 → 合并 → 输出时间戳。

用法:
    python pick_highlights.py <视频> [--chunk 20] [--top 3] [--transcript xxx.json]
输出:
    终端表格 + <视频名>.highlights.json
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

FFMPEG = os.path.expanduser("~/.local/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/.local/bin/ffprobe")
KEY_FILE = os.path.expanduser("~/.local/opt/clip-naming/dashscope.key")
BASE = os.environ.get("CLIP_VLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL = os.environ.get("CLIP_VLM_API_MODEL", "qwen3-vl-plus")

PROMPT = """这是一段带货素材的第 {idx} 块（{a:.1f}s–{b:.1f}s）的连续画面。
请找出这一块里**最适合放进成片的高光窗口**（2–6 秒），判断标准按重要性排序：
1) 动作完整（用户能一眼看懂在做什么，例如"吸出零件""开灯伸长"）
2) 结果可见（零件被吸出、灯照亮了、价格牌出现）
3) 画面清楚（主体大、不糊、不乱）
4) 有卖点（功能、对比、价格、质感）

只输出 JSON：
{{"highlights":[{{"start":<绝对秒数>,"end":<绝对秒数>,"score":0-100,
  "what":"这段在演什么（10字内）","why":"为什么值得用（15字内）"}}]}}
没有合格的高光就返回 {{"highlights":[]}}。绝对秒数 = 本块起始 {a:.1f} 秒 + 块内偏移。
"""


def key() -> str:
    k = os.environ.get("DASHSCOPE_API_KEY")
    if not k and os.path.exists(KEY_FILE):
        k = open(KEY_FILE).read().strip()
    if not k:
        sys.exit("没有找到百炼 API key")
    return k


def dur(p: str) -> float:
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip()
    return float(r)


def frames(video: str, a: float, b: float, n: int) -> list[str]:
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(n):
            t = a + (b - a) * (i + 0.5) / n
            p = os.path.join(tmp, f"{i}.jpg")
            subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video,
                            "-frames:v", "1", "-vf", "scale=448:-2", "-q:v", "3", p], check=True)
            if os.path.exists(p):
                out.append(base64.b64encode(open(p, "rb").read()).decode())
    return out


def ask(imgs: list[str], k: str, idx: int, a: float, b: float) -> list[dict]:
    content = [{"type": "text", "text": PROMPT.format(idx=idx, a=a, b=b)}]
    for b64 in imgs:
        content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}})
    body = {"model": MODEL, "messages": [{"role": "user", "content": content}],
            "max_tokens": 500, "temperature": 0.2}
    req = urllib.request.Request(BASE + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + k,
                                          "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=120))
            txt = r["choices"][0]["message"]["content"]
            m = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
            return m.get("highlights", [])
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            print("   ⚠️ API 錯誤", e.code, file=sys.stderr)
            return []
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            print("   ⚠️", e, file=sys.stderr)
            return []


def merge(items: list[dict]) -> list[dict]:
    """合併重疊窗口：保留分數高的那個。"""
    items = sorted(items, key=lambda x: -x.get("score", 0))
    kept: list[dict] = []
    for it in items:
        if any(not (it["end"] <= k["start"] or it["start"] >= k["end"]) for k in kept):
            continue
        kept.append(it)
    return kept


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--chunk", type=float, default=20.0, help="每块多少秒（预设 20）")
    ap.add_argument("--frames", type=int, default=5, help="每块抽几帧")
    ap.add_argument("--top", type=int, default=3, help="保留前几个高光")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    video = os.path.abspath(args.video)
    total = dur(video)
    k = key()
    print(f"{os.path.basename(video)}  長 {total:.1f}s，按 {args.chunk:.0f}s 分塊…")

    all_hits: list[dict] = []
    idx = 0
    a = 0.0
    while a < total - 1:
        b = min(total, a + args.chunk)
        idx += 1
        hits = ask(frames(video, a, b, args.frames), k, idx, a, b)
        for h in hits:
            h["start"] = max(a, float(h.get("start", a)))
            h["end"] = min(b, float(h.get("end", b)))
            if h["end"] - h["start"] >= 1.0:
                all_hits.append(h)
        print(f"   塊 {idx}: {a:6.1f}-{b:6.1f}s → {len(hits)} 個候選", flush=True)
        a = b

    kept = merge(all_hits)[: args.top]
    print(f"\n最佳高光（前 {len(kept)} 個）：")
    for h in kept:
        print(f"   {h['start']:6.1f}–{h['end']:6.1f}s  分 {h.get('score','?'):>3}  "
              f"{h.get('what','')} — {h.get('why','')}")
    out = args.out or os.path.join(os.path.dirname(video),
                                   os.path.splitext(os.path.basename(video))[0] + ".highlights.json")
    json.dump({"video": video, "duration": total, "highlights": kept},
              open(out, "w"), ensure_ascii=False, indent=1)
    print("\n已寫出:", out)


if __name__ == "__main__":
    main()

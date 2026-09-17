#!/usr/bin/env python3
"""拆解参考视频：自动分镜 → 每个镜头抽帧 → 用视觉模型读懂每一拍。

用法:
    python analyze_reference.py <参考视频> [--shots 0,6.8,18.1,...] [--out 目录]

输出 <out>/shots.json：
  [{id, start, end, dur, 画面, 动作[], 主角, 景别, 运镜, 作用, 一句话, 把握度}]
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
SCENE_TH = 0.15
KEY_FILE = os.path.expanduser("~/.local/opt/clip-naming/dashscope.key")
BASE = os.environ.get("CLIP_VLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL = os.environ.get("CLIP_VLM_API_MODEL", "qwen3-vl-plus")

PROMPT = """这是同一条参考视频里「第 {i} 个镜头」（起止 {a}s–{b}s，共 {dur:.1f} 秒）的连续画面。
我要照着它剪同类视频，请像剪辑师一样看懂这一拍，只输出 JSON：
{{
 "画面": "这一段到底在演什么（谁、在哪、做什么、看到什么结果）",
 "动作": ["按顺序的动词"],
 "主角": "画面主体（产品/手/工具/道具/人物）",
 "景别": "特写/近景/中景/全景 之一",
 "运镜": "固定/推近/拉远/跟随/手摇 之一",
 "作用": "钩子/展示/证明/引导下单 之一",
 "一句话": "15 字以内",
 "把握度": 0.0-1.0
}}"""


def key() -> str:
    k = os.environ.get("DASHSCOPE_API_KEY")
    if not k and os.path.exists(KEY_FILE):
        k = open(KEY_FILE).read().strip()
    if not k:
        sys.exit("没有找到百炼 API key")
    return k


def duration(path: str) -> float:
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(r)


def detect_shots(video: str, th: float = SCENE_TH) -> list[float]:
    out = subprocess.run([FFMPEG, "-v", "error", "-i", video,
                          "-vf", f"select='gt(scene,{th})',metadata=print:file=-",
                          "-f", "null", "-"], capture_output=True, text=True).stdout
    cuts = [0.0]
    for line in out.splitlines():
        if "pts_time" in line:
            try:
                t = float(line.split("pts_time:")[1].split()[0])
                if t - cuts[-1] > 0.6:          # 忽略碎片切点
                    cuts.append(round(t, 2))
            except (IndexError, ValueError):
                pass
    return cuts


def frames(video: str, a: float, b: float, n: int, tmp: str) -> list[str]:
    step = max((b - a) / n, 0.3)
    out = []
    for k in range(n):
        t = a + step * k + min(0.3, step / 3)
        p = os.path.join(tmp, f"f{k:02d}.jpg")
        subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video,
                        "-frames:v", "1", "-vf", "scale=448:-2", "-q:v", "3", p], check=True)
        if os.path.exists(p):
            out.append(p)
    return out


def ask(frames_list: list[str], i: int, a: float, b: float, k: str) -> dict:
    content = [{"type": "text", "text": PROMPT.format(i=i, a=a, b=b, dur=b - a)}]
    for f in frames_list:
        b64 = base64.b64encode(open(f, "rb").read()).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    body = {"model": MODEL, "messages": [{"role": "user", "content": content}],
            "max_tokens": 500, "temperature": 0.2}
    req = urllib.request.Request(BASE.rstrip("/") + "/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + k,
                                          "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=120))
            txt = r["choices"][0]["message"]["content"]
            m = txt[txt.find("{"): txt.rfind("}") + 1]
            return json.loads(m)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt < 2:
                time.sleep(2)
                continue
            return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--shots", default="", help="自定义切点，逗号分隔（秒）")
    ap.add_argument("--frames", type=int, default=5, help="每个镜头抽几帧")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    video = os.path.abspath(args.video)
    total = duration(video)
    cuts = [float(x) for x in args.shots.split(",") if x.strip()] if args.shots else detect_shots(video)
    cuts = [c for c in cuts if c < total]
    bounds = cuts + [total]
    out_dir = args.out or os.path.join(os.path.dirname(video), "ref_analysis")
    os.makedirs(out_dir, exist_ok=True)
    k = key()

    shots = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        if b - a < 0.5:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            fl = frames(video, a, b, args.frames, tmp)
            info = ask(fl, i + 1, a, b, k)
        info.update({"id": i + 1, "start": round(a, 2), "end": round(b, 2), "dur": round(b - a, 2)})
        shots.append(info)
        print(f"[{i+1}/{len(bounds)-1}] {a:5.2f}-{b:5.2f}s  {info.get('作用','?'):<5} "
              f"{info.get('景别','?')}/{info.get('运镜','?')}  {info.get('一句话','?')}", flush=True)

    out = os.path.join(out_dir, "shots.json")
    json.dump({"video": video, "duration": round(total, 2), "shots": shots},
              open(out, "w"), ensure_ascii=False, indent=1)
    print("已輸出:", out)


if __name__ == "__main__":
    main()

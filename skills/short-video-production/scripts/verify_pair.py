#!/usr/bin/env python3
"""Given a cut segment and candidate 4K sources, sample a few frames from each
(fast keyframe seek) and report how well the segment matches each candidate."""
import os
import subprocess
import sys

import numpy as np

FFMPEG = os.path.expanduser("~/.local/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/.local/bin/ffprobe")
POOL = "/Users/wangsi/Documents/Codex/2026-08-05/qin/work/feishu-dl/downloads/pool"
SIZE = 64


def duration(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(r)


def grab(path, t):
    out = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{t:.3f}", "-i", path,
                          "-frames:v", "1", "-vf", f"scale={SIZE}:{SIZE}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    if len(out) < SIZE * SIZE:
        return None
    return np.frombuffer(out[: SIZE * SIZE], dtype=np.uint8).astype(np.float32)


def frames(path, fracs):
    d = duration(path)
    out = []
    for f in fracs:
        t = max(0.05, min(d - 0.1, d * f))
        img = grab(path, t)
        if img is not None:
            out.append(img)
    return out


def main():
    seg = sys.argv[1]
    cands = sys.argv[2:]
    seg_f = frames(seg, (0.1, 0.3, 0.5, 0.7, 0.9))
    print(f"seg {os.path.basename(seg)} 抽取 {len(seg_f)} 帧")
    rows = []
    for c in cands:
        path = c if os.path.isabs(c) else os.path.join(POOL, c)
        cf = frames(path, tuple(round(0.04 + i * 0.08, 3) for i in range(12)))
        if not cf:
            rows.append((9999.0, os.path.basename(path)))
            continue
        best = min(float(np.sqrt(((a - b) ** 2).mean())) for a in seg_f for b in cf)
        rows.append((best, os.path.basename(path)))
    rows.sort()
    for d, n in rows:
        flag = "  <== 命中" if d < 18 else ""
        print(f"  距離 {d:7.2f}  {n}{flag}")


if __name__ == "__main__":
    main()

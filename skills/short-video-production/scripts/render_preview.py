#!/usr/bin/env python3
"""把剪映草稿渲染成一支預覽 mp4（畫面照草稿的入點/時長，聲音用配音軌）。"""
import json
import os
import subprocess
import sys

FFMPEG = os.path.expanduser("~/.local/bin/ffmpeg")
DRAFTS = "/Users/wangsi/Movies/JianyingPro/User Data/Projects/com.lveditor.draft"
OUT = "/Users/wangsi/Documents/Codex/2026-08-05/qin/outputs"


def render(draft_name):
    d = os.path.join(DRAFTS, draft_name)
    data = json.load(open(os.path.join(d, "draft_content.json")))
    vids = {v["id"]: v for v in data["materials"]["videos"]}
    segments = data["tracks"][0]["segments"]
    audio = data["materials"]["audios"][0]["path"]

    cmd = [FFMPEG, "-v", "error", "-y"]
    for s in segments:
        m = vids[s["material_id"]]
        st = s["source_timerange"]["start"] / 1e6
        du = s["source_timerange"]["duration"] / 1e6
        cmd += ["-ss", f"{st:.3f}", "-t", f"{du:.3f}", "-i", m["path"]]
    cmd += ["-i", audio]
    n = len(segments)
    chain = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    out = os.path.join(OUT, f"{draft_name}.mp4")
    cmd += ["-filter_complex", chain, "-map", "[v]", "-map", f"{n}:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest", out]
    subprocess.run(cmd, check=True)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    for name in sys.argv[1:]:
        p = render(name)
        print("已輸出:", p, os.path.getsize(p) // 1024 // 1024, "MB", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""按 plan_final.json 生成 5 条剪映草稿（只新增，不覆盖任何已有草稿）。

每一步都用「整段素材」放时间线，只标出要用的那一段，
所以在剪映里可以自由把片段拉长/缩短。
"""
import concurrent.futures as cf
import json
import os
import subprocess
import sys

FFMPEG = os.path.expanduser("~/.local/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/.local/bin/ffprobe")
PROJ = "/Users/wangsi/Documents/Codex/2026-08-05/qin"
WORK = os.path.join(PROJ, "work/edit-magnet")
BUILD = os.path.join(WORK, "v2build")
GEN = os.path.expanduser("~/Developer/capcut-mate/local/plan_to_draft.py")
VO = os.path.join(WORK, "vo_tiktok.m4a")
PLAN = os.path.join(WORK, "plan_final.json")

BEATS = ["掉零件①", "掉零件②", "展示灯", "拉弯吸+展示", "吸零件特写",
         "再吸发动机", "底部吸住+拉长+照亮", "收起灯吸住照深处", "前后吸零件", "结尾"]
USE = [2.80, 3.70, 2.50, 7.00, 4.50, 3.80, 8.00, 2.73, 4.00, 4.74]
START_IN = 0.4          # 从素材第 0.4 秒开始用
EXTRA = 8.0             # 后面多留 8 秒，方便你在剪映里往后拉


def duration(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(r)


def encode(args):
    src, dst, length = args
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if is_done(dst, length):
        return dst
    # 被中斷留下的半截檔案 -> 另存一個 _fix 版本，不刪除任何東西
    alt = dst.replace(".mp4", "_fix.mp4")
    if is_done(alt, length):
        return alt
    out = dst if not os.path.exists(dst) else alt
    cmd = [FFMPEG, "-v", "error", "-y", "-i", src]
    if length:
        cmd += ["-t", f"{length:.3f}"]
    cmd += ["-vf", "scale=1080:1920,fps=30", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-pix_fmt", "yuv420p", "-an", out]
    subprocess.run(cmd, check=True)
    return out


def is_done(path, expect):
    """檔案存在、能讀、長度合理，才算轉檔完成（避免半截檔被當成完成）。"""
    if not os.path.exists(path) or os.path.getsize(path) < 100_000:
        return False
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        got = float(r.stdout.strip())
    except ValueError:
        return False
    return got >= min(expect, 0.6) - 0.5


def main():
    plan = json.load(open(PLAN))
    jobs, keys, meta = [], [], {}
    for video, beats in plan.items():
        meta[video] = {}
        for i, beat in enumerate(BEATS):
            src = beats[beat]["path"]
            ln = duration(src)
            window = min(ln, USE[i] + START_IN + EXTRA)
            dst = os.path.join(BUILD, f"v{video}", f"{i + 1:02d}.mp4")
            jobs.append((src, dst, window))
            keys.append((video, beat))
            meta[video][beat] = {"asset": dst, "use": USE[i], "src_name": beats[beat]["name"]}

    print(f"要轉檔 {len(jobs)} 段素材（4K→1080×1920）", flush=True)
    done, results = 0, []
    with cf.ThreadPoolExecutor(max_workers=int(os.environ.get("BUILD_WORKERS", "4"))) as ex:
        for r in ex.map(encode, jobs):
            results.append(r)
            done += 1
            if done % 10 == 0:
                print(f"  已完成 {done}/{len(jobs)}", flush=True)
    for (video, beat), r in zip(keys, results):
        meta[video][beat]["asset"] = r
    print("轉檔完成", flush=True)

    # 每段實際可用長度 → 自動分配時長，避免時間軸出現黑洞，總長固定 43.772s
    total = 43.772
    computed = {}
    for video, beats in plan.items():
        caps = [max(0.5, duration(meta[video][b]["asset"]) - START_IN) for b in BEATS]
        use = list(USE)
        carry = 0.0
        for i in range(len(BEATS)):
            if use[i] > caps[i]:
                carry += use[i] - caps[i]
                use[i] = caps[i]
            elif carry > 1e-6:
                give = min(carry, caps[i] - use[i])
                use[i] += give
                carry -= give
        for i in range(len(BEATS)):
            if carry <= 1e-6:
                break
            spare = caps[i] - use[i]
            if spare > 1e-6:
                give = min(carry, spare)
                use[i] += give
                carry -= give
        diff = total - sum(use)
        if abs(diff) > 1e-3:
            idx = max(range(len(BEATS)), key=lambda i: caps[i] - use[i])
            use[idx] += diff
        computed[video] = use

    suffix = os.environ.get("DRAFT_SUFFIX", "V3")
    drafts = []
    for video, beats in plan.items():
        clips, t = [], 0.0
        for i, beat in enumerate(BEATS):
            info = meta[video][beat]
            use = computed[video][i]
            clips.append({"path": info["asset"], "target_start": round(t, 3),
                          "duration": round(use, 3), "source_start": START_IN, "volume": 0.0})
            t += use
        plan_obj = {
            "draft_name": f"磁吸灯0916（{video}）{suffix}",
            "canvas": {"width": 1080, "height": 1920, "fps": 30},
            "audio": {"path": VO, "start": 0.0, "volume": 1.0},
            "clips": clips,
        }
        p = os.path.join(BUILD, f"plan_v{video}_{suffix}.json")
        json.dump(plan_obj, open(p, "w"), ensure_ascii=False, indent=1)
        runner = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_generator.py")
        out = subprocess.run([sys.executable, runner, p], capture_output=True, text=True)
        print(f"草稿 磁吸灯0916（{video}）{suffix} -> {out.stdout.strip().splitlines()[-1] if out.stdout else out.stderr[-200:]}",
              flush=True)
        drafts.append(video)
    json.dump(meta, open(os.path.join(BUILD, "build_meta.json"), "w"), ensure_ascii=False, indent=1)
    print("全部完成:", drafts)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""看完一整段视频，输出结构化描述 JSON（本机视觉模型，不上传）。

用法:
    python caption_clip.py <视频文件 或 文件夹> [--out 目录] [--limit N]

每个视频产出一个同名 .json，字段：
  主体 / 动作[] / 部位 / 结果 / 视角 / 场景 / 是否演戏 / 是否引下单 / 一句话 / 把握度
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

FFMPEG = os.path.expanduser("~/.local/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/.local/bin/ffprobe")
MODEL = os.environ.get("CLIP_VLM_MODEL", "mlx-community/Qwen2.5-VL-3B-Instruct-4bit")
VIDEO_EXT = (".mov", ".mp4", ".MOV", ".MP4")

# 云端视觉模型（OpenAI 兼容；默认阿里云百炼）
API_KEY_FILE = os.path.expanduser("~/.local/opt/clip-naming/dashscope.key")
API_BASE = os.environ.get("CLIP_VLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
API_MODEL = os.environ.get("CLIP_VLM_API_MODEL", "qwen-vl-plus")
PRODUCT = os.environ.get("CLIP_PRODUCT", "磁吸灯")

PROMPT = """这是同一段拍摄素材的连续画面（按时间顺序，共 {n} 张）。

**第一步：只描述你真实看到的东西，不要预设产品是什么。**
很多片段里出现的并不是产品本身——可能是指甲油瓶/胶水、手、工具、发动机、液体、烟雾、道具。
先老实说你看到了什么，再谈它在做什么。

参考词汇（只在画面里真的出现时才用）：
· 如果出现一根可弯曲、可伸缩、带 LED 的磁性拾取工具，那是「磁吸灯」，我们简称"灯"；
  它常吸附金属零件：细钉子/粗钉子/带帽钉子/套筒/带把套筒/扳手/锤子/钥匙/铁桶。
· 如果是小瓶子在滴液体、冒烟，那就照实写「指甲油瓶滴胶」「胶瓶滴胶」「冒烟」——
  不要硬说成磁吸灯在吸零件。

按下面 JSON 输出（不要解释、不要代码块）：
{{
 "画面主角": "画面里最主要的东西（磁吸灯/指甲油瓶/胶瓶/扳手/手/发动机…）",
 "看到的东西": ["按重要程度列 3-5 个真实出现在画面里的东西"],
 "时间线": ["<起-止秒> <这一段具体看到什么>", "<起-止秒> <...>"],
 "主体": "单灯/双灯/多灯/8只/指甲油瓶/双支/平面小猫 等（照实写）",
 "动作": ["按时间顺序，优先用这些词：吸/吸出/吸住/后吸住/底部吸/假吸/指功能/伸/弯/缩/开灯/照/照亮/展/搞掉零件/敲一敲/拿起/放下/收起"],
 "部位": "前端/后端/底部/整体 之一（只有真的用磁吸灯时才分部位；否则填 整体）",
 "结果": "动作直接作用的对象，照实写：细钉子/粗长钉子/带帽钉子/套筒/扳手/钥匙/指甲油/胶水/烟雾/没吸到/照亮某处",
 "视角": "特写/俯/侧/跟随/正常 之一",
 "场景": "发动机/车底/车盖/后备箱/洗手池/下水道/柜子/桌面/盘子/货架；没有就空字符串",
 "是否演戏": true 或 false（剧情化动作：滴胶/冒烟/假装失手/故意搞掉零件/夸张表演 = true）,
 "是否引下单": true 或 false（只有出现「收起所有灯/放回包装/双手举多灯展示/引导下单字幕或手势」才算 true；单纯关灯、单纯展示不算）,
 "一句话": "15 字以内中文",
 "简短命名": "按用户的命名习惯给这段起个名字：不超过 12 个汉字，格式是「对象+动作(+结果)」，连续动作用 + 连接，可用（特）（俯）（侧）表示视角；不要写成句子、不要标点。示例：指甲油瓶滴胶包裹套筒 / 手伸入发动机按压部件 / 零件冒烟起火 / 双手展示八支磁吸灯 / 吸出细钉子",
 "把握度": 0.0 到 1.0（看不清就写低）
}}

严格要求：
1. 「时间线」必须描述**这段画面本身**看到的内容；上面的 <...> 是占位符，禁止照抄任何示例文字。
2. 看不出来就写「看不清」，绝对不要猜（例如不要写"疑似油盖"）。
3. **不要把画面里不存在的东西写进去**：如果没看到磁吸灯在吸零件，就不要写"吸出XX"。
4. 「结果」只写画面上真实出现过的东西。"""


def duration(path: str) -> float:
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    try:
        return float(r)
    except ValueError:
        return 0.0


def extract_frames(video: str, outdir: str, max_frames: int = 24) -> list[str]:
    """按时间均匀抽帧（含画面变化处），覆盖整段，保证是"看完整段"。"""
    dur = duration(video)
    fps = 1.0 if dur <= 24 else max(0.4, max_frames / max(dur, 1))
    dst = os.path.join(outdir, "f%03d.jpg")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", video,
                    "-vf", f"fps={fps:.3f},scale=448:-2", "-q:v", "3", dst], check=True)
    frames = sorted(f for f in os.listdir(outdir) if f.endswith(".jpg"))
    if len(frames) > max_frames:                      # 太多就等间隔取样
        step = len(frames) / max_frames
        frames = [frames[int(i * step)] for i in range(max_frames)]
    return [os.path.join(outdir, f) for f in frames]


def parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def api_key() -> str:
    k = os.environ.get("DASHSCOPE_API_KEY")
    if not k and os.path.exists(API_KEY_FILE):
        k = open(API_KEY_FILE).read().strip()
    return k or ""


def resolve_local_model(model: str) -> str:
    """本機模型：直接用 HF 快取的本地路徑並離線載入（避免去連 huggingface.co）。"""
    if os.path.isdir(model):
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        return model
    slug = "models--" + model.replace("/", "--")
    snaps = os.path.expanduser(f"~/.cache/huggingface/hub/{slug}/snapshots")
    if os.path.isdir(snaps):
        for d in sorted(os.listdir(snaps)):
            path = os.path.join(snaps, d)
            if os.path.exists(os.path.join(path, "config.json")):
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                return path
    return model


def describe_via_api(frames: list[str], key: str) -> str:
    """一个片段一次调用：整段的帧一起送给视觉模型（看完整段再命名）。"""
    import base64
    import urllib.error
    import urllib.request

    content = [{"type": "text", "text": PROMPT.format(n=len(frames), product=PRODUCT)}]
    for f in frames:
        b64 = base64.b64encode(open(f, "rb").read()).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    body = {"model": API_MODEL, "messages": [{"role": "user", "content": content}],
            "max_tokens": 500, "temperature": 0.2}
    req = urllib.request.Request(
        API_BASE.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    last = ""
    for attempt in range(3):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=120))
            return r["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:200]}"
            if e.code in (429, 500, 502, 503):
                time.sleep(3 * (attempt + 1))
                continue
            raise RuntimeError(last)
        except Exception as e:                    # 网络抖动，重试
            last = str(e)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(last)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="视频文件或包含视频的文件夹")
    ap.add_argument("--out", default=None, help="JSON 输出目录（默认与视频同目录）")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--backend", choices=["auto", "local", "dashscope"], default="auto",
                    help="auto=有 API key 就用云端，否则用本机模型")
    args = ap.parse_args()

    videos: list[str] = []
    if os.path.isdir(args.target):
        for root, _, files in os.walk(args.target):
            videos += [os.path.join(root, f) for f in sorted(files) if f.endswith(VIDEO_EXT)]
    else:
        videos = [args.target]
    if args.limit:
        videos = videos[: args.limit]
    if not videos:
        sys.exit("没找到视频文件")

    key = api_key()
    backend = args.backend
    if backend == "auto":
        backend = "dashscope" if key else "local"
    model = processor = config = None
    if backend == "local":
        # 延迟导入：本机模型要 GPU，云端后端不需要
        from mlx_vlm import generate, load
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.utils import load_config
        local_path = resolve_local_model(args.model)
        print(f"加载本机视觉模型 {local_path} …", flush=True)
        model, processor = load(local_path)
        config = load_config(local_path)
    else:
        if not key:
            sys.exit("没有找到 API key（~/.local/opt/clip-naming/dashscope.key）")
        print(f"使用云端视觉模型 {API_MODEL}", flush=True)

    for i, video in enumerate(videos, 1):
        name = os.path.splitext(os.path.basename(video))[0]
        out_json = os.path.join(args.out or os.path.dirname(video), f"{name}.json")
        if os.path.exists(out_json):
            print(f"[{i}/{len(videos)}] 已有描述，跳过 {name}")
            continue
        with tempfile.TemporaryDirectory() as tmp:
            frames = extract_frames(video, tmp)
            if not frames:
                print(f"[{i}/{len(videos)}] 抽帧失败：{name}")
                continue
            if backend == "dashscope":
                text = describe_via_api(frames, key)
            else:
                prompt = apply_chat_template(processor, config,
                                             PROMPT.format(n=len(frames), product=PRODUCT),
                                             num_images=len(frames))
                text = generate(model, processor, prompt, image=frames, max_tokens=400, verbose=False)
                text = text if isinstance(text, str) else getattr(text, "text", str(text))
        data = parse_json(text)
        data["文件"] = os.path.abspath(video)
        data["时长"] = round(duration(video), 2)
        data["抽帧数"] = len(frames)
        if not data.get("一句话"):
            data["把握度"] = 0.0
            data["原始输出"] = text[:500]
        with open(out_json, "w") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        print(f"[{i}/{len(videos)}] {name} → {data.get('一句话','?')} "
              f"(把握度 {data.get('把握度','?')})", flush=True)


if __name__ == "__main__":
    main()

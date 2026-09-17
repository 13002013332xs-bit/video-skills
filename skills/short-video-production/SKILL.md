---
name: short-video-production
description: 短视频全流程生产：拆解参考视频的镜头结构、转写配音、从素材库（飞书/本地/网络）选片、用 ffmpeg 或剪映草稿出片，并把成片预览交给用户确认。当用户要求"照着某条视频剪""批量出 N 条带货视频""出剪映草稿""拆解/模仿这个视频""给素材库选片段"时使用。
metadata:
  short-description: 拆片 → 选片 → 剪映/ffmpeg 出片 → 预览
---

# 短视频生产流水线（拆片 → 选片 → 剪辑 → 交付）

把"一条参考视频"变成"一批可交付、可编辑的成片"。这条流水线整合了：参考视频拆解、
本地转写、素材获取、按画面语义选片、ffmpeg 精剪与剪映草稿交付、以及验收/清理规范。

## 不可违背的规则（先读这段）

**操作安全**
1. 只新增，不覆盖；重名自动加后缀。
2. 不硬删任何东西（素材、草稿、云端文件）。要清理就**移动到回收目录**（`<项目>/_回收_XXX_日期/`），
   同步维护剪映草稿索引，然后告诉用户回收位置、能否恢复。清理前先列清单取得同意。
3. 素材库/云文档**只读**：只调查询与下载接口。

**交付正确性**
4. **剪映草稿必须自包含**：素材复制进 `<草稿>/assets/`。剪映是沙盒应用，引用草稿目录以外的路径
   会显示"素材丢失"（详见 `references/jianying-draft.md`）。
5. **每段素材的可用时长 ≥ 该镜头需要的时长**，否则时间轴出现黑洞；总时长必须等于配音长度。
6. ffmpeg 精剪时执行 `references/ffmpeg-correctness.md` 里的硬规则（字幕最后、分段无损拼接、
   30ms 淡入淡出、切点落在词边界并留 30–200ms 余量、转写结果缓存）。

**协作方式**
7. 我看不到画面。凡是"这段画面是不是演我要的动作"这类判断，**要么让用户当眼睛确认，要么先用
   客观信号（文件名语义、时长、抽帧比对）得出可复核的结论**，不要猜。
8. 先出 1 条样片或选片清单给用户过目，确认后再批量。
9. 交付习惯：先给**预览成片**（本地绝对路径内嵌），文字极简；片段要留余量，用户能自己拉长拉短。

## 流程

### 1. 拆参考视频

下载原片 → 抽配音当音轨 → **按切镜头分镜**（切一次算一个镜头），逐镜头写"画面含义 + 时长"。
画面结构优先于文案措辞。需要评分/精选镜头时用 `references/reference-analysis.md` 的方法
（Walter Murch 六法则 + 五维评分、多平台下载）。

### 2. 转写（用户提供配音时先听它）

本地跑，不上传：`vu-transcribe <文件> --language en`（faster-whisper，见 `references/transcription.md`）。
词级时间戳是后面切点、字幕的唯一依据；结果按源文件缓存，不重复转写。

### 3. 拿素材

飞书素材库走 OAuth 只读下载（`references/material-sourcing.md`）；网络素材用 yt-dlp；
下完按 `开头/中间/结尾` 与类别整理命名，方便按名字选片。

### 4. 选片（最容易翻车的一步）

按 `references/selection-rules.md` 的硬规则：类别锁定 + 关键词必须命中 + 排除词 +
时长下限 + **按内容去重**（同片段常被下载两次、名字不同）。用 `scripts/pick_clips.py` 落盘分配表。

### 5. 出片

- **要剪映可编辑草稿** → `scripts/build_v2.py`（转码竖屏 + 自动分配时长 + 调
  `scripts/run_generator.py` 生成草稿，素材复制进草稿目录）。
- **要直接成片** → ffmpeg 按 `references/ffmpeg-correctness.md` 精剪；动画/字幕可用
  manim / HyperFrames / Remotion（见 `references/ffmpeg-correctness.md` 末节）。
- 渲染预览：`scripts/render_preview.py`。

### 6. 验收与交付

自检：总长=配音长度、无空洞、视频间重复率 < 30%、草稿自包含、能打开能拖动。
交付时把预览片内嵌给用户，附一句草稿名与"可拉长"的说明。

## 已有工具

- `scripts/pick_clips.py` 选片；`scripts/build_v2.py` 出草稿；`scripts/run_generator.py` 调 capcut-mate；
  `scripts/render_preview.py` 渲染预览；`scripts/verify_pair.py` 反查片段用的是哪条素材。
- 转写：`vu-transcribe`；ffmpeg/ffprobe/yt-dlp 在 `~/.local/bin`；剪映适配层在
  `~/Developer/capcut-mate/local/plan_to_draft.py`。

脚本内是这台机器的绝对路径，换环境先改常量。

## 参考文件

| 需要什么 | 读哪个 |
|---|---|
| 拆片、镜头评分、多平台下载 | `references/reference-analysis.md` |
| 飞书/OAuth、素材下载整理 | `references/material-sourcing.md` |
| 选片硬规则与去重 | `references/selection-rules.md` |
| 剪映草稿结构、沙盒、增删 | `references/jianying-draft.md` |
| ffmpeg 生产正确性、动画/字幕 | `references/ffmpeg-correctness.md` |
| 本地转写、词级时间戳、缓存 | `references/transcription.md` |
| 效率坑与权限坑 | `references/pitfalls.md` |

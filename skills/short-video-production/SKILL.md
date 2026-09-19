---
name: short-video-production
description: 短视频全流程生产：拆解参考视频的镜头结构、转写配音、从素材库（飞书/本地/网络）选片、用 ffmpeg 或剪映草稿出片，并把成片预览交给用户确认。当用户要求"照着某条视频剪""批量出 N 条带货视频""出剪映草稿""拆解/模仿这个视频""给素材库选片段"时使用。
metadata:
  short-description: 拆片 → 选片 → 剪映/ffmpeg 出片 → 预览
---

# 短视频生产流水线（拆片 → 选片 → 剪辑 → 交付）

把"一条参考视频"变成"一批可交付、可编辑的成片"。这条流水线整合了：参考视频拆解、
本地转写、素材获取、按画面语义选片、ffmpeg 精剪与剪映草稿交付、以及验收/清理规范。

## ⚠️ 开工前必做：环境自检（第一次用一定要跑）

**每次接到任务（尤其是新用户第一次用），先跑自检，不要直接开始剪：**

```bash
bash <本技能目录>/scripts/setup_check.sh
```

它会逐项检查：ffmpeg/ffprobe、yt-dlp、python3、**视觉模型 key（"眼睛"）**、capcut-mate 适配层、
剪映草稿目录、素材目录。**任何一项是 ❌，就先停下来，把下面这段原样发给用户，等他配好再继续。**

### 如果缺"眼睛"（最常见）——把下面这段话发给用户

> 我还缺一双"眼睛"：我本身看不见画面，需要接一个视觉模型才能看懂参考视频和你的素材。
> 请你花 3 分钟配一次（免费额度够跑很久）：
>
> 1. 打开 https://bailian.console.aliyun.com/ ，登录/注册阿里云（需实名），开通「百炼」
> 2. 左侧找「API-KEY」→ 创建我的 API-KEY → 复制 `sk-` 开头那串
> 3. 在终端执行（把 `你的key` 换成刚复制的）：
>    ```bash
>    mkdir -p ~/.local/opt/clip-naming
>    printf '%s\n' '你的key' > ~/.local/opt/clip-naming/dashscope.key
>    chmod 600 ~/.local/opt/clip-naming/dashscope.key
>    ```
> 4. 顺手在控制台打开「免费额度用完即停」，防止意外扣费
> 5. 配好跟我说一声，我重新自检一次就开始剪
>
> 费用参考：一条素材约 0.005 元、一条完整成片约 0.1–0.3 元；新用户每个模型送 100 万 token（90 天）。
> 不想用云端的，也可以选本机模型（要 Apple Silicon，跑 `scripts/setup_check.sh` 后会提示）。

### 其它缺项怎么引导

| 缺什么 | 告诉用户 |
|---|---|
| ffmpeg / ffprobe | 装一次即可（macOS 可用静态包放 `~/.local/bin`，或 `brew install ffmpeg`） |
| yt-dlp | `pipx install yt-dlp` 或 `pip install yt-dlp` |
| capcut-mate 适配层 | 按 `references/jianying-draft.md` 获取 `plan_to_draft.py`；如路径不同，改脚本里的 `GEN` |
| 剪映草稿目录 | 装剪映专业版；或改脚本里的草稿目录参数 |
| 素材目录 | 建一个素材文件夹，或改脚本里的 `ROOT`/`POOL` 指到自己的素材 |

### 路径通用化

脚本不再写死某个人的路径。**顺序是：先自己探测 → 探测不到才问用户。**

自动探测规则（`pipeline_config.py` 里的 `CANDIDATES` / `autodetect()`）：
剪映草稿目录找 `~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft`；
capcut-mate 会去 `~/Developer`、`~/Documents`、`~/.local/opt` 里搜 `plan_to_draft.py`；
素材根目录找 `~/Desktop/短视频素材` 等。**只有都找不到时，才问用户：**

1. **素材根目录**（里面有 `开头/中间/结尾` 和 `未命名上传`）—— 例：`~/Desktop/短视频素材`
2. **剪映草稿目录** —— macOS 默认 `~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft`
3. **capcut-mate 的 `plan_to_draft.py` 路径**（生成剪映草稿用；他没有就按 `references/jianying-draft.md` 装）
4. （可选）**素材池目录**、**工作目录**

问完这样写（或直接跑交互式初始化，它会一项一项问）：

```bash
python3 <本技能目录>/scripts/pipeline_config.py --init
# 或者非交互：直接写入 ~/.config/clip-pipeline/config.json
```

配置就存在 `~/.config/clip-pipeline/config.json`，也支持环境变量覆盖
（`CLIP_VIDEOS_ROOT` / `CLIP_JIANYING_DRAFTS` / `CLIP_CAPCUT_ADAPTER` / `CLIP_POOL` / `CLIP_PROJECT_DIR`）。
查当前配置：`python3 <本技能目录>/scripts/pipeline_config.py --show`

个别脚本里仍留有作者示例路径，如与自己机器不符就改：

```bash
grep -rn "/Users/" <本技能目录>/scripts | head -20
```

## 不可违背的规则（先读这段）

**素材不能吃老本（用户明确要求）**
10. **每出一支新视频前，先查用片台账**：`python3 scripts/ledger.py --show`。
    选片一律用 `scripts/pick_fresh.py`（优先"从没用过"的素材），**不要凭记忆挑顺手的**——
    否则不同结构/脚本的视频也会撞画面，用户会看出来。
11. **同一支视频内不重复**；跨视频目标 **0 重复**；实在要用旧素材，必须标明"复用"并说明原因。
12. 出片后**立刻登记台账**（`ledger.py --record-plan`），否则下次还会撞。
13. 素材不够时**先说"池子见底了，需要补素材"**，不要偷偷复用。

**新素材怎么进流程**
- **本地新拍**：用户把片段丢进 `~/Desktop/短视频素材/<日期>/未命名上传/` → 双击「命名并分类.command」
  → 命名后进分类夹；选片时用 `pick_fresh.py --source <分类目录>` 把分类夹也当候选（新片段自动优先）。
- **飞书新素材**：`scripts/feishu_sync.py --inventory <清单.json> --dest <素材池> --report` 先看有没有新增，
  再去掉 `--report` 只下载新增的（本地已下载清单记在 `<素材池>/_已下载清单.json`）。
  飞书令牌 2 小时过期——要长期自动发现新素材，最好让用户把应用加为文件夹协作者（应用身份永久有效）。

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
| **参考视频五维度拆解 + 运动类型判定**（照参考片剪必读） | `references/reference-analysis-5aspect.md` |
| 飞书/OAuth、素材下载整理 | `references/material-sourcing.md` |
| 选片硬规则与去重 | `references/selection-rules.md` |
| 剪映草稿结构、沙盒、增删 | `references/jianying-draft.md` |
| ffmpeg 生产正确性、动画/字幕 | `references/ffmpeg-correctness.md` |
| 本地转写、词级时间戳、缓存 | `references/transcription.md` |
| 效率坑与权限坑 | `references/pitfalls.md` |
| **出片自检协议（准确/完整/可执行）** | `references/self-review.md` |
| **批量出片一致性规则** | `references/batch-consistency.md` |
| **某一拍找不到画面时怎么办** | `references/material-gaps.md` |
| **解说/文案风格矩阵（口吻、钩子、人格、六维质检）** | `references/commentary-styles.md` |
| **混剪与音画同步规则（禁止定格凑时长）** | `references/mixing-rules.md` |
| **从长素材里挑高光片段（8 类信号 + 自动找窗口）** | `references/highlight-picking.md` |
| **语音克隆 / TTS 三条路线与授权红线** | `references/voice-cloning.md` |
| **多视频共性挖掘 → 自动出脚本** | `references/script-generation.md` |

## 画面不够时的铁律（2026-09-19 补）

配音比素材长时，**只允许**这四种做法：直接连接、截取高光段、安全范围内慢放、合并过短的语音段。
**不许**用末帧定格（freeze）、**不许**重复镜头、**不许**把画面拉长到变形来凑时长。
盖不住就**明确告诉用户"这一拍素材不足，需要补拍"**，不许伪造达标。

## 照参考视频剪片的标准流程（2026-09-18 定稿）

1. **拆参考视频**：切镜头 → 转写脚本 → 逐拍五维度拆解（`reference-analysis-5aspect.md`），先讲给用户听
2. **按时间轴对齐**：脚本哪一句 ↔ 参考视频哪几拍（**不要按序号硬配**，会错位）
3. **选片**：类别锁定（c=开头/中间/结尾）+ 关键词（含 `折扣|9.99|30&20|50%` 这类价格词）
   + 台账（`pick_fresh.py`，优先没用过的）
4. **看图验证**：候选抽帧让视觉模型对照参考画面打分，挑最贴合的；同一脚本段跨多拍时**每拍用不同素材**
5. **出片**：按参考视频的真实镜头时长分配；批量时套用统一模板（`batch-consistency.md`）
6. **自检**：成片逐拍打分（`self-review.md`），<0.6 的列出来给改法；改不动的写进报告
7. **交付**：草稿 + 预览 + 自检报告 + 用片台账更新
8. **素材长/多时**：先跑 `scripts/pick_highlights.py` 找高光窗口，再进选片流程（省掉整段看的时间）
9. **要统一音色**：按 `references/voice-cloning.md` 选路线（自己配音 → 直接用；要克隆 → API 或本地，且必须有授权）
10. **要"照着一批爆款出脚本"**：先给每条参考视频跑 `analyze_reference.py`，再用 `scripts/mine_structures.py`
    提炼共性（结构占比/固定顺序/钩子类型/卖点顺序）→ 生成脚本模板 → 按模板出片（详见 `references/script-generation.md`）

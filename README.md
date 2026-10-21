# 项目技能库（Codex Skills）

按项目分类维护技能；技能目录保留在 `skills/`，安装路径不变。

## 按项目查找

| 项目分类 | 技能 | 作用 |
|---|---|---|
| [找达人](projects/creator-outreach/README.md) | [tiktok-dm-outreach](skills/tiktok-dm-outreach/SKILL.md) | 店铺及商品图片选择、PPS和内容筛选、批量邀约、重叠处理、紫鸟私信 |
| [剪辑视频](projects/video-editing/README.md) | [short-video-production](skills/short-video-production/SKILL.md) | 按配音和真实分类选片、原片草稿、预览与独立验收 |
| [剪辑视频 · 素材命名](projects/video-editing/README.md) | [clip-naming](skills/clip-naming/SKILL.md) | 整体命名习惯、按产品选择规则和细分类，支持新增产品 |
| 图片与视频生成 | [dreamina-cli](skills/dreamina-cli/SKILL.md) | 即梦登录、会话、任务及图片/视频生成 |

新增技能时先登记所属项目；一个技能保留一个安装目录，由项目目录提供分类入口，不复制成多个版本。

## 分享“找达人”功能

具体安装、店铺选择和首次连接步骤见 [找达人项目说明](projects/creator-outreach/README.md)。分享版包含授权的店铺商品目录：选泽凡显示对应商品及图片；辉翔达及另两家等待有权限的人补充。每轮话术和佣金自行填写，登录状态不随包分享。

## 分享“剪辑与素材命名”

直接分享本仓库链接；产品选择、磁吸灯/多功能笔规则与剪辑流程位于 [剪辑视频项目说明](projects/video-editing/README.md)。肌理画和多功能锤保留各自学习状态。接收者使用自己的素材、路径和账号权限；规则更新不包含原作者的视频或飞书访问权。

## 安装

### 方式一：手动（最简单）

把 `skills/` 下的文件夹放进：

```
~/.codex/skills/
```

然后在下一轮对话中调用对应技能；若仍未识别，再重启 Codex。

### 方式二：用 Codex 的 skill-installer

让 Codex 从本仓库安装，例如：

```
--repo <owner>/<repo> --path skills/clip-naming
--repo <owner>/<repo> --path skills/short-video-production
--repo <owner>/<repo> --path skills/tiktok-dm-outreach
--repo <owner>/<repo> --path skills/dreamina-cli
```

## 方法论来源

参考视频拆解（五维度）、出片自检协议、批量一致性规则、素材缺口决策这四份参考文档，
思路参考了开源项目 **OpenMontage**（AGPL-3.0，github.com/calesthio/OpenMontage）的做法，
但**内容是按我们自己的流程重写的**（未复制其文件，无许可证传染）。

另外，「解说/文案风格矩阵」与「混剪/音画同步规则」的思路参考了 **JJYB_AI 智剪**
（github.com/jianjieyiban/JJYB_AI_VideoAutoCut，个人使用许可、禁止商用）——
同样只借鉴方法论、未复制其代码，因此不受其许可约束。

新增两项能力：**高光片段自动选取**（`scripts/pick_highlights.py`，思路参考 Anil-matcha/AI-Youtube-Shorts-Generator，MIT）
、**多视频结构挖掘→自动出脚本**（`scripts/mine_structures.py`）与**语音克隆/TTS 路线指南**（`references/voice-cloning.md`，含 MiMo MCP / voice-pro / clone-voice 三条路线与授权红线）。

## 剪辑视频项目需要准备的环境

**按当前任务核对环境。** 仅命名需要可用的看片方式和素材/输出位置；生成草稿才需要核对剪映生成器及目录。先复用已有配置，只有当前步骤确实缺项时再补。旧脚本的配置工具可用：

```bash
python3 skills/short-video-production/scripts/pipeline_config.py --init
```

**然后跑自检**：

```bash
bash skills/short-video-production/scripts/setup_check.sh
```

会逐项告诉你缺什么、怎么补。总共有这几样：

| 需要什么 | 作用 | 怎么补 |
|---|---|---|
| `ffmpeg` / `ffprobe` | 抽帧、转码、拼接 | 装一次即可 |
| `yt-dlp` | 下载参考视频（TikTok/YouTube/抖音等） | `pipx install yt-dlp` |
| Python 3 | 跑脚本 | 3.10+ |
| 可用的画面分析方式 | 看懂完整动作；可复用宿主视觉和有效分析缓存，云端脚本另需配置 | 见所选技能入口 |
| capcut-mate 适配层 | 生成可编辑的剪映草稿 | 见 `references/jianying-draft.md` |
| 剪映专业版 | 最终编辑/导出 | 装剪映 |
| 素材来源 | 你拍的片段（本地文件夹或飞书素材库） | 自己的素材 |

### 可选云端视觉配置

1. 去 <https://bailian.console.aliyun.com/> 开通阿里云百炼 → 创建 API-KEY（`sk-` 开头）
2. 存到本机：

```bash
mkdir -p ~/.local/opt/clip-naming
printf '%s\n' '你的sk-key' > ~/.local/opt/clip-naming/dashscope.key
chmod 600 ~/.local/opt/clip-naming/dashscope.key
```

3. （可选）本机模型（Apple Silicon，约 2GB，无需联网）：

```bash
bash skills/clip-naming/scripts/setup_vision.sh
```

### 配好之后，一句话就能干活

> "照着这个视频剪：" + 链接

也就是：下载参考视频 → 自动切镜头 → 逐拍看懂画面 → 从素材库选对应片段 → 出剪映草稿 → 渲染预览。

## 注意

- 环境依赖按所选技能准备；只使用找达人功能无需配置剪映、ffmpeg或百炼视觉。剪辑相关旧脚本中的机器路径需按各技能说明配置。
- 本仓库不含任何账号凭据；用云端视觉模型时，画面帧会发送到对应服务商。
- `tiktok-dm-outreach` 走浏览器自动化，需要你自己已经登录的 TikTok 会话；
  仓库里不含登录凭据、达人名单、实际话术或佣金；授权的店铺商品名称及图片由独立目录提供。

## 日常用法（clip-naming）

在Codex中说“使用 $clip-naming，开始命名”。未指定产品时先选择磁吸灯、多功能笔、肌理画、多功能锤或新增产品；指定产品就直接加载对应规则。素材位置用接收者自己的当前配置。

旧 `process.command`、`process_inbox.sh`、`name_and_file.py` 尚未接入新的产品选择与全部规则，不作为当前多产品入口直接运行；本次更新的是对话执行规则，未新增桌面程序或后台监控。

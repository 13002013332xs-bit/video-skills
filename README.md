# 视频技能包（Codex Skills）

两个 Codex 技能，用于「照着参考视频剪带货短视频」和「给拍摄素材自动命名分类」。

## 包含什么

| 技能 | 作用 |
|---|---|
| `skills/short-video-production` | 照着一条参考视频剪片：拆解镜头结构 → 从素材库选片 → 输出可在剪映里编辑的草稿 → 渲染预览 |
| `skills/clip-naming` | 看完一整段拍摄素材，按你的命名习惯起名（0–15 字），并自动分到「开头/中间/结尾」 |

## 安装

### 方式一：手动（最简单）

把 `skills/` 下的文件夹放进：

```
~/.codex/skills/
```

然后重启 Codex。

### 方式二：用 Codex 的 skill-installer

让 Codex 从本仓库安装，例如：

```
--repo <owner>/<repo> --path skills/clip-naming
--repo <owner>/<repo> --path skills/short-video-production
```

## 方法论来源

参考视频拆解（五维度）、出片自检协议、批量一致性规则、素材缺口决策这四份参考文档，
思路参考了开源项目 **OpenMontage**（AGPL-3.0，github.com/calesthio/OpenMontage）的做法，
但**内容是按我们自己的流程重写的**（未复制其文件，无许可证传染）。

## 需要准备的环境

**第一次用：先让 Codex 问你几个目录在哪**（素材根目录、剪映草稿目录、capcut-mate 位置），
它会写进 `~/.config/clip-pipeline/config.json`，之后脚本都从这里读，不用改代码：

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
| **百炼 API key（"眼睛"）** | 看懂画面（分镜、选片都靠它） | 见下节 |
| capcut-mate 适配层 | 生成可编辑的剪映草稿 | 见 `references/jianying-draft.md` |
| 剪映专业版 | 最终编辑/导出 | 装剪映 |
| 素材来源 | 你拍的片段（本地文件夹或飞书素材库） | 自己的素材 |

### 配置"眼睛"（必须）

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

- 脚本里的路径是原作者的绝对路径，**换机器要改**（参见每个技能里的说明）。
- 本仓库不含任何账号凭据；用云端视觉模型时，画面帧会发送到对应服务商。

## 日常用法（clip-naming）

```
素材放进：~/Desktop/短视频素材/<日期>/未命名上传/
双击：    skills/clip-naming/scripts/process.command
```

跑完：分类结果在 `<日期>/开头|中间|结尾/`，原片自动移到 `_原片存档/`，确认清单是 `_命名确认清单.md`。

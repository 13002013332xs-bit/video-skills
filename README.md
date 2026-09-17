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

## 需要准备的环境

- `ffmpeg` / `ffprobe`（视频处理）
- `yt-dlp`（下载参考视频）
- Python 3
- **云端视觉模型（推荐）**：阿里云百炼 API-KEY（`sk-` 开头），存到
  `~/.local/opt/clip-naming/dashscope.key`（`chmod 600`）；新用户每个模型送 100 万 token
- **可选本机视觉模型**：`bash skills/clip-naming/scripts/setup_vision.sh`（Apple Silicon，约 2GB）
- **剪映草稿生成**：capcut-mate 的本地适配层 `plan_to_draft.py`（见 `skills/short-video-production/references/jianying-draft.md`）

## 注意

- 脚本里的路径是原作者的绝对路径，**换机器要改**（参见每个技能里的说明）。
- 本仓库不含任何账号凭据；用云端视觉模型时，画面帧会发送到对应服务商。

## 日常用法（clip-naming）

```
素材放进：~/Desktop/短视频素材/<日期>/未命名上传/
双击：    skills/clip-naming/scripts/process.command
```

跑完：分类结果在 `<日期>/开头|中间|结尾/`，原片自动移到 `_原片存档/`，确认清单是 `_命名确认清单.md`。

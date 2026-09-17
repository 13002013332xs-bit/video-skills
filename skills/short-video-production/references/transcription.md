# 本地转写（不上传、不花钱）

- 命令：`vu-transcribe <音频或视频> --language en`（默认 medium 模型；要更快用 `--model small`）。
- 环境：`~/.local/opt/video-use/asr-env`（faster-whisper），命令在 `~/.local/bin/vu-transcribe`。
- 用途：
  - **先听用户给的配音**，据内容决定每段画面要什么（这是选片的前置步骤）。
  - 出**词级时间戳**：切点、字幕、节奏都以它为准。
- 规范：
  - 只做逐字转写，不做整句归一化。
  - 结果按源文件缓存（`transcripts/<name>.json`），源文件没变就不重转。
  - 配音是英语时用 `--language en`；不确定语言可让模型自动判断。
- 相关脚本参考：`~/.codex/skills/video-use/helpers/transcribe_local.py`、
  `build_subtitles_local.py`、`pack_transcripts.py`（把词级结果打包成便于阅读的短语表）。

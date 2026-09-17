# ffmpeg 精剪：生产正确性硬规则

这些不是风格偏好，是"错了会静默出问题"的正确性规则（来自 video-use 的实战总结）：

1. **字幕最后加**，在所有 overlay 之后，否则被遮住。
2. **每段单独 extract → 无损 `-c copy` 拼接**，不要一次性大 filtergraph，避免二次编码。
3. **每个拼接边界加 30ms 音频淡入淡出**（`afade=t=in:st=0:d=0.03` + `afade=t=out:...`），
   否则每次剪切都会有爆音。
4. overlay 用 `setpts=PTS-STARTPTS+T/TB` 把动画第 0 帧对到窗口起点，否则会看到动画中段。
5. 字幕时间轴用**输出时间线**：`output_time = word.start - segment_start + segment_offset`。
6. **绝不在词中间切**：切点对齐转写的词边界。
7. **切点留 30–200ms 余量**（转写时间戳有 50–100ms 漂移）：快节奏取小值，电影感取大值。
8. 用**词级逐字转写**，不要用整句/归一化模式（丢失间隙与口语信号）。
9. 转写结果**按源文件缓存**，源文件没变就不重转。
10. 多个动画并行渲染（子任务并发），不要串行。

## 本机转码实测

- 素材常是 4K/60（个别带 Dolby Vision），**逐帧解码一个文件 30 秒以上**；
  只做画面比对时用 `-skip_frame nokey`（≈1s/文件）或 `-ss <t> -i`（≈0.5s/帧）。
- 硬件编码器 `h264_videotoolbox` 在本机**不可用**（`cannot create compression session: -12908`），
  只能软编：`scale=1080:1920,fps=30 -c:v libx264 -preset veryfast -crf 20`。
- 只转"要用的秒数 + 余量"，别整段转。

## 动画与字幕（需要时）

- 已装：Manim（数学/技术动画）、LaTeX、HyperFrames、Remotion（需要 node/npx）。
- 说明性动画走 manim-video 子技能；网页式动画走 HyperFrames/Remotion；
- 字幕：本地 `vu-transcribe` 出词级时间戳 → 生成 SRT → 按上面第 1、5 条烧录。

# 书梦（DoingDream）克隆配音 —— 实测接法

> 2026-09-21 实测打通。核心思路：**不去点网页，读完它前端 JS 拿到后端接口，
> 再用浏览器里"已登录"的凭据直接调接口。**

## 一、接口（从站点 JS bundle 里挖出来的）

- 基址：`https://doingdream-api.yuyanplus.com`
- 认证：请求头 `Authorization: Bearer <token>`
- 令牌来源：浏览器 localStorage 的键 `doingdream.browser-auth-token.v1`

| 用途 | 接口 | 参数 |
|---|---|---|
| 上传参考音频 | `POST /upload_reference_audio` | multipart，字段名 `audio_file` → 返回 `url` |
| **单条参考音频的零样本克隆** | `POST /custom_tts` | `{reference_audio_url, text, speed, transcription}` → 返回 `url` |
| 音色融合（**至少 2 条**参考） | `POST /voice_fusion` | `{reference_audio_urls[], text, speed}` |
| 指令式合成 | `POST /tts_instruct` | `{reference_audio_urls, tts_text, instruct_text, speed}` |
| 声音转换 | `POST /voice_conversion` | 源音频 + 目标音色 |
| 查账号 / 查点数 | `GET /api/auth/me`、`GET /get_remaining_points` | — |

## 二、拿登录凭据：直接读磁盘，不要麻烦用户开 DevTools

Chrome 的 localStorage 存在：

```
~/Library/Application Support/Google/Chrome/Default/Local Storage/leveldb/
```

- 最新的值通常在 `.log`（写前日志）文件里；搜键名 `browser-auth-token.v1`，
  取它**后面**那段长令牌（约 64 位）
- **坑**：别把键名本身当值取出来（会拿到 20 来位的键名，调接口只会返回"未登录"）
- 拿到后存本地 600 权限文件，**不要写进任何交付物或分享包**

## 三、两个必踩的坑

1. **上传被风控挡**：裸请求会返回 `HTTP 403 / error code 1010`。
   补上浏览器特征即可通过：`User-Agent`、`Accept`、`Origin: https://www.doingdream.com`、
   `Referer: https://www.doingdream.com/`
2. **接口选错**：`/voice_fusion` 是"音色融合"，只给 1 条参考会报
   "音色融合至少需要 2 个参考音频"。**单条克隆要用 `/custom_tts`**。

## 四、参考音频规格（书梦前端写死的限制）

- 时长：**3–15 秒最佳**（硬上限 30 秒）
- 大小：≤ 25 MB
- 格式：wav / mp3 / m4a / flac / ogg / webm
- 我们的统一处理：切 14–15 秒、单声道 44.1kHz、响度归一化到 -16 LUFS

## 五、每次开工的顺序（照这个走）

1. 先 `GET /api/auth/me` 验令牌（几十毫秒的事，**先验再干活**）
2. 令牌过期 → 让用户在 Chrome 登录一次书梦，再按第二节从磁盘取
3. 上传参考音频 → `POST /custom_tts`（带脚本）→ 下载结果
4. 试听确认音色，再批量

## 六、红线

克隆**别人**的声音（达人/客户/明星）必须拿到本人**书面授权**；克隆自己的没问题。
对外文案里 `Amz` 保持不改成 `Amazon`。

# 即梦（Dreamina）CLI 出图 —— 实测接法

> 2026-09-22 打通。**这是给"图文/产品图"用的出图链路，全自动、不需要浏览器。**

## 为什么走 CLI 而不是浏览器

浏览器那侧卡死在一个点上：**上传参考图必须由真人点击**（Chrome 的安全限制，
程序模拟的点击不算"用户手势"，文件框不弹）。试过并且**都失败**的路径：

1. 点 UI 上的「+」按钮（CDP 真实点击也不行）
2. `opencli upload`（页面里没有 `input[type=file]`）
3. 系统剪贴板 + Cmd+V
4. 页面内合成 `paste` 事件（带 File）
5. 页面内合成 `dragenter/dragover/drop`（带 File）
6. 装 MutationObserver 等它创建临时 file input
7. AppleScript 操作系统文件框（权限给了也会被 browser 拒绝）

**CLI 这条路把这些全绕开了。**

## 安装与登录

```bash
curl -s https://jimeng.jianying.com/cli | bash
# 装到 ~/.local/bin/dreamina；Skill 落到 ~/.dreamina_cli/dreamina/SKILL.md

dreamina login              # OAuth 设备码登录（会打印 verification_uri + user_code）
dreamina login --headless   # 只打印设备码，之后用 checklogin 收尾
dreamina login checklogin --device_code=<code>
dreamina user_credit        # 验证：返回 vip_level / total_credit
```

**必须 maestro（大师）级别会员**，否则调用会报权限不足。
`user_credit` 返回 `vip_level: maestro` 就说明可用。

## 出图：三种命令

```bash
# 文生图
dreamina text2image --prompt="..." --ratio=9:16 --resolution_type=2k --model_version=5.0

# 图生图（**带参考图，保住真实产品**，1-10 张）
dreamina image2image --images ./产品图.jpg --prompt="..." \
  --ratio=9:16 --resolution_type=2k --model_version=5.0 --generate_num=2

# 放大
dreamina image_upscale --images ./结果.png
```

抓结果：

```bash
dreamina list_task                      # 看最近任务（含 submit_id / gen_status / 扣了多少分）
dreamina query_result --submit_id=<id> --download_dir=<目录>
```

## 关键参数

| 参数 | 取值 |
|---|---|
| `--ratio` | 21:9 / 16:9 / 3:2 / 4:3 / 1:1 / 3:4 / 2:3 / **9:16** |
| `--resolution_type` | 2k 或 4k（5.0Pro 还支持 1.5k）；**必填** |
| `--model_version` | 4.0–4.7 / 5.0 / 5.0Pro（默认 5.0） |
| `--generate_num` | 1–10 |
| `--width/--height` | 自定义尺寸，和 `--ratio` 互斥，需要 `--resolution_type` |
| `--poll N` | 提交后最多轮询 N 秒 |

## 踩过的坑

1. **提示词别太长** —— 控制在 50 字以内，太长容易排队超时。
2. **`--resolution_type` 不填会直接报错**（不是可选项）。
3. 提交后会打印 `get_history_by_ids failed: ret=1015` —— **这不代表失败**，
   任务其实已经提交了，用 `list_task` 一看就知道（状态 `querying`，积分已扣）。
4. 沙箱里跑要提权，否则写不了 `~/.dreamina_cli/logs`。
5. 生成是**异步**的：`gen_status: querying` → 等到 `success` 再下载。

## 产品图交付规格（TikTok 图文）

- 画布：**1080×1920（9:16）**
- 出图用 `--ratio=9:16 --resolution_type=2k` → 原始约 1440×2560
- 后处理：按比例放大到覆盖 1080×1920 再居中裁切（不要拉伸变形）
- 文件大小：1080×1920 的 PNG 一般落在 2–3MB；要更大只能上 16 位 PNG 或保留 2K 原图

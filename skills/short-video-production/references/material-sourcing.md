# 素材获取（飞书为主）

## 飞书自建应用 + OAuth（只读）

1. `open.feishu.cn` 建**自建应用**，开通 `drive:drive:readonly`（应用身份 + 用户身份都要开）；
   **改权限后必须创建版本并发布**才生效。
2. 用户身份通常比应用身份省事（应用身份还要被加为文件夹协作者，需要文件夹管理权限）。
3. 授权 URL **必须显式带 scope**：

```
https://accounts.feishu.cn/open-apis/authen/v1/authorize
  ?client_id=<APP_ID>
  &redirect_uri=<URL编码回调，如 http://localhost:8080/callback>
  &scope=drive:drive%20wiki:wiki:readonly
  &state=<任意>
```

4. 回调页打不开是正常的（本机没起服务）。**授权码藏在浏览器地址栏变成的 `data:` URL 里的
   `failedUrl` 字符串中**（形如 `...callback?code=XXXX&state=...`）。把它取出来。
5. 换令牌（v2）：

```
POST https://open.feishu.cn/open-apis/authen/v2/oauth/token
{"grant_type":"authorization_code","client_id":...,"client_secret":...,"code":...,"redirect_uri":...}
```

令牌（含 `expires_at`）存本地文件，**2 小时过期**，过期重新走一次授权即可。

## 下载表格里的内嵌素材

- 内嵌视频必须用媒体接口，用 `files/` 会 403：

```
GET /open-apis/drive/v1/medias/{fileToken}/download
Authorization: Bearer <user_access_token>
```

- 步骤：先按行/列清点成清单（行号、列、类别、名字、大小、fileToken）→ 再按名字下载 →
  按 `开头/中间/结尾` 分类落盘，文件名保留原始描述（后面选片全靠它）。

## 现成实现

`<项目>/work/feishu-dl/feishu_media.py`：`inventory` 清点、`download` 批量下载、
`download-one` 单文件下载，全部只读，凭据在同目录 `.env` 与 `.user_token.json`。

## 其它来源

- 用户本地磁盘 / 桌面素材：直接读取，先清点再选，别盲目全量转码。
- 网络素材：yt-dlp；下载后同样按结构分类命名。

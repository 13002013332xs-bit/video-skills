# 剪映草稿：结构、沙盒限制、安全增删

## 素材必须复制进草稿目录

剪映专业版（`/Applications/VideoFusion-macOS.app`）是**沙盒应用**，实测 entitlements：

```
com.apple.security.app-sandbox = true
com.apple.security.assets.movies.read-write = true   # 只额外给了"影片"目录
```

所以草稿引用草稿目录（位于 `~/Movies/JianyingPro/...`）以外的路径，例如 `~/Documents/...`，
剪映读不到 → 时间线显示**素材丢失**。把素材复制进 `<草稿>/assets/video/`、
`<草稿>/assets/audio/` 就正常，草稿也变成自包含、可迁移（每条约几十 MB）。

## 草稿目录结构（macOS）

```
~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/
|-- <草稿名>/
|   |-- draft_content.json      # 轨道、片段、素材引用（主文件）
|   |-- draft_info.json         # 同内容（双写兼容旧版）
|   |-- draft_meta_info.json    # 草稿名、id、路径、时间
|   |-- draft_settings / draft_cover.jpg
|   `-- assets/video|audio/     # 复制进来的素材
`-- root_meta_info.json         # 草稿列表索引：all_draft_store[]
```

`draft_meta_info.json` 的 `draft_name` 才是剪映里显示的名字（可与文件夹名不同）。

## 生成草稿

用 capcut-mate 的本地适配层 `~/Developer/capcut-mate/local/plan_to_draft.py`：

```json
{
  "draft_name": "...", "canvas": {"width":1080,"height":1920,"fps":30},
  "audio": {"path": "...", "start": 0.0, "volume": 1.0},
  "clips": [{"path":"...", "target_start":0.0, "duration":2.8, "source_start":0.4, "volume":0.0}]
}
```

- 主轨片段必须从 0 开始；`source_start` 是"从素材第几秒开始用"，配合比镜位更长的素材，
  用户就能在剪映里往后拉。
- 该脚本依赖 `pymediainfo`（本机没装），但加载后会立刻换成 ffprobe 探测 →
  给它一个空壳模块即可：用 `scripts/run_generator.py` 调用。
- 脚本默认把素材复制进草稿目录（我们要的就是这个行为），重名自动加后缀，不覆盖已有草稿。

## 安全清理旧草稿

1. 先把草稿**移动**到回收目录（如 `<项目>/_回收_XXX_日期/`）。
2. 备份 `root_meta_info.json` 到回收目录。
3. 从 `all_draft_store` 移除 `draft_fold_path` 命中该目录的条目，回写并 `json.load` 验证。
4. 告诉用户回收位置与能否恢复。`all_draft_store` 条数与 `draft_ids` 本来就可能不一致，不要"修齐"。

**注意**：草稿被用户改过名（例如加"改"字）说明他手动编辑过——清理前一定要单独确认。

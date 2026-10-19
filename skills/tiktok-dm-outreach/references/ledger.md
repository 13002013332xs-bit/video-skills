# 结构化建联台账

按任务保存 `outreach-ledger.jsonl`，每条事件一行，立即追加。批次报告由台账生成，不能反过来拿报告覆盖原始事件。

每条最少记录：

| 字段 | 含义 |
|---|---|
| `event_id`, `task_id`, `batch_id` | 唯一事件和批次标识 |
| `timestamp`, `timezone` | 实际时间和时区 |
| `sender` | 现场确认的发送账号 |
| `recipient_input`, `recipient_handle`, `recipient_id` | 输入名、主页核对后的用户名、观察到的 ID；未知填 null |
| `action`, `attempt_no` | dm / follow / like；第几次尝试 |
| `authorization_ref` | 当前任务用户授权出处；重发另记 `resend_authorization_ref` |
| `template_id`, `template_hash` | 当次话术编号、完整实际文案的内容哈希；正文另存在任务私有文件，不写进技能 |
| `status`, `reason` | 下述状态与具体理由 |
| `evidence_ref` | 本次核验文件路径及可定位的信息 |
| `actual_gap_seconds` | 与前一条/前批末条的实际间隔 |

批次另记 `last_dm_attempt_at`、`next_batch_not_before`、时区和本次抽样间隔。关注、点赞、汇报不覆盖末次私信时间；私信重试仍属实际发送动作，更新该时间但不增加独立达人数。下一批允许时刻确定后落盘，恢复时复用；未到时不提前发送。

发送状态：

| 状态 | 使用条件 |
|---|---|
| `planned` | 在当前授权名单中，尚未点击发送 |
| `attempted` | 已执行发送，持久化尚待核验 |
| `persisted_verified` | 重载后目标身份、本次预览/持久化消息与时间吻合 |
| `uncertain` | 页面未加载、列表未渲染、证据不完整等，不能断定成功或失败 |
| `not_persisted` | 重载列表并定向复核后，本次消息仍未保存 |
| `skipped` | 已联系去重、无可用入口、授权不足或超过重试上限等 |

`persisted_verified` 表示网页重载后仍保存，不代表对方已收到或已读。另用 `recipient_event` 记录 `request_accepted`、`seen_receipt`、`replied`，附直接证据和时间。无回执记 `unknown`。

去重需同时查本批、跨批与既有记录：以观察到的收件人 ID 优先，用户名为次，显示名不能作为唯一键；同时记录发送账号和活动。曾成功联系的达人默认跳过，用户明确要求再发才记录重发授权。`attempted` / `uncertain` 先核实，不当作成功，也不盲目重试。

批次汇报只列：计划、已核验保存、未保存、待核验、跳过，各自条数；关注/点赞实际成功数；下一批最早时间或停止原因。不能把“尝试数”列作“已发送数”。

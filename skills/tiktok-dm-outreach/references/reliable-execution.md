# 已有失败案例驱动的执行改进

适用：维护技能、修复已复现故障，或开始/恢复紫鸟邀约。只在涉及的阶段读取；正常连接不重复诊断、不读全量历史。

## 执行方法替换与退役

用户已确认更快且有效的替代方法后，更新当前实现和入口，删除失效分支及默认回退，不能只追加新规则却仍调用旧实现。删除前检查调用者、适用环境和替代方法的现场证据。仅离线通过的新实现不据此删除仍有效的备用方案；替代失败、已验证失效和必须保留的备用方法分别处理，不批量清理旧文件。

| 当前阶段 | 当前采用的方法 | 退出执行入口的方法 |
|---|---|---|
| 页面工具仍绑定旧标签、不能枚举新标签时接入私信 | 从本轮紫鸟窗口读取新标签真实地址，校验店铺后将受控target导航至该地址；新鲜原生标签观察后切回受控标签，检查visible及实际私信弹窗。窗口、地址和target每轮取当前值 | 不带target的page exec反复探测新标签；以旧target结果推断新标签没打开 |
| 汇总邀请收件人 | 读取全部相关分页，核对完整账号集合及实际总数 | 把默认20条当前tbody当成全部名单 |
| 连接已正常的所选店铺 | 合并读取身份、URL及卡片，可用就复用；具体错误才诊断 | 正常轮次无条件重开窗口、整套doctor/登录/端口排查 |
| 私信弹窗已经就绪 | 替换本轮已确认正文，沿用已选可发达人，统一核对后分享一次 | 分享前另查邀请、完成后单人抽查及限额排查 |

第一行是特定页面工具无法绑定新标签时的已验证路径，不排除其他环境中已经实测可用的直接新target绑定。原生工具仍需在当前使用者环境可用；离线替身验证不能当作新使用者现场成功。历史脚本、成功证据及必要备用方法保留用于追溯；只从当前入口移除失效调用，不从故障记录复制旧实现回当前流程。

## 执行入口

筛选完成并进入邀请表单后，复用 `scripts/ziniao_flow.py` 的 `run_invitation`，不复制旧轮整套脚本。每轮只提供自己的配置、状态路径及当前原生页面适配器。筛人仍按现有PPS分流表与本屏集中复核，不改内容判断。

```python
from ziniao_flow import run_invitation

result = run_invitation(
    state_path, confirmation, ui,
    scope=latest_user_scope,
)
```

`latest_user_scope` 来自最新直接用户指令；本轮配置齐全且已授权完整执行时为 `full-round-through-ziniao-message`，不额外索取发送确认。仅修复/技能维护使用 `repair-only`，入口在读取业务页面前返回。已完成或取消的轮次不重新执行。待确认的旧面板不能变成当前轮次授权。

`state_path` 是使用者私有的本轮JSON，不进入共享包；必备 `roundKey/storeKey/stage/namingDate/shopDate/language/batchNumber`。筛选完成、创建邀约页面就绪后将stage设为 `invitation-form`，不能在页面尚未到达时提前写已完成。命名日期从当轮中国日期来源绑定，店铺日期另取；同轮恢复保持已绑定值。`confirmation` 为 `{roundKey, storeKey, config}`，其中config必须为本轮分别确认的message/ziniaoMessage/contentType/provideSamples/sampleMode/products；产品字段与现有面板一致。不在代码中放店铺、产品、话术、佣金或历史日期默认值。

入口连续负责：原生日期路线→连续填其余字段→统一回读核对一次→当前50/页读取全部重叠→按达人集中排除→重开再次50/页核验→统一移动→发送一次→成功后下一页面动作立即进入消息→已确认正文分享一次→完成状态。10与10.00数值等价，真实差值不放行；实际日期未写入不能通过统一核对。状态原子保存，跨调用恢复才重新核对表单，正常连续执行不增加多轮检查。finalAccounts记录本轮最终名单；恢复已解决重叠阶段时核对当前剩余账号及冲突，发消息准备也核对这份账号集合，人数相同不能代替身份相同。消息灰色/限额为正常跳过，不补人、重试或事后单人抽查。

## 原生页面适配器契约

调度代码不附带浏览器控制工具、固定选择器、登录状态或连接端口。`ui` 仅实现当前页面的原生操作和实际读回，不另写流程决策：

| 方法 | 返回/要求 |
|---|---|
| identity() | 当前页面实际店铺映射后的 `{storeKey}`；观察不到不能声称匹配 |
| date_control() | 实际 `{readOnly: bool}` |
| calendar_select(ISO日期) / native_date_input(ISO日期) | 用现场已观察的日历或原生输入，不能JS改值 |
| fill_fields(fields, config) | 连续填名称、正文、按ID定位商品及佣金、内容和样品；邮箱沿用系统、电话留空，不再改日期 |
| form_snapshot() | 实际name/endDate/message/email/phone/contentType/provideSamples/sampleMode/products；产品为id/standardRate/adEnabled/adRate，开关归一为布尔 |
| overlap_summary() | 当前 `{hasConflicts: bool, accounts: [完整账号]}`，accounts是本次全部剩余达人，不能只取可见几行 |
| open_overlaps()/close_overlaps() | 当前重叠窗口原生开/关 |
| read_page_control() | 当前窗口的ready/pageSize/selector/expanded；同ziniao_controls契约 |
| click_page_control(selector)/click_50() | 原生点击当前值标签/50选项；不得读行或移动 |
| read_overlap_page() | `{page, rows, hasNext}`；rows为account/invitationName及可靠invitationDate(ISO)；仅名称MMDD无法可靠确定年份时补看当前已有邀请元数据，不猜 |
| next_overlap_page() | 翻页且按实际条件等该页数据刷新；不得用固定等待充当已刷新 |
| remove_creators(accounts) | 只从本次名单集中删除，保留旧邀请 |
| move_conflicts() | 只移动剩余冲突；出现原生确认则处理当前确认 |
| send_invitation()/invitation_outcome() | 原生发送一次；实际成功页才能返回success，其余不得当成功 |
| open_messages() | 从成功页立即进入向达人发送消息；新标签绑定实际页面，不先查看邀请 |
| prepare_messages(text) | 填确认正文/开关、选可选达人；回读 `{text, enabled, invitationCard, accounts, selectable, disabled, quota?}`，accounts为全部剩余完整账号（含禁用者），不能只按人数判断身份 |
| share_messages()/message_outcome() | 分享一次；用正常流程已有结果返回 `{status: submitted或quota, submitted, skipped}`，两人数相加等于剩余人数；不额外聊天抽查 |

适配器必须按当前原生工具帮助和现场控件实现；未接好就明确当前未完成阶段，不回退到复制旧轮脚本。本次共用入口验证是离线页面替身回放，尚未证明每个使用者环境的原生页面适配器可用，不能说整轮现场验收已完成。

发送或分享前保存pending；调用报错/结果不明时保留该状态，禁止自动重放外发。先核实当前已有结果，再据证据修正原状态并恢复；保存成功不等于对方收到。取消/暂停/仅修复从最新用户指令更新范围，不能靠历史完整执行范围越过当次限制。

## 学习、回归与发布

1. 从已观察的失败建立小型可复现案例；保存修改前结果。规则文字已有但实际调用绕过，也属于失败。
2. 机械规则进共用代码，判断规则留引用；先复现，再最小修改，再用同一场景检验。不能只增加“必须记住”的段落。
3. 有真实选择器/页面依赖时替身只放在原生页面边界，真实状态保存、判断、顺序和计算参与测试。比较完整行为、失败次数和耗时；离线耗时不能当真实达人处理速度。
4. 正常连接/控件能用就立即继续；按可观察状态等待，只对已明确的当前控件错误有界恢复。未知错误保留原现场和失败阶段，不能整套重连重开。
5. 修复只测试受影响阶段及已有回归；通过后同步本机、公开源和分享包。记录具体验证范围，后续已授权正常一轮再确认原生适配，不为验收另发真实私信。

自检：`python3 -m unittest discover -s <技能目录>/tests -v`。这证明共用代码的离线行为；格式校验器只校验技能格式，两者都不冒充现场成功。

## 参考方法

- Anthropic [skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)：真实任务评测、修改前后对照、行为结果和耗时、把重复机械步骤写成脚本。
- [Superpowers](https://github.com/obra/superpowers)：先复现查因、按条件等待、用结果验证完成。本机已有同类技能，重点在实际应用。
- Vercel [agent-browser](https://github.com/vercel-labs/agent-browser)：复用会话及状态、文档匹配工具版本。本技能只吸收方法，未安装替换当前紫鸟控制工具，也未宣称接口兼容。

沿用当前项目指定的唯一操作记忆；不另装一份自我学习记忆目录造成多源冲突。公开文件只保留通用方法和虚构测试数据。

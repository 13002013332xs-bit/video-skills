---
name: tiktok-dm-outreach
description: Use when handling 紫鸟/TikTok达人筛选、PPS卡片评分核验、对话筛选面板、达人建联私信、名单去重、发送核验或回复台账。未给标准时不沿用旧画像；筛选或维护技能不自动授权外发。
metadata:
  short-description: 紫鸟达人筛选、PPS核验、建联与台账
  project: "找达人"
  category: "达人运营"
---

# 找达人项目 · TikTok达人筛选与建联

## 当前唯一流程

紫鸟找达人按[当前主流程](references/creator-workflow.md)执行，版本`2026-11-02-v4`。该文件统一定义范围、模式、PPS分流、同屏筛选、配置填写、冲突循环和收尾；不再从历史规则拼接操作顺序。用户明确纠正直接更新，不重复确认。

开始先按当前使用者的项目AGENTS与指定唯一操作记忆定位当前入口；没有原作者的文件仍可使用本技能，不依赖原作者路径、账号或历史。当前用户明确指令优先；同轮从状态接未完成部分，旧草稿不能覆盖较新指令。

紫鸟接口固定`zn-open-eco agent tool`，复用`scripts/ziniao_agent.py`与有效店铺上下文。正常窗口先接通再交用户设条件，之后保留页面；不全量读历史、不调用旧接口或旧轮包装器。

## 按当前阶段读取资源

| 阶段 | 按需资源 |
|---|---|
| 连接所选店铺与页面 | [ziniao-connection.md](references/ziniao-connection.md) |
| 筛选面板、账号读取、视频复核细节 | [creator-filters.md](references/creator-filters.md)；PPS分流以当前主流程为准 |
| 商品目录、邀约面板与原生控件 | [invite-configuration.md](references/invite-configuration.md) |
| 修复当前异常、共用程序契约 | [reliable-execution.md](references/reliable-execution.md)；正常轮次不全量加载 |
| 独立电脑网页私信 | [execution.md](references/execution.md)，仅当次明确安排时 |
| 独立手机私信 | [phone-outreach.md](references/phone-outreach.md)，仅当次明确安排时 |
| 名单、回复与发送台账 | [ledger.md](references/ledger.md)，不额外给紫鸟收尾增加长台账 |

筛选后的表单与冲突复用`scripts/ziniao_flow.py`和当前原生适配器。仅准备执行到无冲突交接；完整发送才包含成功后立即紫鸟私信。真实异常立即先告知，结果不明保存pending并核实，不能盲重发。

## 店铺选择、面板与分享

用`scripts/build_invite_panel.py --output <当前项目的绝对输出路径>`生成新轮面板，自动加载`assets/store-catalog.json`；同轮恢复才传原`--round-key`。不要展示没有注入目录的底层空白模板。

选择哪个店铺就显示对应商品及真实图片；目录中的泽凡店铺已收录41款商品，辉翔达和待补充店铺由有权限的人同步。共享目录只是带日期快照，不提供店铺登录；连接时从使用者有权访问的实际店铺准确匹配，不猜后台ID。未收录的新店从使用者自己的紫鸟读取自己的商品与图片。

切店清空当前选品、佣金及两份正文；共享商品不预设本轮选择。已确认商品按位置快速定位再用ID核对当前可选状态，不每轮重扫全部目录。

只分享通用方法、空白交互面板与用户明确授权的店铺商品名称/ID/图片/展示价格。凭据、邮箱、真实话术、佣金、轮次名单及机器路径不进入公开包；使用者独立确认自己的配置。

## 维护与验收

调整同时落实到项目主规则、实际程序、唯一操作记忆、本机/开源技能及受影响面板/分享包。被替代的失效方法退出执行和默认检索，重要配置与历史证据保留。

新接口筛选、商品及分批冲突准备已有现场验证；完整邀约发送与紫鸟私信链路仍待完整授权轮现场验收。离线测试不当作现场业务完成，也不为验收额外发送。

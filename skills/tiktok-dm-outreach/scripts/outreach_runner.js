/*
 * 浏览器自动化会话里可直接复用的操作脚本。
 *
 * 用法：把本文件内容粘进浏览器自动化（cua_repl）会话，先设置下面 T（话术正文）和 jobs（本批名单），
 * 再执行循环。变量 c 是浏览器应用绑定：`c = await cua.getApp("Google Chrome", { emit: false })`。
 *
 * 设计要点：
 * - 每批只放 3–4 个达人：工具调用有 5 分钟上限，放多了会被截断、日志丢失。
 * - 每次动作后重新读无障碍树，不复用旧的元素编号。
 * - 关注/点赞前先读状态，避免点成取关或取消赞。
 * - 返回值里的「已发送」只有在输入框被清空时才成立。
 */

// 1) 话术正文：键是版本号，值是正文（不含个性化开场白）
const T = {
  1: "<话术 1 正文>",
  2: "<话术 2 正文>",
  3: "<话术 3 正文>",
  4: "<话术 4 正文>",
  5: "<话术 5 正文>"
};

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function getL() {
  return (await c.getAXState({ emit: false, disableDiffing: true })).split("\n");
}
async function navWait(url, ms) {
  await c.pressKey("super+l");
  await c.paste(url, { format: "text" });
  await c.pressKey("Return");
  await sleep(ms || 6000);
  return await getL();
}
function idx(L, re) {
  const l = L.find(x => re.test(x));
  return l ? parseInt(l.trim().split(/\s+/)[0], 10) : null;
}
function firstVideo(L) {
  return L.map(x => (x.match(/Value: (tiktok\.com\/@[A-Za-z0-9._]+\/video\/\d+)/) || [])[1]).find(Boolean);
}

async function likeUser(user) {
  let L = await navWait("https://www.tiktok.com/@" + user, 7000);
  let v = firstVideo(L);
  if (!v) { L = await navWait("https://www.tiktok.com/@" + user, 7500); v = firstVideo(L); }
  if (!v) return "拿不到视频";
  L = await navWait(v, 7000);
  const li = idx(L, /切换按钮 点赞视频/);
  if (li === null) return "没有点赞按钮";
  if (/Value: 1/.test(L.find(x => /切换按钮 点赞视频/.test(x)) || "")) return "已经是点赞状态";
  await c.click(li);
  await sleep(2000);
  const a = (await getL()).filter(x => /切换按钮 点赞视频/.test(x))[0] || "";
  return /Value: 1/.test(a) ? "已点赞" : "点赞未确认";
}

async function followUser(user) {
  let L = await navWait("https://www.tiktok.com/@" + user, 7000);
  let fi = idx(L, /按钮 关注 /);
  if (fi === null) { L = await navWait("https://www.tiktok.com/@" + user, 7500); fi = idx(L, /按钮 关注 /); }
  if (fi === null) return "无关注按钮(可能已关注)";
  await c.click(fi);
  await sleep(1800);
  return (await getL()).some(x => /已关注/.test(x)) ? "已关注" : "关注未确认";
}

async function sendDM(user, tpl, opener) {
  let L = await navWait("https://www.tiktok.com/@" + user, 7000);
  let mi = idx(L, /link 消息, Value: tiktok\.com\/messages/);
  if (mi === null) { L = await navWait("https://www.tiktok.com/@" + user, 7500); mi = idx(L, /link 消息, Value: tiktok\.com\/messages/); }
  if (mi === null) return "没有私信入口";
  await c.click(mi);
  await sleep(4000);
  let L2 = await getL();
  let ci = idx(L2, /文本输入区 .*(发送消息|Send a message)/);
  if (ci === null) { await sleep(3500); L2 = await getL(); ci = idx(L2, /文本输入区 .*(发送消息|Send a message)/); }
  if (ci === null) return "没找到输入框";
  await c.click(ci);
  await c.paste(opener + "\n\n" + T[tpl], { format: "text" });
  await sleep(1500);
  const si = idx(await getL(), /按钮 (发送|Send)/);
  if (si === null) return "没找到发送按钮";
  await c.click(si);
  await sleep(2500);
  const L4 = await getL();
  const cleared = /Value:\s*$/.test(L4.find(x => /文本输入区/.test(x)) || "x");
  return (cleared ? "已发送" : "发送未确认") + "(话术" + tpl + ")";
}

// 2) 本批名单：follow / like 标记这一批轮到他做哪个动作（每批至少 2 关注、3 点赞，且不重复）
const jobs = [
  { u: "<用户名A>", opener: "<个性化开场白 A>", follow: true },
  { u: "<用户名B>", opener: "<个性化开场白 B>", like: true },
  { u: "<用户名C>", opener: "<个性化开场白 C>" }
];

// 3) 执行：话术随机且不与上一条重复
let lastTpl = 0;
for (const j of jobs) {
  const parts = [];
  if (j.follow) parts.push("关注:" + await followUser(j.u));
  if (j.like) parts.push("点赞:" + await likeUser(j.u));
  let tpl;
  do { tpl = 1 + Math.floor(Math.random() * 5); } while (tpl === lastTpl);
  const r = await sendDM(j.u, tpl, j.opener);
  parts.push("私信:" + r);
  if (/已发送/.test(r)) lastTpl = tpl;
  nodeRepl.write(j.u + " → " + parts.join(" | ") + "\n");
  await sleep(20000 + Math.floor(Math.random() * 18000)); // 20–40 秒随机
}
nodeRepl.write("本批完成\n");

import { existsSync } from "node:fs";
import { chromium } from "playwright-core";

const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const webUrl = process.env.WEB_URL || "http://127.0.0.1:5173/";
const browser = await chromium.launch(
  existsSync(chromePath) ? { executablePath: chromePath, headless: true } : { headless: true },
);

const page = await browser.newPage({ viewport: { width: 1440, height: 1024 } });
const browserErrors = [];
page.on("console", (message) => {
  if (message.type() === "error") browserErrors.push(message.text());
});
page.on("pageerror", (error) => browserErrors.push(error.message));
await page.goto(webUrl, { waitUntil: "networkidle" });

await page.getByRole("heading", { name: "鱼盆趋势雷达" }).waitFor();
const dateLedger = page.locator(".date-ledger");
await dateLedger.getByText("文章", { exact: true }).waitFor();
await dateLedger.getByText("2026-07-21", { exact: true }).waitFor();
await dateLedger.getByText("指数", { exact: true }).waitFor();
await dateLedger.getByText("板块", { exact: true }).waitFor();
if ((await dateLedger.getByText("2026-07-20", { exact: true }).count()) !== 2) {
  throw new Error("Index and sector data dates should both be visible");
}
await page.getByText(/主攻恢复为中证消费/).waitFor();
await page.getByRole("heading", { name: "1 个主攻方向" }).waitFor();
await page.getByRole("heading", { name: "趋势方向雷达" }).waitFor();
if ((await page.locator("[data-testid='focus-groups'] .radar-group").count()) !== 4) {
  throw new Error("Actionable states should stay in the four-column focus area");
}
const avoidGroup = page.locator("[data-testid='avoid-group']");
if ((await avoidGroup.locator(".direction-row").count()) !== 6) {
  throw new Error("Avoid group should show six directions before expansion");
}
const expandAvoidButton = avoidGroup.getByRole("button", { name: /查看全部 \d+ 个/ });
const avoidCount = Number((await expandAvoidButton.textContent()).match(/\d+/)?.[0]);
await expandAvoidButton.click();
if ((await avoidGroup.locator(".direction-row").count()) !== avoidCount) {
  throw new Error("Avoid group should expose every direction after expansion");
}
const avoidOverflow = await avoidGroup.locator(".direction-list").evaluate(
  (element) => getComputedStyle(element).overflowY,
);
if (avoidOverflow === "auto" || avoidOverflow === "scroll") {
  throw new Error("Avoid group should use page scrolling instead of nested scrolling");
}
await page.getByRole("button", { name: /中证消费/ }).click();
const detail = page.locator("[data-testid='direction-detail']");
await detail.getByRole("heading", { name: "中证消费" }).waitFor();
await detail.locator(".group-label").getByText("主攻", { exact: true }).waitFor();
await detail.locator(".group-label").getByText("可关注", { exact: true }).waitFor();
await detail.locator(".metric-strip").getByText("第 1 名", { exact: true }).waitFor();
await detail.getByText("较 2026-07-17 持平", { exact: true }).waitFor();
await detail.getByText("量比 1.26", { exact: true }).waitFor();
await detail.getByText("中证A500", { exact: true }).waitFor();
await detail.getByText(/偏离率若升至8%以上则不追高/).waitFor();
const history = detail.locator("[data-testid='direction-history']");
await history.getByRole("heading", { name: "最近 5 次状态" }).waitFor();
await history.getByText("2026-07-13", { exact: true }).waitFor();
await history.getByText("2026-07-15", { exact: true }).waitFor();
await history.getByText("2026-07-17", { exact: true }).waitFor();
await history.getByText("2026-07-20", { exact: true }).waitFor();
await history.getByText("主攻", { exact: true }).first().waitFor();
const evidenceImage = detail.getByRole("img", { name: /板块鱼盆原始表格/ });
await evidenceImage.waitFor();
if ((await evidenceImage.evaluate((image) => image.naturalWidth)) === 0) {
  throw new Error("Fish-table evidence image should load");
}

await page.getByRole("button", { name: /半导体/ }).click();
await detail.getByRole("heading", { name: "半导体" }).waitFor();
await detail.locator(".group-label").getByText("回避", { exact: true }).waitFor();
await detail.locator(".metric-strip").getByText("第 14 名", { exact: true }).waitFor();
await detail.getByText("较 2026-07-17 持平", { exact: true }).waitFor();
await detail.getByText("-26.05%", { exact: true }).waitFor();

const mobilePage = await browser.newPage({ viewport: { width: 390, height: 844 } });
await mobilePage.goto(webUrl, { waitUntil: "networkidle" });
await mobilePage.getByRole("heading", { name: "鱼盆趋势雷达" }).waitFor();
const hasHorizontalOverflow = await mobilePage.evaluate(
  () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
);
if (hasHorizontalOverflow) {
  throw new Error("Mobile layout should not overflow horizontally");
}
await mobilePage.getByRole("button", { name: /中证消费/ }).click();
await mobilePage.waitForFunction(
  () => {
    const element = document.querySelector("[data-testid='direction-detail']");
    const top = element?.getBoundingClientRect().top;
    return typeof top === "number" && top >= 0 && top < window.innerHeight;
  },
  undefined,
  { timeout: 5000 },
);
const mobileDetailBox = await mobilePage.locator("[data-testid='direction-detail']").boundingBox();
if (!mobileDetailBox || mobileDetailBox.y < 0 || mobileDetailBox.y >= 844) {
  throw new Error("Selecting a direction on mobile should bring its detail into view");
}

const errorContext = await browser.newContext();
let snapshotRequests = 0;
await errorContext.route("**/data/project-snapshot.json", (route) => {
  snapshotRequests += 1;
  if (snapshotRequests === 1) {
    return route.fulfill({ status: 503, contentType: "application/json", body: "{}" });
  }
  return route.continue();
});
const errorPage = await errorContext.newPage();
await errorPage.goto(webUrl);
await errorPage.getByText("项目快照不可用", { exact: true }).waitFor();
await errorPage.getByText("读取失败（503）", { exact: true }).waitFor();
await errorPage.getByRole("button", { name: "重试" }).click();
await errorPage.getByRole("heading", { name: "鱼盆趋势雷达" }).waitFor();
await errorContext.close();

if (browserErrors.length) {
  throw new Error(`Browser console errors: ${browserErrors.join(" | ")}`);
}

await browser.close();
console.log("Smoke check passed");

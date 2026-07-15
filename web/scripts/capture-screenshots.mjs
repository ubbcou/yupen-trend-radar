import { existsSync, mkdirSync } from "node:fs";
import { chromium } from "playwright-core";

const root = new URL("..", import.meta.url);
const outputDir = new URL("screenshots/", root);
mkdirSync(outputDir, { recursive: true });

const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const launchOptions = existsSync(chromePath)
  ? { executablePath: chromePath, headless: true }
  : { headless: true };

const browser = await chromium.launch(launchOptions);

const desktop = await browser.newPage({
  viewport: { width: 1440, height: 1024 },
  deviceScaleFactor: 1,
});
await desktop.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
await desktop.screenshot({
  path: new URL("desktop-1440.png", outputDir).pathname,
  fullPage: false,
});

const mobile = await browser.newPage({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 1,
  isMobile: true,
});
await mobile.goto("http://127.0.0.1:5173/", { waitUntil: "networkidle" });
await mobile.screenshot({
  path: new URL("mobile-390.png", outputDir).pathname,
  fullPage: false,
});

await browser.close();

console.log("Captured screenshots in web/screenshots");

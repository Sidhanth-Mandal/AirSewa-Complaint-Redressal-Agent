// Browser smoke test of the wow-moment: post on the simulator (left), see PACR detect it (right) in < 2 s.
// Run with the app up:  node e2e/demo.mjs   (requires `npm i playwright` + `npx playwright install chromium` in e2e/)
import { chromium } from "playwright";

const BASE = process.env.BASE || "http://localhost:3000";
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1500, height: 950 } });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
page.on("console", (m) => m.type() === "error" && errors.push("console: " + m.text()));

await page.goto(BASE + "/demo");
await page.getByRole("button", { name: /Log in as demo agent/ }).click();
await page.getByText("PACR Live Social Feed").first().waitFor();
await page.waitForTimeout(1500);

const tag = "T" + Math.floor(Math.random() * 90000 + 10000);
const text = `@IndiGo6E flight 6E 981 DEL-BOM delayed 4 hours, my father's medicine is in the bag and no water. PNR ZK45LM #AirSewa ref${tag}`;
await page.getByLabel("Log in as").selectOption("@techie_arjun");
await page.getByLabel(/What's happening/).fill(text);
const t0 = Date.now();
await page.getByRole("button", { name: "Post", exact: true }).click();
const row = page.locator("li", { hasText: tag }).first();
await row.waitFor({ timeout: 5000 });
const dt = Date.now() - t0;
console.log("post -> detected row visible in", dt, "ms");
await page.screenshot({ path: "e2e/demo.png" });
console.log((await row.innerText()).replace(/\n/g, " | ").slice(0, 400));
console.log("errors:", errors.length ? errors : "none");
await browser.close();
process.exit(dt < 2000 && errors.length === 0 ? 0 : 1);

// Captures screenshots of every screen for docs/FEATURES.md. Run with the app up: node shots.mjs (from e2e/)
import { chromium } from "playwright";
import fs from "fs";

const BASE = process.env.BASE || "http://localhost:3000";
const OUT = "../docs/screenshots";
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const errors = [];

async function ctx(w = 1440, h = 900) {
  const c = await browser.newContext({ viewport: { width: w, height: h } });
  await c.addInitScript(() => {
    const add = () => { const s = document.createElement("style"); s.textContent = "nextjs-portal{display:none!important}"; document.documentElement.appendChild(s); };
    if (document.documentElement) add(); else document.addEventListener("DOMContentLoaded", add);
  });
  const p = await c.newPage();
  p.on("pageerror", (e) => errors.push(e.message));
  return p;
}
async function pwLogin(p, user) {
  await p.goto(BASE + "/login");
  await p.getByRole("tab", { name: /Password/ }).click();
  await p.getByLabel(/Mobile number or e-mail/).fill(user);
  await p.getByLabel(/^Password/).fill("Demo@1234");
  await p.getByRole("button", { name: "Login", exact: true }).last().click();
  await p.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 15000 });
  await p.waitForLoadState("networkidle").catch(() => {});
}
async function shot(p, name, path, { full = false, wait = 1800, action } = {}) {
  if (path) await p.goto(BASE + path);
  await p.waitForLoadState("networkidle").catch(() => {});
  await p.waitForTimeout(wait);
  if (action) await action();
  await p.screenshot({ path: `${OUT}/${name}.png`, fullPage: full });
  console.log("ok", name);
}
const safe = async (name, fn) => { try { await fn(); } catch (e) { console.log("FAIL", name, e.message.split("\n")[0]); } };

// ---------- public / passenger ----------
let p = await ctx();
await safe("home", () => shot(p, "01-home", "/"));
await safe("login", () => shot(p, "02-login", "/login"));
await safe("register", () => shot(p, "03-register", "/register", { full: true }));
await safe("track", () => shot(p, "04-track-flight", "/track"));

await safe("pax-login", async () => {
  await p.goto(BASE + "/login");
  await p.getByLabel(/Mobile number or e-mail/).fill("9000000001");
  await p.getByRole("button", { name: /Send OTP/ }).click();
  await p.waitForTimeout(800);
  await p.screenshot({ path: `${OUT}/02b-login-otp.png` });
  await p.getByRole("button", { name: /Verify/ }).click();
  await p.waitForURL("**/passenger");
});
await safe("pax-dash", () => shot(p, "05-passenger-dashboard", "/passenger", { full: true }));
await safe("pax-new", async () => {
  await p.goto(BASE + "/passenger/new");
  await p.getByLabel(/^Airline/).selectOption({ label: "Air India" });
  await p.getByLabel(/Service Request Number/).fill("SR" + Math.floor(Math.random() * 1e8));
  await p.getByLabel(/Date & time/).fill("2026-10-28T10:30");
  await p.getByLabel(/Describe your grievance/).fill("Air India lost my baggage and it contains my father's medicine. Urgent help needed at the airport.");
  await p.getByText(/Detected:/).waitFor();
  await p.waitForTimeout(500);
  await p.screenshot({ path: `${OUT}/06-grievance-form.png`, fullPage: true });
  await p.getByLabel(/privacy notice/).check();
  await p.getByRole("button", { name: "Submit grievance" }).click();
  await p.getByTestId("ticket-id").waitFor();
  await p.waitForTimeout(500);
  await p.screenshot({ path: `${OUT}/07-grievance-submitted.png` });
  const id = (await p.getByTestId("ticket-id").innerText()).trim();
  fs.writeFileSync("./tmp-ticket.txt", id);
  await shot(p, "08-ticket-passenger-view", "/tickets/" + id, { full: true });
});
await safe("chatbot", async () => {
  await p.goto(BASE + "/passenger");
  await p.waitForTimeout(1200);
  await p.getByLabel("Open assistant chat").click();
  await p.getByLabel("Message").fill("My baggage is lost, what should I do?");
  await p.getByLabel("Message").press("Enter");
  await p.waitForTimeout(1500);
  await p.screenshot({ path: `${OUT}/09-chatbot.png` });
});
await p.context().close();

// ---------- redressor / nodal ----------
p = await ctx();
await safe("l2", async () => {
  await pwLogin(p, "ai.l2@demo.in");
  await shot(p, "10-redressor-queue", "/redressor", { full: true });
  const ticket = fs.readFileSync("./tmp-ticket.txt", "utf8");
  await shot(p, "11-ticket-detail-staff", "/tickets/" + ticket, { full: true });
  await shot(p, "12-redressor-performance", "/redressor/performance", { full: true });
});
await p.context().close();
p = await ctx();
await safe("nodal", async () => {
  await pwLogin(p, "nodal.ai@demo.in");
  await shot(p, "13-nodal-queue", "/redressor", { full: true });
  await shot(p, "14-nodal-staff", "/redressor/staff", { full: true });
});
await p.context().close();

// ---------- agent (PACR) ----------
p = await ctx();
await safe("agent", async () => {
  await pwLogin(p, "agent1@pacr.demo");
  await shot(p, "15-agent-home", "/agent", { full: true });
  await shot(p, "16-agent-tickets", "/agent/tickets", { full: true });
  await shot(p, "17-agent-social-feed", "/agent/social", { full: true });
  await shot(p, "18-agent-channels", "/agent/channels", { full: true });
  await shot(p, "19-agent-closure-committee", "/agent/closure", { full: true });
});
await p.context().close();

// ---------- manager ----------
p = await ctx();
await safe("manager", async () => {
  await pwLogin(p, "manager@pacr.demo");
  await shot(p, "20-control-room", "/manager", { full: true });
});
await p.context().close();

// ---------- admin ----------
p = await ctx(1500, 1000);
await safe("admin", async () => {
  await pwLogin(p, "admin@moca.demo");
  await p.getByText("Total grievances").waitFor();
  await p.waitForTimeout(1500);
  await p.screenshot({ path: `${OUT}/21-dashboard-overview.png`, fullPage: true });
  for (const [t, f] of [["SLA & performance", "22-dashboard-sla"], ["Geography", "23-dashboard-geography"], ["Social Media Pulse", "24-dashboard-social"], ["Predictive", "25-dashboard-predictive"]]) {
    await safe(t, async () => {
      await p.getByRole("tab", { name: t }).click();
      await p.waitForTimeout(1200);
      await p.screenshot({ path: `${OUT}/${f}.png`, fullPage: true });
      console.log("ok", f);
    });
  }
  await shot(p, "26-admin-rules", "/admin/rules", { full: true });
  await shot(p, "27-admin-sla", "/admin/sla", { full: true });
  await shot(p, "28-admin-watchlist", "/admin/watchlist", { full: true });
  await shot(p, "29-admin-clock", "/admin/clock", { full: true });
  await shot(p, "30-admin-users", "/admin/users", { full: true });
  await shot(p, "31-admin-settings", "/admin/settings", { full: true });
  await shot(p, "32-admin-audit", "/admin/audit", { full: true });
  await shot(p, "33-admin-api-sandbox", "/admin/api", { full: true });
});
await p.context().close();

// ---------- simulators ----------
p = await ctx(1500, 950);
await safe("sim", async () => {
  await shot(p, "34-simulator", "/simulator", { full: true });
  await shot(p, "36-crm-webhook", "/crm", { full: true });
});
await safe("demo", async () => {
  await p.goto(BASE + "/demo");
  await p.getByRole("button", { name: /Log in as demo agent/ }).click();
  await p.getByText("PACR Live Social Feed").first().waitFor();
  await p.waitForTimeout(1500);
  const tag = "T" + Math.floor(Math.random() * 90000 + 10000);
  await p.getByLabel("Log in as").selectOption("@techie_arjun");
  await p.getByLabel(/What's happening/).fill(`@IndiGo6E flight 6E 981 DEL-BOM delayed 4 hours, my father's medicine is in the bag and no water. PNR ZK45LM #AirSewa ref${tag}`);
  await p.getByRole("button", { name: "Post", exact: true }).click();
  await p.locator("li", { hasText: tag }).first().waitFor({ timeout: 6000 });
  await p.waitForTimeout(1500);
  await p.screenshot({ path: `${OUT}/35-demo-split-screen.png` });
});
await p.context().close();

console.log("errors", errors.length ? errors : "none");
await browser.close();

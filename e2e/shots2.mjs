// Re-captures very tall pages at viewport height for docs/FEATURES.md
import { chromium } from "playwright";
const BASE = "http://localhost:3000", OUT = "../docs/screenshots";
const b = await chromium.launch();
async function page(user) {
  const c = await b.newContext({ viewport: { width: 1440, height: 900 } });
  await c.addInitScript(() => { const a = () => { const s = document.createElement("style"); s.textContent = "nextjs-portal{display:none!important}"; document.documentElement.appendChild(s); }; document.documentElement ? a() : document.addEventListener("DOMContentLoaded", a); });
  const p = await c.newPage();
  if (user) {
    await p.goto(BASE + "/login"); await p.getByRole("tab", { name: /Password/ }).click();
    await p.getByLabel(/Mobile number or e-mail/).fill(user); await p.getByLabel(/^Password/).fill("Demo@1234");
    await p.getByRole("button", { name: "Login", exact: true }).last().click();
    await p.waitForURL((u) => !u.pathname.startsWith("/login"));
  }
  return p;
}
let p = await page("agent1@pacr.demo");
await p.goto(BASE + "/agent"); await p.waitForTimeout(2500); await p.screenshot({ path: `${OUT}/15-agent-home.png` }); await p.goto(BASE + "/agent/social"); await p.waitForTimeout(2500); await p.screenshot({ path: `${OUT}/17-agent-social-feed.png` });
p = await page("admin@moca.demo");
await p.goto(BASE + "/admin/users"); await p.waitForTimeout(2000); await p.screenshot({ path: `${OUT}/30-admin-users.png` });
await p.goto(BASE + "/admin/audit"); await p.waitForTimeout(2000); await p.screenshot({ path: `${OUT}/32-admin-audit.png` });
p = await page();
await p.goto(BASE + "/simulator"); await p.waitForTimeout(2500); await p.screenshot({ path: `${OUT}/34-simulator.png` });
await b.close();


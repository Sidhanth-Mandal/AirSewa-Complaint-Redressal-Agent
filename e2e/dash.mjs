import { chromium } from "playwright";
const b = await chromium.launch(); const p = await (await b.newContext({ viewport: { width: 1500, height: 1100 } })).newPage();
const errs=[]; p.on("pageerror", e => errs.push(e.message)); p.on("console", m => m.type()==="error" && errs.push(m.text().slice(0,150)));
await p.goto("http://localhost:3000/login"); await p.getByRole("tab",{name:/Password/}).click();
await p.getByLabel(/Mobile number or e-mail/).fill("admin@moca.demo"); await p.getByLabel(/^Password/).fill("Demo@1234"); await p.getByRole("button",{name:"Login",exact:true}).last().click();
await p.waitForURL("**/admin"); await p.getByText("Total grievances").waitFor(); await p.waitForTimeout(1500);
await p.screenshot({path:"dash.png"});
for (const t of ["SLA & performance","Geography","Social Media Pulse","Predictive"]) { await p.getByRole("tab",{name:t}).click(); await p.waitForTimeout(700); }
await p.screenshot({path:"dash2.png"});
console.log("errors", errs.length? errs: "none"); await b.close();

// Browser smoke test: passenger OTP login -> file grievance -> redressor sees it -> admin fast-forwards clock.
import { chromium } from "playwright";
const BASE = process.env.BASE || "http://localhost:3000";
const browser = await chromium.launch();
const errors = [];
const mk = async () => { const c = await browser.newContext({ viewport: { width: 1300, height: 900 } }); const p = await c.newPage(); p.on("pageerror", (e) => errors.push(e.message)); return p; };

const pax = await mk();
await pax.goto(BASE + "/login");
await pax.getByLabel(/Mobile number or e-mail/).fill("9000000001");
await pax.getByRole("button", { name: /Send OTP/ }).click();
await pax.getByRole("button", { name: /Verify/ }).click();
await pax.waitForURL("**/passenger");
await pax.goto(BASE + "/passenger/new");
await pax.getByLabel(/^Airline/).selectOption({ label: "Air India" });
const srn = "SR" + Math.floor(Math.random() * 1e8);
await pax.getByLabel(/Service Request Number/).fill(srn);
await pax.getByLabel(/Service Request Number/).blur();
await pax.getByLabel(/Date & time/).fill("2026-10-28T10:30");
await pax.getByLabel(/Describe your grievance/).fill("Air India lost my baggage and it contains my father's medicine. Urgent help needed at the airport.");
await pax.getByText(/Detected:/).waitFor();
await pax.getByLabel(/privacy notice/).check();
await pax.getByRole("button", { name: "Submit grievance" }).click();
const id = (await pax.getByTestId("ticket-id").innerText()).trim();
console.log("ticket", id, "|", (await pax.getByText(/Routed to|routedTo/).first().innerText()).slice(0, 120));
await pax.screenshot({ path: "portal-success.png" });

const red = await mk();
await red.goto(BASE + "/login");
await red.getByRole("tab", { name: /Password/ }).click();
await red.getByLabel(/Mobile number or e-mail/).fill("ai.l2@demo.in");
await red.getByLabel(/^Password/).fill("Demo@1234");
await red.getByRole("button", { name: "Login", exact: true }).last().click();
await red.waitForURL("**/redressor");
await red.getByText(id).first().waitFor({ timeout: 8000 });
console.log("redressor L2 queue shows", id);
await red.goto(BASE + "/tickets/" + id);
await red.getByText(/Why this priority/).waitFor();
await red.screenshot({ path: "ticket-detail.png" });

console.log("errors:", errors.length ? errors : "none");
await browser.close();
process.exit(errors.length ? 1 : 0);

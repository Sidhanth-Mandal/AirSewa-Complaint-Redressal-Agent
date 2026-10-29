// One-command runner: `npm run dev` -> sets up venv + deps + seed (first run), then starts FastAPI (8000) and Next.js (3000).
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const api = join(root, "api");
const web = join(root, "web");
const win = process.platform === "win32";
const venvPy = win ? join(api, ".venv", "Scripts", "python.exe") : join(api, ".venv", "bin", "python");
const args = process.argv.slice(2);
const npm = win ? "npm.cmd" : "npm";

function run(cmd, a, cwd, opts = {}) {
  const r = spawnSync(cmd, a, { cwd, stdio: "inherit", shell: win && cmd.endsWith(".cmd"), ...opts });
  if (r.status !== 0) { console.error(`\n[airsewa] command failed: ${cmd} ${a.join(" ")}`); process.exit(r.status ?? 1); }
}

if (!existsSync(venvPy)) {
  console.log("[airsewa] creating Python virtualenv ...");
  const py = win ? "python" : "python3";
  run(py, ["-m", "venv", ".venv"], api);
  run(venvPy, ["-m", "pip", "install", "-q", "-r", "requirements.txt"], api);
}
if (!existsSync(join(web, "node_modules"))) {
  console.log("[airsewa] installing web dependencies ...");
  run(npm, ["install", "--no-audit", "--no-fund"], web);
}
if (args.includes("--seed-only") || !existsSync(join(api, "airsewa.db"))) {
  console.log("[airsewa] seeding database (~3,000 tickets + ~300 simulated social posts) ...");
  run(venvPy, ["seed.py"], api);
}
if (args.includes("--setup-only") || args.includes("--seed-only")) process.exit(0);
if (args.includes("--test")) { run(venvPy, ["-m", "pytest", "-q"], api); process.exit(0); }

const procs = [
  spawn(venvPy, ["-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"], { cwd: api, stdio: "inherit" }),
  spawn(npm, ["run", "dev"], { cwd: web, stdio: "inherit", shell: win }),
];
console.log("\n[airsewa] API  -> http://localhost:8000/docs   |   Web -> http://localhost:3000\n");
const stop = () => procs.forEach((p) => { try { p.kill(); } catch {} });
process.on("SIGINT", () => { stop(); process.exit(0); });
process.on("exit", stop);
procs.forEach((p) => p.on("exit", (c) => { if (c) { console.error("[airsewa] a process exited with code", c); stop(); process.exit(c); } }));

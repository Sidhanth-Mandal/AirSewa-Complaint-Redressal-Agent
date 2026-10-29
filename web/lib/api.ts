export class ApiError extends Error {
  status: number;
  detail: any;
  constructor(status: number, detail: any) {
    super(typeof detail === "string" ? detail : detail?.message || JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: any; form?: FormData } = {}): Promise<T> {
  const init: RequestInit = { method: opts.method || (opts.body || opts.form ? "POST" : "GET"), credentials: "include", headers: {} };
  if (opts.form) init.body = opts.form;
  else if (opts.body !== undefined) {
    (init.headers as any)["Content-Type"] = "application/json";
    init.body = JSON.stringify(opts.body);
  }
  const r = await fetch("/api" + path, init);
  if (!r.ok) {
    let d: any = r.statusText;
    try {
      const j = await r.json();
      d = j.detail ?? j;
      if (Array.isArray(d)) d = { message: d.map((x: any) => `${(x.loc || []).slice(1).join(".")}: ${x.msg}`).join("; "), fields: d.map((x: any) => (x.loc || []).slice(-1)[0]) };
    } catch {}
    throw new ApiError(r.status, d);
  }
  const ct = r.headers.get("content-type") || "";
  return (ct.includes("json") ? r.json() : r.blob()) as any;
}

export const qs = (o: Record<string, any>) => {
  const p = new URLSearchParams();
  Object.entries(o).forEach(([k, v]) => v !== undefined && v !== null && v !== "" && p.set(k, String(v)));
  const s = p.toString();
  return s ? "?" + s : "";
};

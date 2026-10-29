"use client";
import { useCallback, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Input, Simulated, useToast } from "@/components/ui";
import { api } from "@/lib/api";

export default function ApiSandbox() {
  const { push } = useToast();
  const [keys, setKeys] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [fresh, setFresh] = useState("");
  const [tryKey, setTryKey] = useState("");
  const [tryNo, setTryNo] = useState("AS-2026-000001");
  const [out, setOut] = useState("");
  const load = useCallback(() => api("/admin/api-keys").then(setKeys), []);
  useEffect(() => { load(); }, [load]);
  async function call() {
    const r = await fetch(`/api/v1/tickets/${tryNo}`, { headers: { "X-API-Key": tryKey } });
    setOut(`HTTP ${r.status}\n` + JSON.stringify(await r.json(), null, 2));
    load();
  }
  return (
    <Shell roles={["admin"]}>
      <div className="mb-2 flex items-center gap-2"><h1 className="text-2xl font-bold text-navy">API ecosystem - developer sandbox</h1><Simulated /></div>
      <p className="mb-3 text-sm text-slate-600">Versioned REST API (<code>/v1</code>) with API-key auth (keys issued only by the administrator), rate limit (30 requests/min/key), usage counters and OpenAPI docs at <a className="text-navy underline" href="http://localhost:8000/docs" target="_blank">localhost:8000/docs</a>. Sandbox returns dummy data only.</p>
      <div className="grid gap-4 md:grid-cols-2">
        <Card><CardHeader><CardTitle className="text-base">Issue key</CardTitle></CardHeader><CardBody className="space-y-2">
          <Input aria-label="Key name" placeholder="Integration name (e.g. Airline CRM)" value={name} onChange={(e) => setName(e.target.value)} />
          <Button disabled={!name} onClick={() => api("/admin/api-keys", { body: { name } }).then((r) => { setFresh(r.key); setTryKey(r.key); setName(""); load(); push("Key issued - copy it now", "success"); })}>Issue API key</Button>
          {fresh && <p className="break-all rounded bg-amber-50 p-2 font-mono text-xs">{fresh}</p>}
        </CardBody></Card>
        <Card><CardHeader><CardTitle className="text-base">Try the API</CardTitle></CardHeader><CardBody className="space-y-2">
          <Input aria-label="API key" placeholder="X-API-Key" value={tryKey} onChange={(e) => setTryKey(e.target.value)} />
          <Input aria-label="Ticket" value={tryNo} onChange={(e) => setTryNo(e.target.value)} />
          <Button onClick={call}>GET /v1/tickets/{"{id}"}</Button>
          {out && <pre className="max-h-48 overflow-auto rounded bg-slate-900 p-2 text-xs text-green-300">{out}</pre>}
        </CardBody></Card>
        <Card className="md:col-span-2"><CardHeader><CardTitle className="text-base">API usage</CardTitle></CardHeader><CardBody>
          <table className="w-full text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th>Name</th><th>Key</th><th>Calls</th><th>Last min</th><th>Last used</th><th>Status</th><th></th></tr></thead>
            <tbody>{keys.map((k) => <tr key={k.id} className="border-t"><td className="py-1">{k.name}</td><td className="font-mono">{k.prefix}…</td><td>{k.calls}</td><td>{k.last_minute}/30</td><td>{k.last_used || "-"}</td><td><Badge className={k.active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}>{k.active ? "active" : "revoked"}</Badge></td>
              <td>{k.active && <Button size="sm" variant="outline" onClick={() => api(`/admin/api-keys/${k.id}`, { method: "DELETE" }).then(load)}>Revoke</Button>}</td></tr>)}</tbody></table>
        </CardBody></Card>
      </div>
    </Shell>
  );
}

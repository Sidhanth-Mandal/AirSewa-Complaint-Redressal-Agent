"use client";
import { useCallback, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Select, Simulated, useToast } from "@/components/ui";
import { api } from "@/lib/api";

export default function SlaPage() {
  const { push } = useToast();
  const [pols, setPols] = useState<any[]>([]);
  const [car, setCar] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [n, setN] = useState<any>({ name: "", category: "", severity: "", e1_hours: 24, e2_hours: 72, e3_hours: 96, warn_pct: 0.8, active: true });
  const load = useCallback(() => { api("/admin/sla").then(setPols); api("/admin/car-rules").then(setCar); }, []);
  useEffect(() => { load(); api("/meta").then(setMeta); }, [load]);
  const upd = (p: any, k: string, v: any) => setPols((x) => x.map((y) => (y.id === p.id ? { ...y, [k]: v } : y)));
  const save = (p: any) => api(`/admin/sla/${p.id}`, { method: "PUT", body: p }).then(() => push("SLA policy saved", "success")).catch((e) => push(e.message, "error"));
  return (
    <Shell roles={["admin", "agent", "manager"]} wide>
      <h1 className="mb-1 text-2xl font-bold text-navy">SLA policies & CAR rule base</h1>
      <p className="mb-3 text-sm text-slate-600">Multiple SLA policies run in parallel; the most specific (category + priority) policy applies. Hours are measured from creation (or last reopen) on the demo clock. L1→L2 at <i>e1</i>, L2→L3 at <i>e2</i>, L3→Nodal at <i>e3</i>; S1 starts at L2 so it shifts one level up. After <i>e3</i> the ticket is handed to PACR.</p>
      <Card className="mb-4"><CardBody className="overflow-x-auto pt-4"><table className="w-full min-w-[820px] text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th>Policy</th><th>Category</th><th>Priority</th><th>→L2 (h)</th><th>→L3 (h)</th><th>→Nodal (h)</th><th>Warn at</th><th>On</th><th></th></tr></thead>
        <tbody>{pols.map((p) => (
          <tr key={p.id} className="border-t"><td className="py-1.5 pr-2"><Input aria-label="Name" value={p.name} onChange={(e) => upd(p, "name", e.target.value)} className="!min-h-[34px]" /></td><td>{p.category || "any"}</td><td>{p.severity ? `S${p.severity}` : "any"}</td>
            {["e1_hours", "e2_hours", "e3_hours"].map((k) => <td key={k} className="pr-2"><Input aria-label={k} type="number" min={1} value={p[k]} onChange={(e) => upd(p, k, Number(e.target.value))} className="!min-h-[34px] w-24" /></td>)}
            <td className="pr-2"><Input aria-label="warn" type="number" step="0.05" value={p.warn_pct} onChange={(e) => upd(p, "warn_pct", Number(e.target.value))} className="!min-h-[34px] w-20" /></td>
            <td><input type="checkbox" aria-label="Active" checked={p.active} onChange={(e) => upd(p, "active", e.target.checked)} /></td><td><Button size="sm" onClick={() => save(p)}>Save</Button></td></tr>
        ))}</tbody></table></CardBody></Card>
      <Card className="mb-6"><CardHeader><CardTitle className="text-base">Add SLA policy</CardTitle></CardHeader><CardBody className="grid gap-2 sm:grid-cols-4 lg:grid-cols-8">
        <Input aria-label="Name" placeholder="Name" value={n.name} onChange={(e) => setN({ ...n, name: e.target.value })} className="lg:col-span-2" />
        <Select aria-label="Category" value={n.category} onChange={(e) => setN({ ...n, category: e.target.value })}><option value="">any category</option>{Object.keys(meta?.categories || {}).map((c) => <option key={c}>{c}</option>)}</Select>
        <Select aria-label="Priority" value={n.severity} onChange={(e) => setN({ ...n, severity: e.target.value })}><option value="">any priority</option>{[1, 2, 3, 4].map((s) => <option key={s} value={s}>S{s}</option>)}</Select>
        {["e1_hours", "e2_hours", "e3_hours"].map((k) => <Input key={k} aria-label={k} type="number" value={n[k]} onChange={(e) => setN({ ...n, [k]: Number(e.target.value) })} />)}
        <Button disabled={!n.name} onClick={() => api("/admin/sla", { body: { ...n, category: n.category || null, severity: n.severity ? Number(n.severity) : null } }).then(() => { push("Policy added", "success"); load(); }).catch((e) => push(e.message, "error"))}>Add</Button>
      </CardBody></Card>
      <h2 className="mb-2 flex items-center gap-2 text-xl font-semibold text-navy">CAR / DGCA compliance rule base <Simulated text="Illustrative values" /></h2>
      <p className="mb-3 text-sm text-slate-600">Used by the AI-style closure check (RFP 2.5.9 #4): the resolution is verified against these rules before a ticket can be resolved. Update the parameters when regulations change - no code change required.</p>
      <div className="grid gap-3 md:grid-cols-2">{car.map((r) => <CarCard key={r.id} r={r} onSaved={load} />)}</div>
    </Shell>
  );
}

function CarCard({ r, onSaved }: { r: any; onSaved: () => void }) {
  const { push } = useToast();
  const [txt, setTxt] = useState(JSON.stringify(r.params, null, 1));
  return (
    <Card><CardHeader><CardTitle className="text-sm">{r.code}</CardTitle><Badge className="bg-slate-100">{r.rule_type}</Badge></CardHeader><CardBody className="space-y-2 text-sm">
      <p>{r.title}</p><p className="text-xs text-slate-500">Applies to subcategory: <b>{r.subcategory}</b></p>
      <textarea aria-label="Parameters JSON" className="w-full rounded border border-slate-400 p-2 font-mono text-xs" rows={4} value={txt} onChange={(e) => setTxt(e.target.value)} />
      <Button size="sm" onClick={() => { try { api(`/admin/car-rules/${r.id}`, { method: "PUT", body: { params: JSON.parse(txt), active: r.active } }).then(() => { push("Rule updated", "success"); onSaved(); }); } catch { push("Invalid JSON", "error"); } }}>Save parameters</Button>
    </CardBody></Card>
  );
}

"use client";
import { useCallback, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/badges";
import { Badge, Button, Card, CardBody, Input, Select, Simulated, useToast } from "@/components/ui";
import { api } from "@/lib/api";

export default function CrmPage() {
  const { push } = useToast();
  const [org, setOrg] = useState("6E");
  const [items, setItems] = useState<any[]>([]);
  const [f, setF] = useState<Record<string, any>>({});
  const load = useCallback(() => api(`/crm/inbox?org=${org}`).then((r) => setItems(r.items)), [org]);
  useEffect(() => { load(); const i = setInterval(load, 6000); return () => clearInterval(i); }, [load]);
  async function upd(tn: string, status: string) {
    try {
      const r = await api(`/crm/${tn}/update`, { body: { status, amount: f[tn]?.amount ? Number(f[tn].amount) : null, txn_id: f[tn]?.txn || null, note: f[tn]?.note || "" } });
      push(`Synced back to AirSewa → ${r.synced_status}`, "success"); load();
    } catch (e: any) { push(e.message, "error"); }
  }
  const setField = (tn: string, k: string, v: string) => setF({ ...f, [tn]: { ...f[tn], [k]: v } });
  return (
    <Shell>
      <div className="mb-2 flex items-center gap-2"><h1 className="text-2xl font-bold text-navy">Airline CRM (fake, for the webhook flow)</h1><Simulated /></div>
      <p className="mb-3 text-sm text-slate-600">AirSewa pushes a “call to action” webhook into an airline&apos;s own CRM (stakeholder-with-CRM flow, RFP 2.5.26–2.5.29). Updating the status here syncs back to AirSewa and runs the normal closure rules (evidence + CAR check).</p>
      <label className="mb-3 block max-w-xs text-sm">Airline CRM<Select value={org} onChange={(e) => setOrg(e.target.value)}><option value="6E">IndiGo CRM</option><option value="AI">Air India CRM</option><option value="QP">Akasa Air CRM</option></Select></label>
      <div className="space-y-3">
        {items.length === 0 && <p className="text-slate-500">No webhook calls yet - file a grievance against this airline.</p>}
        {items.map((i) => (
          <Card key={i.ticket_no}><CardBody className="space-y-2 pt-4">
            <div className="flex flex-wrap items-center gap-2"><b className="text-navy">{i.ticket_no}</b><Badge className="bg-slate-100">CRM: {i.crm_status}</Badge>{i.airsewa_status && <StatusBadge s={i.airsewa_status} />}<span className="text-xs text-slate-500">{i.subcategory} · S{i.severity}</span></div>
            <p className="text-sm">{i.summary}</p>
            {i.crm_status !== "Resolved" && (
              <div className="flex flex-wrap items-end gap-2">
                <Input aria-label="Refund amount" placeholder="Amount ₹" className="w-32" value={f[i.ticket_no]?.amount || ""} onChange={(e) => setField(i.ticket_no, "amount", e.target.value)} />
                <Input aria-label="Transaction ID" placeholder="Txn ID" className="w-40" value={f[i.ticket_no]?.txn || ""} onChange={(e) => setField(i.ticket_no, "txn", e.target.value)} />
                <Input aria-label="Note" placeholder="Note" className="w-56" value={f[i.ticket_no]?.note || ""} onChange={(e) => setField(i.ticket_no, "note", e.target.value)} />
                <Button size="sm" variant="outline" onClick={() => upd(i.ticket_no, "Acknowledged")}>Acknowledge</Button>
                <Button size="sm" variant="green" onClick={() => upd(i.ticket_no, "Resolved")}>Resolve in CRM</Button>
              </div>
            )}
          </CardBody></Card>
        ))}
      </div>
    </Shell>
  );
}

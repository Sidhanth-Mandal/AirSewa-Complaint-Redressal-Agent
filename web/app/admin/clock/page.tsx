"use client";
import { useCallback, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Button, Card, CardBody, Input, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

export default function ClockPage() {
  const { push } = useToast();
  const [c, setC] = useState<any>(null);
  const [h, setH] = useState(25);
  const [last, setLast] = useState<any>(null);
  const load = useCallback(() => api("/admin/clock").then(setC), []);
  useEffect(() => { load(); const i = setInterval(load, 5000); return () => clearInterval(i); }, [load]);
  async function adv(x: number) {
    try { const r = await api("/admin/clock/advance", { body: { hours: x } }); setLast(r); push(`Clock +${x}h: ${r.breached} newly breached, ${r.escalated} escalated, ${r.near_breach} warnings`, "success"); load(); }
    catch (e: any) { push(e.message, "error"); }
  }
  return (
    <Shell roles={["admin"]}>
      <h1 className="mb-1 text-2xl font-bold text-navy">Demo clock</h1>
      <p className="mb-3 text-sm text-slate-600">Fast-forward application time to demonstrate SLA breach flags, near-breach alerts to L3/Nodal and automatic escalation L1→L2→L3→Nodal→PACR. Every SLA calculation uses this clock; the sweeper runs immediately after each jump.</p>
      <Card><CardBody className="space-y-4 pt-4">
        <div className="text-lg">Application time: <b className="text-navy" data-testid="clock-now">{c ? fmtDate(c.now) : "-"}</b> <Badge className={c?.offset_hours ? "bg-amber-100 text-amber-900" : "bg-green-100 text-green-800"}>{c?.offset_hours ? `+${c.offset_hours}h ahead of real time` : "real time"}</Badge></div>
        <div className="flex flex-wrap gap-2">{[1, 6, 12, 24, 48, 72].map((x) => <Button key={x} variant="outline" onClick={() => adv(x)}>+{x}h</Button>)}</div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-sm">Custom hours<Input type="number" value={h} min={1} onChange={(e) => setH(Number(e.target.value))} className="w-32" /></label>
          <Button variant="saffron" onClick={() => adv(h)}>Fast-forward</Button>
          <Button variant="outline" onClick={() => api("/admin/clock/reset", { method: "POST" }).then(() => { push("Clock reset to real time (ticket states are kept)", "success"); load(); })}>Reset to real time</Button>
        </div>
        {last && <p className="rounded bg-slate-50 p-3 text-sm">Last sweep: {last.breached} newly breached · {last.escalated} escalated · {last.near_breach} near-breach warnings sent.</p>}
        <p className="text-xs text-slate-500">Tip: open the story ticket “SLA breach auto-escalation” (SpiceJet) as the SpiceJet nodal officer in another window, then jump +5h.</p>
      </CardBody></Card>
    </Shell>
  );
}

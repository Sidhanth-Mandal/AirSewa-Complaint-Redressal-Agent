"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Shell } from "@/components/Shell";
import { Card, CardBody, CardHeader, CardTitle, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

export default function Performance() {
  const [p, setP] = useState<any>(null);
  useEffect(() => { api("/redressor/performance").then(setP); }, []);
  if (!p) return <Shell roles={["redressor", "nodal"]}><Spinner /></Shell>;
  const m = p.me;
  return (
    <Shell roles={["redressor", "nodal"]} wide>
      <h1 className="mb-3 text-2xl font-bold text-navy">My performance</h1>
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-8">
        {[["Assigned", m.assigned_total], ["Open", m.open], ["Resolved", m.resolved], ["Avg TAT (h)", m.avg_tat_h], ["SLA breached", m.breached], ["Breach %", m.breach_pct], ["CSAT", m.csat], ["Reopened", m.reopened]].map(([k, v]) => (
          <Card key={k as string}><CardBody className="pt-3"><div className="text-xs uppercase text-slate-500">{k}</div><div className="text-2xl font-bold text-navy">{v}</div></CardBody></Card>
        ))}
      </div>
      {p.staff && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card><CardHeader><CardTitle>Staff workload & fairness</CardTitle></CardHeader><CardBody>
            <div className="h-64"><ResponsiveContainer><BarChart data={p.staff}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" tick={false} /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="open" fill="#0b3d91" name="Open" /><Bar dataKey="breached" fill="#dc2626" name="Breached" /></BarChart></ResponsiveContainer></div>
          </CardBody></Card>
          <Card><CardHeader><CardTitle>Staff table</CardTitle></CardHeader><CardBody className="overflow-x-auto">
            <table className="w-full text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th>Name</th><th>Lvl</th><th>Open</th><th>Resolved</th><th>Avg TAT</th><th>Breach %</th><th>CSAT</th><th>Load share</th></tr></thead>
              <tbody>{p.staff.map((s: any, i: number) => <tr key={s.id} className="border-t"><td className="py-1">{s.name}</td><td>L{s.level}</td><td>{s.open}</td><td>{s.resolved}</td><td>{s.avg_tat_h}</td><td>{s.breach_pct}</td><td>{s.csat}</td><td>{p.fairness[i].load_share_pct}%</td></tr>)}</tbody></table>
          </CardBody></Card>
        </div>
      )}
    </Shell>
  );
}

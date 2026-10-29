"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Shell } from "@/components/Shell";
import { Badge, Card, CardBody, CardHeader, CardTitle, Input, Simulated, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

export default function Manager() {
  const [p, setP] = useState<any>(null);
  const [target, setTarget] = useState(60);
  const [invoice, setInvoice] = useState(5000000);
  const [days, setDays] = useState(30);
  useEffect(() => { api(`/manager/productivity?days=${days}&target=${target}&invoice=${invoice}`).then(setP); }, [days, target, invoice]);
  if (!p) return <Shell roles={["manager", "admin"]}><Spinner /></Shell>;
  const bad = p.agents.filter((a: any) => a.avg_pu < p.target - 7);
  return (
    <Shell roles={["manager", "admin"]} wide>
      <h1 className="mb-1 text-2xl font-bold text-navy">Control Room - seat & shift productivity</h1>
      <p className="mb-3 text-sm text-slate-600">Unified Productivity Units (RFP 2.28): inbound call 1 · outbound call 1 · e-mail/ticket/social response 0.5 · chat 0.75. Target 60 PU per operator per shift. Shortfall ≤7 PU: no penalty; 8–20: ₹500; 21–40: ₹1,000; &gt;40: ₹1,500. Monthly penalties are capped at 10% of the PACR invoice.</p>
      <Card className="mb-4"><CardBody className="flex flex-wrap items-end gap-3 pt-4">
        <label className="text-sm">PU target<Input type="number" value={target} onChange={(e) => setTarget(Number(e.target.value))} className="w-24" /></label>
        <label className="text-sm">Window (days)<Input type="number" value={days} onChange={(e) => setDays(Number(e.target.value))} className="w-24" /></label>
        <label className="text-sm">Monthly invoice (₹)<Input type="number" value={invoice} onChange={(e) => setInvoice(Number(e.target.value))} className="w-40" /></label>
        <Simulated text="Penalty simulation" />
      </CardBody></Card>
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card><CardBody className="pt-3"><div className="text-xs uppercase text-slate-500">Gross penalty</div><div className="text-2xl font-bold text-red-600">₹{p.gross_penalty.toLocaleString()}</div></CardBody></Card>
        <Card><CardBody className="pt-3"><div className="text-xs uppercase text-slate-500">Cap (10% of invoice)</div><div className="text-2xl font-bold">₹{p.cap.toLocaleString()}</div></CardBody></Card>
        <Card><CardBody className="pt-3"><div className="text-xs uppercase text-slate-500">Payable penalty</div><div className="text-2xl font-bold text-navy">₹{p.payable_penalty.toLocaleString()}</div>{p.capped && <Badge className="bg-amber-100 text-amber-900">capped</Badge>}</CardBody></Card>
        <Card><CardBody className="pt-3"><div className="text-xs uppercase text-slate-500">Agents below target</div><div className="text-2xl font-bold">{bad.length} / {p.agents.length}</div></CardBody></Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader><CardTitle className="text-base">Average PU per shift by agent</CardTitle></CardHeader><CardBody><div className="h-72"><ResponsiveContainer><BarChart data={p.agents}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="agent" tick={{ fontSize: 10 }} /><YAxis /><Tooltip /><ReferenceLine y={p.target} stroke="#138808" label="target" /><Bar dataKey="avg_pu">{p.agents.map((a: any, i: number) => <Cell key={i} fill={a.avg_pu >= p.target ? "#138808" : a.avg_pu >= p.target - 7 ? "#ff9933" : "#dc2626"} />)}</Bar></BarChart></ResponsiveContainer></div></CardBody></Card>
        <Card><CardHeader><CardTitle className="text-base">Penalty by agent (₹)</CardTitle></CardHeader><CardBody><table className="w-full text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th>Agent</th><th>Shifts</th><th>Avg PU</th><th>Short shifts</th><th>Penalty</th></tr></thead><tbody>{p.agents.map((a: any) => <tr key={a.agent} className="border-t"><td className="py-1">{a.agent}</td><td>{a.shifts}</td><td>{a.avg_pu}</td><td>{a.short_shifts}</td><td className="font-semibold">₹{a.penalty.toLocaleString()}</td></tr>)}</tbody></table></CardBody></Card>
        <Card className="lg:col-span-2"><CardHeader><CardTitle className="text-base">Recent shifts</CardTitle></CardHeader><CardBody className="overflow-x-auto"><table className="w-full min-w-[640px] text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th>Day</th><th>Shift</th><th>Agent</th><th>Inbound</th><th>Outbound</th><th>E-mail/ticket</th><th>Chat</th><th>PU</th><th>Penalty</th></tr></thead>
          <tbody>{p.recent.map((r: any, i: number) => <tr key={i} className="border-t"><td className="py-1">{r.day}</td><td>{r.shift}</td><td>{r.agent}</td><td>{r.inbound}</td><td>{r.outbound}</td><td>{r.email}</td><td>{r.chat}</td><td className="font-semibold">{r.pu}</td><td>{r.penalty ? <Badge className="bg-red-100 text-red-800">₹{r.penalty}</Badge> : "-"}</td></tr>)}</tbody></table></CardBody></Card>
      </div>
    </Shell>
  );
}

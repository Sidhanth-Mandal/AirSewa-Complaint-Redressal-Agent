"use client";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Card, CardBody, Simulated, Tabs } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

export default function Audit() {
  const [tab, setTab] = useState("audit");
  const [a, setA] = useState<any>(null);
  const [n, setN] = useState<any[]>([]);
  useEffect(() => { api("/admin/audit?limit=150").then(setA); api("/admin/notifications?limit=150").then(setN); }, []);
  return (
    <Shell roles={["admin"]} wide>
      <h1 className="mb-3 text-2xl font-bold text-navy">Governance: audit log & notification log</h1>
      <Tabs value={tab} onChange={setTab} tabs={[{ id: "audit", label: "Audit log" }, { id: "notif", label: "Notification log (Simulated SMS/e-mail)" }]} />
      {tab === "audit" ? (
        <Card className="mt-3"><CardBody className="overflow-x-auto pt-4">
          {a?.anomalies?.map((x: string) => <p key={x} role="alert" className="mb-2 rounded bg-amber-50 p-2 text-sm text-amber-900">⚠ Anomaly: {x}</p>)}
          <table className="w-full min-w-[640px] text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th>When</th><th>Actor</th><th>Action</th><th>Entity</th><th>Detail</th></tr></thead>
            <tbody>{a?.items.map((x: any, i: number) => <tr key={i} className="border-t"><td className="whitespace-nowrap py-1">{fmtDate(x.at)}</td><td>{x.actor}</td><td><Badge className="bg-slate-100">{x.action}</Badge></td><td>{x.entity}</td><td className="max-w-md truncate">{x.detail}</td></tr>)}</tbody></table>
        </CardBody></Card>
      ) : (
        <Card className="mt-3"><CardBody className="space-y-2 pt-4"><Simulated text="No real message was sent" />
          {n.map((x, i) => <div key={i} className="rounded border p-2 text-sm"><span className="mr-2 rounded bg-slate-100 px-1 text-xs uppercase">{x.channel}</span><span className="text-xs text-slate-500">to {x.to} · {fmtDate(x.at)}</span><div className="font-medium">{x.subject}</div><div className="text-slate-700">{x.body}</div></div>)}
        </CardBody></Card>
      )}
    </Shell>
  );
}

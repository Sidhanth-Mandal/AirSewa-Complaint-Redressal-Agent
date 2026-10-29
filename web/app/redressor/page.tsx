"use client";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import TicketList from "@/components/TicketList";
import { Card, CardBody } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

export default function RedressorQueue() {
  const { me } = useSession();
  const [p, setP] = useState<any>(null);
  useEffect(() => { api("/redressor/performance").then(setP).catch(() => {}); }, []);
  const m = p?.me;
  return (
    <Shell roles={["redressor", "nodal"]} wide>
      <h1 className="mb-1 text-2xl font-bold text-navy">{me?.org} - queue</h1>
      <p className="mb-3 text-sm text-slate-600">{me?.role === "nodal" ? "Nodal Officer: all organisation tickets." : `Level L${me?.level}: you see tickets at your level and below. Critical (S1) cases are routed to L2 and above.`}</p>
      {m && (
        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5">
          {[["Open (mine)", m.open], ["Critical open", m.critical_open], ["SLA breached", m.breached], ["Resolved", m.resolved], ["Avg TAT (h)", m.avg_tat_h]].map(([k, v]) => (
            <Card key={k as string}><CardBody className="pt-3"><div className="text-xs uppercase text-slate-500">{k}</div><div className="text-2xl font-bold text-navy">{v}</div></CardBody></Card>
          ))}
        </div>
      )}
      <TicketList base={{ status: "open", sort: "severity" }} cols={["assignee"]} />
    </Shell>
  );
}

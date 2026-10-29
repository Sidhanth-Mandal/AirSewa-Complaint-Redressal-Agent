"use client";
import { useState } from "react";
import { Shell } from "@/components/Shell";
import TicketList from "@/components/TicketList";
import { Tabs } from "@/components/ui";

export default function Closure() {
  const [tab, setTab] = useState("committee");
  return (
    <Shell roles={["agent"]} wide>
      <h1 className="mb-1 text-2xl font-bold text-navy">Closure verification & Case Closure Committee</h1>
      <p className="mb-3 text-sm text-slate-600">Disputed cases (passenger unhappy although the AI/CAR check passed, or reopen limit reached) land here for PACR coordination. Re-verify recently resolved/closed tickets and reinstate wrongful closures.</p>
      <Tabs value={tab} onChange={setTab} tabs={[{ id: "committee", label: "Committee queue" }, { id: "pacr", label: "Escalated to PACR (SLA)" }, { id: "resolved", label: "Resolved - to verify" }]} />
      <div className="mt-3" key={tab}>
        {tab === "committee" && <TicketList base={{ queue: "committee", status: "" }} />}
        {tab === "pacr" && <TicketList base={{ queue: "pacr", status: "open" }} />}
        {tab === "resolved" && <TicketList base={{ status: "Resolved", sort: "newest" }} />}
      </div>
    </Shell>
  );
}

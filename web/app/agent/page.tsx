"use client";
import { Shell } from "@/components/Shell";
import PacrFeed from "@/components/PacrFeed";

export default function AgentHome() {
  return (
    <Shell roles={["agent"]} wide>
      <h1 className="mb-1 text-2xl font-bold text-navy">AirSewa Agent - review queue</h1>
      <p className="mb-3 text-sm text-slate-600">Complaints ingested from social media and other channels arrive here as draft tickets. Approve, edit, merge or reject. S1 (critical) drafts jump to the top.</p>
      <PacrFeed showFiltered />
    </Shell>
  );
}

"use client";
import { useState } from "react";
import { Shell } from "@/components/Shell";
import PacrFeed from "@/components/PacrFeed";
import Simulator from "@/components/Simulator";
import { Button, Card, CardBody, Simulated, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

export default function Demo() {
  const { me, loading, refresh } = useSession();
  const { push } = useToast();
  const [last, setLast] = useState<number | null>(null);
  const staff = me && ["agent", "admin", "manager"].includes(me.role);
  async function quickLogin() {
    try { await api("/auth/login", { body: { username: "agent1@pacr.demo", password: "Demo@1234" } }); await refresh(); } catch (e: any) { push(e.message, "error"); }
  }
  return (
    <Shell wide bot={false}>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-bold text-navy">Live demo - post on the left, watch PACR detect it on the right <Simulated /></h1>
        {last !== null && <span className="rounded bg-india-50 px-3 py-1 text-sm font-semibold text-india-700" role="status" data-testid="e2e-ms">Last post → draft ticket: {last} ms</span>}
      </div>
      <div className="grid gap-4 lg:grid-cols-2 lg:items-start">
        <section aria-label="Social simulator" className="lg:sticky lg:top-2"><div className="lg:max-h-[calc(100vh-130px)] lg:overflow-y-auto"><Simulator onPosted={(r) => setLast(Math.round(r.pipeline_ms))} /></div></section>
        <section aria-label="PACR live feed">
          <h2 className="mb-2 font-semibold text-navy">PACR Live Social Feed</h2>
          {loading ? null : staff ? <PacrFeed compact /> : (
            <Card><CardBody className="space-y-3 pt-4"><p>The PACR console needs an AirSewa Agent login.</p><Button onClick={quickLogin}>Log in as demo agent (agent1@pacr.demo)</Button><p className="text-xs text-slate-500">Prototype convenience - uses the documented demo account.</p></CardBody></Card>
          )}
        </section>
      </div>
    </Shell>
  );
}

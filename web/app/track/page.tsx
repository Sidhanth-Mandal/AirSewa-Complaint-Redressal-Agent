"use client";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Shell } from "@/components/Shell";
import { StatusBadge } from "@/components/badges";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Simulated } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtDate } from "@/lib/utils";

export default function Track() {
  const t = useTranslations("track");
  const [fn, setFn] = useState("");
  const [fl, setFl] = useState<any>(null);
  const [ferr, setFerr] = useState("");
  const [contact, setContact] = useState("");
  const [sub, setSub] = useState(false);
  const [tn, setTn] = useState("");
  const [m4, setM4] = useState("");
  const [tk, setTk] = useState<any>(null);
  const [terr, setTerr] = useState("");

  async function check(e: React.FormEvent) {
    e.preventDefault(); setFerr(""); setFl(null); setSub(false);
    try { setFl(await api(`/flights/${encodeURIComponent(fn)}`)); } catch (x: any) { setFerr(x.message); }
  }
  async function subscribe() {
    try { await api("/flights/subscribe", { body: { flight_no: fn, contact, channel: contact.includes("@") ? "email" : "sms" } }); setSub(true); } catch (x: any) { setFerr(x.message); }
  }
  async function trackTicket(e: React.FormEvent) {
    e.preventDefault(); setTerr(""); setTk(null);
    try { setTk(await api(`/track/${encodeURIComponent(tn)}?mobile4=${encodeURIComponent(m4)}`)); } catch (x: any) { setTerr(x.message); }
  }
  return (
    <Shell>
      <h1 className="mb-4 text-2xl font-bold text-navy">{t("title")}</h1>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>{t("flightTitle")}</CardTitle><Simulated text="Mock flight data" /></CardHeader>
          <CardBody>
            <form onSubmit={check} className="flex flex-wrap items-end gap-2">
              <div className="min-w-[200px] flex-1"><Field label={t("flightNo")}>{(i) => <Input id={i} value={fn} onChange={(e) => setFn(e.target.value)} required />}</Field></div>
              <Button>{t("check")}</Button>
            </form>
            {ferr && <p role="alert" className="mt-2 text-sm text-red-700">{ferr}</p>}
            {fl && (
              <div className="mt-4 space-y-2 rounded border p-3">
                <div className="flex items-center justify-between"><b className="text-xl text-navy">{fl.flight_no}</b><Badge className={fl.status === "Cancelled" ? "bg-red-100 text-red-800" : fl.status === "Delayed" ? "bg-amber-100 text-amber-900" : "bg-green-100 text-green-800"}>{fl.status}{fl.delay_minutes ? ` +${fl.delay_minutes}m` : ""}</Badge></div>
                <p className="text-lg">{fl.from} → {fl.to}</p>
                <p className="text-sm text-slate-700">Scheduled dep: {fmtDate(fl.scheduled_departure)} · {t("eta")}: {fmtDate(fl.estimated_arrival)} · {t("gate")} {fl.gate} · {fl.terminal}</p>
                <div className="border-t pt-3">
                  <Field label={t("notifyContact")}>{(i) => <Input id={i} value={contact} onChange={(e) => setContact(e.target.value)} />}</Field>
                  <Button className="mt-2" variant="outline" disabled={!contact} onClick={subscribe}>{t("notify")}</Button>
                  {sub && <p className="mt-2 text-sm text-india-700" role="status">{t("subscribed")}</p>}
                </div>
              </div>
            )}
          </CardBody>
        </Card>
        <Card id="ticket">
          <CardHeader><CardTitle>{t("ticketTitle")}</CardTitle></CardHeader>
          <CardBody>
            <form onSubmit={trackTicket} className="space-y-3">
              <Field label={t("ticketId")}>{(i) => <Input id={i} value={tn} onChange={(e) => setTn(e.target.value)} placeholder="AS-2026-000123" required />}</Field>
              <Field label={t("mobile4")}>{(i) => <Input id={i} value={m4} onChange={(e) => setM4(e.target.value)} maxLength={4} inputMode="numeric" required />}</Field>
              <Button>{t("check")}</Button>
            </form>
            {terr && <p role="alert" className="mt-2 text-sm text-red-700">{terr}</p>}
            {tk && (
              <div className="mt-4 space-y-2 rounded border p-3">
                <div className="flex items-center justify-between"><b className="text-navy">{tk.ticket_no}</b><StatusBadge s={tk.status} /></div>
                <p className="text-sm">{tk.category} · with {tk.assigned_org} · updated {fmtDate(tk.updated_at)}</p>
                <ol className="ml-2 border-l-2 pl-3 text-sm">{tk.timeline.map((e: any, i: number) => <li key={i}><span className="text-xs text-slate-500">{fmtDate(e.at)}</span> {e.to}</li>)}</ol>
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </Shell>
  );
}

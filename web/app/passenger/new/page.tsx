"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Suspense, useEffect, useRef, useState } from "react";
import { Shell } from "@/components/Shell";
import { SevBadge } from "@/components/badges";
import { Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Select, Simulated, Textarea } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useSession } from "@/lib/session";

const CATS = ["flight", "airport", "ground", "govt", "other"];

function Form() {
  const t = useTranslations("form");
  const tc = useTranslations("common");
  const sp = useSearchParams();
  const { me, loading } = useSession();
  const [meta, setMeta] = useState<any>(null);
  const [f, setF] = useState<any>({ category: sp.get("category") || "flight", description: sp.get("description") || "", contact_name: "", contact_mobile: "", contact_email: "", airline_org_id: "",
    airport_id: "", event_at: "", service_request_no: "", pnr: "", flight_no: "", consent: false, ticket_amount: "", block_time_hours: "", baggage_weight_kg: "" });
  const [files, setFiles] = useState<File[]>([]);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<any>(null);
  const [prev, setPrev] = useState<any>(null);
  const timer = useRef<any>(undefined);
  const set = (k: string, v: any) => setF((x: any) => ({ ...x, [k]: v }));

  useEffect(() => { api("/meta").then(setMeta); }, []);
  useEffect(() => {
    if (me) setF((x: any) => ({ ...x, contact_name: x.contact_name || me.name || "", contact_mobile: x.contact_mobile || me.mobile || "", contact_email: x.contact_email || me.email || "" }));
  }, [me]);
  useEffect(() => {
    clearTimeout(timer.current);
    if (f.description.length < 8) { setPrev(null); return; }
    timer.current = setTimeout(() => api("/tickets/preview", { body: { text: f.description, category: f.category } }).then(setPrev).catch(() => {}), 350);
  }, [f.description, f.category]);

  const tat = meta?.tat?.[f.category];
  async function lookup() {
    if (!f.airline_org_id || !f.service_request_no) return;
    const al = meta.airlines.find((a: any) => String(a.id) === String(f.airline_org_id));
    const r = await api(`/booking/lookup?airline=${al.code}&srn=${encodeURIComponent(f.service_request_no)}`);
    setF((x: any) => ({ ...x, flight_no: r.flight_no, pnr: r.pnr }));
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErrs({}); setMsg(""); setBusy(true);
    const body: any = { ...f };
    ["airline_org_id", "airport_id"].forEach((k) => (body[k] = body[k] ? Number(body[k]) : null));
    ["ticket_amount", "block_time_hours", "baggage_weight_kg"].forEach((k) => (body[k] = body[k] ? Number(body[k]) : null));
    ["event_at", "service_request_no", "pnr", "flight_no", "contact_mobile", "contact_email"].forEach((k) => { if (!body[k]) body[k] = null; });
    try {
      const r = await api("/tickets", { body });
      for (const file of files) {
        const fd = new FormData(); fd.append("file", file); fd.append("kind", "upload");
        await api(`/tickets/${r.ticket_no}/attachments`, { form: fd }).catch((x) => setMsg(`Attachment ${file.name}: ${x.message}`));
      }
      setDone(r);
    } catch (x: any) {
      if (x instanceof ApiError && typeof x.detail === "object") {
        const m: Record<string, string> = {};
        (x.detail.fields || []).forEach((k: string) => (m[k] = x.detail.message || "Required"));
        setErrs(m); setMsg(x.detail.message || x.message);
      } else setMsg(x.message);
    }
    setBusy(false);
  }
  function addFiles(list: FileList | null) {
    if (!list) return;
    const ok: File[] = []; let bad = "";
    Array.from(list).forEach((x) => {
      if (!/\.(pdf|jpe?g|png)$/i.test(x.name)) bad = `${x.name}: only PDF, JPG, PNG allowed`;
      else if (x.size > 10 * 1024 * 1024) bad = `${x.name}: larger than 10 MB`;
      else ok.push(x);
    });
    setMsg(bad); setFiles((p) => [...p, ...ok]);
  }

  if (!loading && !me) return <Card><CardBody className="pt-4"><p>{t("loginFirst")}</p><Link href="/login?next=/passenger/new"><Button className="mt-3">{tc("login")}</Button></Link></CardBody></Card>;
  if (me && me.role !== "passenger") return <Card><CardBody className="pt-4">Only passengers can file grievances here. Agents can file on behalf of callers from the agent console.</CardBody></Card>;
  if (done) return (
    <Card className="mx-auto max-w-xl border-india">
      <CardHeader><CardTitle className="text-india-700">✔ {t("success")}</CardTitle></CardHeader>
      <CardBody className="space-y-2">
        <div className="text-sm text-slate-600">{t("yourId")}</div>
        <div className="text-3xl font-bold tracking-wide text-navy" data-testid="ticket-id">{done.ticket_no}</div>
        <p>{t("routedTo")}: <b>{done.assigned_org}</b> (L{done.level}) · {t("priority")}: <SevBadge s={done.severity} /></p>
        <p className="text-sm text-slate-700">{done.severity_reason}</p>
        <p className="text-sm">{t("tat", { h: done.tat_hours })} · A confirmation was sent (Simulated SMS / e-mail - see the notification log on the ticket).</p>
        <div className="flex gap-2 pt-2"><Link href={`/tickets/${done.ticket_no}`}><Button>{t("viewTicket")}</Button></Link><Button variant="outline" onClick={() => location.reload()}>{t("another")}</Button></div>
      </CardBody>
    </Card>
  );
  const flight = f.category === "flight";
  return (
    <form onSubmit={submit} noValidate className="mx-auto max-w-3xl space-y-5">
      <div><h1 className="text-2xl font-bold text-navy">{t("title")}</h1><p className="text-sm text-slate-600">{t("subtitle")}</p></div>
      <Card>
        <CardBody className="space-y-4 pt-4">
          <Field label={t("category")} required>{(i) => (
            <Select id={i} value={f.category} onChange={(e) => set("category", e.target.value)}>{CATS.map((c) => <option key={c} value={c}>{t(`cat.${c}` as any)}</option>)}</Select>
          )}</Field>
          {tat && <p className="rounded bg-navy-50 p-2 text-sm text-navy" role="note">⏱ {t("tat", { h: tat.standard_h })} · {t("tatCritical", { h: tat.critical_h })}</p>}
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label={t("name")} required error={errs.contact_name}>{(i) => <Input id={i} value={f.contact_name} onChange={(e) => set("contact_name", e.target.value)} />}</Field>
            <Field label={t("mobile")} required error={errs.contact_details} hint={t("contactHint")}>{(i) => <Input id={i} value={f.contact_mobile} inputMode="tel" onChange={(e) => set("contact_mobile", e.target.value)} />}</Field>
            <Field label={t("email")}>{(i) => <Input id={i} type="email" value={f.contact_email} onChange={(e) => set("contact_email", e.target.value)} />}</Field>
          </div>
          {flight && (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t("airline")} required error={errs.airline_org_id}>{(i) => (
                <Select id={i} value={f.airline_org_id} onChange={(e) => set("airline_org_id", e.target.value)}><option value="">-</option>{meta?.airlines.map((a: any) => <option key={a.id} value={a.id}>{a.name}</option>)}</Select>
              )}</Field>
              <Field label={t("srn")} required error={errs.service_request_no}>{(i) => <Input id={i} value={f.service_request_no} onChange={(e) => set("service_request_no", e.target.value)} onBlur={lookup} />}</Field>
              <Field label={t("flightNo")} required error={errs.flight_no}>{(i) => <Input id={i} value={f.flight_no} onChange={(e) => set("flight_no", e.target.value.toUpperCase())} />}</Field>
              <Field label={t("pnr")} required error={errs.pnr}>{(i) => <Input id={i} value={f.pnr} maxLength={10} onChange={(e) => set("pnr", e.target.value.toUpperCase())} />}</Field>
              <div className="sm:col-span-2 flex items-center gap-2"><Button type="button" size="sm" variant="outline" onClick={lookup}>{t("autoFetch")}</Button><Simulated /></div>
            </div>
          )}
          {(f.category === "airport" || flight) && (
            <Field label={t("airport")} required={f.category === "airport"} error={errs.airport_id}>{(i) => (
              <Select id={i} value={f.airport_id} onChange={(e) => set("airport_id", e.target.value)}><option value="">-</option>{meta?.airports.map((a: any) => <option key={a.id} value={a.id}>{a.city} ({a.code})</option>)}</Select>
            )}</Field>
          )}
          {f.category !== "other" && <Field label={t("eventAt")} required error={errs.event_at}>{(i) => <Input id={i} type="datetime-local" value={f.event_at} onChange={(e) => set("event_at", e.target.value)} />}</Field>}
          <Field label={t("description")} required error={errs.description} hint={t("descHint")}>{(i) => <Textarea id={i} rows={5} value={f.description} onChange={(e) => set("description", e.target.value)} maxLength={4000} />}</Field>
          {prev && (
            <div className={`rounded border p-2 text-sm ${prev.critical ? "border-red-400 bg-red-50 text-red-900" : "border-slate-200 bg-slate-50"}`} aria-live="polite">
              Detected: <b>{prev.category}/{prev.subcategory}</b> · <SevBadge s={prev.severity} /> {prev.critical ? "Critical keywords found - this will be fast-tracked" : ""} <span className="text-xs text-slate-600">({prev.severity_reason})</span>
            </div>
          )}
          {flight && (
            <details className="rounded border p-3"><summary className="cursor-pointer text-sm font-medium">{t("optional")}</summary>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <Field label={t("ticketAmount")}>{(i) => <Input id={i} type="number" min={0} value={f.ticket_amount} onChange={(e) => set("ticket_amount", e.target.value)} />}</Field>
                <Field label={t("blockTime")}>{(i) => <Input id={i} type="number" step="0.5" min={0} value={f.block_time_hours} onChange={(e) => set("block_time_hours", e.target.value)} />}</Field>
                <Field label={t("baggageKg")}>{(i) => <Input id={i} type="number" min={0} value={f.baggage_weight_kg} onChange={(e) => set("baggage_weight_kg", e.target.value)} />}</Field>
              </div>
            </details>
          )}
          <Field label={t("attach")} hint={t("attachHint")}>{(i) => <Input id={i} type="file" multiple accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => addFiles(e.target.files)} />}</Field>
          {files.length > 0 && <ul className="text-sm">{files.map((x, i) => <li key={i}>📎 {x.name} ({Math.round(x.size / 1024)} KB) <button type="button" className="text-red-700 underline" onClick={() => setFiles(files.filter((_, j) => j !== i))}>remove</button></li>)}</ul>}
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-1 h-5 w-5" checked={f.consent} onChange={(e) => set("consent", e.target.checked)} aria-describedby={errs.consent ? "consent-err" : undefined} />
            <span>{t("consent")} <span className="text-red-600">*</span></span>
          </label>
          {errs.consent && <p id="consent-err" role="alert" className="text-sm text-red-700">{errs.consent}</p>}
          {msg && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-800">{msg}</p>}
          <Button size="lg" className="w-full" disabled={busy}>{busy ? tc("loading") : t("submit")}</Button>
        </CardBody>
      </Card>
    </form>
  );
}
export default function NewGrievance() { return <Shell><Suspense><Form /></Suspense></Shell>; }


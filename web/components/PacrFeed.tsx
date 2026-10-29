"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Line, LineChart, ResponsiveContainer } from "recharts";
import { api, qs } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import { cn, relTime } from "@/lib/utils";
import { SevBadge } from "./badges";
import { Badge, Button, Card, CardBody, Input, Modal, Select, Simulated, Spinner, Tabs, useToast } from "./ui";

export const PlatformIcon = ({ ch, className }: { ch: string; className?: string }) => {
  const m: Record<string, [string, string]> = { social_x: ["𝕏", "bg-black text-white"], social_instagram: ["◎", "bg-gradient-to-br from-fuchsia-500 to-orange-400 text-white"], whatsapp: ["✆", "bg-green-600 text-white"], email: ["✉", "bg-blue-600 text-white"], ivr: ["☎", "bg-slate-600 text-white"], cpgrams: ["▤", "bg-navy text-white"], letter: ["✎", "bg-amber-700 text-white"], chat: ["💬", "bg-teal-600 text-white"] };
  const [g, c] = m[ch] || ["?", "bg-slate-400"];
  return <span className={cn("inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold", c, className)} aria-label={ch} title={ch}>{g}</span>;
};
const STAGES = ["received", "filtered", "translated", "classified", "deduplicated", "draft_created"];
const SENT = (s: number) => (s > 0.2 ? "😊" : s < -0.2 ? "😠" : "😐");

let audioCtx: AudioContext | null = null;
export function beep() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || (window as any).webkitAudioContext)();
    const o = audioCtx.createOscillator(); const g = audioCtx.createGain();
    o.type = "square"; o.frequency.value = 880; g.gain.value = 0.08; o.connect(g); g.connect(audioCtx.destination);
    o.start(); setTimeout(() => { o.frequency.value = 660; }, 160); setTimeout(() => o.stop(), 340);
  } catch {}
}

function Timeline({ t }: { t: any[] }) {
  return (
    <ol className="mt-2 flex flex-wrap items-center gap-x-1 gap-y-1 text-[11px]" aria-label="Pipeline timeline">
      {STAGES.map((s) => {
        const x = t.find((y) => y.stage === s);
        return (
          <li key={s} className={cn("flex items-center rounded px-1.5 py-0.5", x ? "bg-india-50 text-india-700" : "bg-slate-100 text-slate-400")} title={x?.detail}>
            {x ? "✓" : "·"} {s.replace("_", " ")}{x && <b className="ml-1 tabular-nums">{x.ms}ms</b>}
          </li>
        );
      })}
    </ol>
  );
}

export function DraftRow({ d, onOpen, fresh, compact }: { d: any; onOpen: (d: any) => void; fresh?: boolean; compact?: boolean }) {
  const filtered = !d.is_complaint;
  const s1 = d.severity === 1 && !filtered;
  return (
    <li className={cn("rounded-lg border bg-white p-3 shadow-sm", fresh && "animate-slidein", s1 && "border-red-500 ring-1 ring-red-400", filtered && "bg-slate-50 opacity-80", d.status === "grouped" && "ml-6 border-dashed")}>
      <div className="flex items-start gap-3">
        <PlatformIcon ch={d.channel} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            {filtered ? <Badge className="bg-slate-200 text-slate-700">Filtered</Badge> : d.status === "grouped" ? <Badge className="bg-blue-100 text-blue-800">Grouped under #{d.parent_draft_id}</Badge> : <Badge className="bg-red-100 text-red-800">● Complaint detected</Badge>}
            <Badge className="bg-slate-100 text-slate-700">{d.platform} · {d.source_type}</Badge>
            <span className="font-medium text-slate-700">{d.masked_handle}</span>
            <span className="text-slate-500">{relTime(d.created_at)}</span>
            {d.status === "approved" && <Badge className="bg-green-100 text-green-800">Ticket {d.ticket_no}</Badge>}
            {d.status === "rejected" && <Badge className="bg-slate-200 text-slate-700">Rejected</Badge>}
            {d.viral && <Badge className="bg-fuchsia-600 text-white">🔥 VIRAL</Badge>}
            {d.related_count > 0 && <Badge className="bg-blue-600 text-white">{d.related_count} related posts</Badge>}
            {d.dup_of_ticket_id && <Badge className="bg-amber-100 text-amber-900">Possible duplicate: {d.dup_reason}</Badge>}
          </div>
          <p className={cn("mt-1 text-sm", compact && "line-clamp-2")}>{d.original_text}</p>
          {d.lang !== "en" && d.text_en && !filtered && <p className="mt-0.5 text-xs italic text-slate-600">↳ {d.lang === "hi" ? "Hindi" : "Hinglish"} translated (Simulated): {d.text_en}</p>}
          {filtered ? <p className="mt-1 text-xs font-medium text-slate-600">{d.reason}</p> : (
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
              <SevBadge s={d.severity} reason={d.severity_reason} />
              <Badge className="bg-navy-50 text-navy">{d.category}/{d.subcategory}</Badge>
              <Badge className="bg-slate-100 text-slate-800">→ {d.stakeholder}</Badge>
              <span title={`sentiment ${d.sentiment}`}>{SENT(d.sentiment)} {d.sentiment}</span>
              <span className="text-slate-600">{d.lang}</span>
              <span className="flex items-center gap-1" title="AI confidence"><span className="h-1.5 w-14 overflow-hidden rounded bg-slate-200"><span className="block h-full bg-india" style={{ width: `${Math.round(d.confidence * 100)}%` }} /></span>{Math.round(d.confidence * 100)}%</span>
              {d.media_note && <Badge className="bg-purple-50 text-purple-800">🖼 {d.media_note}</Badge>}
            </div>
          )}
          {!filtered && !compact && <p className="mt-1 text-xs text-slate-600">Why {`S${d.severity}`}: {d.severity_reason}</p>}
          <Timeline t={d.timings || []} />
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className="text-[11px] tabular-nums text-slate-500">{d.total_ms}ms total</span>
          <Button size="sm" variant={d.status === "pending" ? "default" : "outline"} onClick={() => onOpen(d)}>{d.status === "pending" ? "Review" : "Open"}</Button>
        </div>
      </div>
    </li>
  );
}

export function Sparkline({ data, color }: { data: number[]; color: string }) {
  return <div className="h-10 w-28"><ResponsiveContainer><LineChart data={data.map((v, i) => ({ i, v }))}><Line type="monotone" dataKey="v" stroke={color} dot={false} strokeWidth={2} isAnimationActive={false} /></LineChart></ResponsiveContainer></div>;
}

export function DraftModal({ id, onClose, onChange, meta, readOnly }: { id: number | null; onClose: () => void; onChange: () => void; meta: any; readOnly?: boolean }) {
  const { push } = useToast();
  const [d, setD] = useState<any>(null);
  const [o, setO] = useState<any>({});
  const [reply, setReply] = useState("");
  const [mergeTo, setMergeTo] = useState("");
  const [reason, setReason] = useState("");
  const load = useCallback(() => id && api(`/pacr/drafts/${id}`).then((x) => { setD(x); setReply(x.reply_text || ""); }), [id]);
  useEffect(() => { setD(null); setO({}); load(); }, [id, load]);
  if (!id) return null;
  async function run(fn: () => Promise<any>, ok: string) { try { const r = await fn(); push(ok, "success"); await load(); onChange(); return r; } catch (e: any) { push(e.message, "error"); } }
  const subs = meta?.subcategories?.[o.category || d?.category] || [];
  return (
    <Modal open title={d ? `Draft #${d.id} - ${d.platform} ${d.source_type}` : "Loading"} onClose={onClose} wide>
      {!d ? <Spinner /> : (
        <div className="space-y-3 text-sm">
          <div className="rounded bg-slate-50 p-3">
            <div className="text-xs text-slate-500">From <b>{d.author_handle}</b> {d.author_name && `(${d.author_name})`} · {relTime(d.created_at)} {d.url && <Link className="ml-2 text-navy underline" href={d.url} target="_blank">Open original post (Simulated app)</Link>}</div>
            <p className="mt-1 whitespace-pre-wrap text-base">{d.original_text}</p>
            {d.lang !== "en" && <p className="mt-1 italic text-slate-700">English (Simulated translation): {d.text_en}</p>}
            {d.media_note && <p className="mt-1 text-purple-800">🖼 {d.media_note} <Simulated /></p>}
            {d.payload?.subject && <p className="text-xs">Subject: {d.payload.subject}</p>}
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <div><b>Entities:</b> {Object.entries(d.entities || {}).map(([k, v]) => <Badge key={k} className="mr-1 bg-slate-100">{k}: {String(v)}</Badge>)}</div>
            <div><b>Severity reason:</b> {d.severity_reason}</div>
            <div><b>Confidence:</b> {Math.round(d.confidence * 100)}% · <b>Sentiment:</b> {d.sentiment}</div>
            {d.dup_reason && <div className="text-amber-800"><b>Duplicate hint:</b> {d.dup_reason}</div>}
          </div>
          <Timeline t={d.timings || []} />
          {d.children?.length > 0 && (
            <div><b>Related posts ({d.children.length}):</b>
              <ul className="mt-1 max-h-40 space-y-1 overflow-y-auto">{d.children.map((c: any) => <li key={c.id} className="rounded border p-1.5 text-xs">{c.author_handle} · {relTime(c.created_at)} - {c.original_text}</li>)}</ul></div>
          )}
          {d.status === "pending" && !readOnly && (
            <div className="space-y-2 rounded border border-navy/30 p-3">
              <b>Review / override before approval</b>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <Select aria-label="Category" value={o.category || ""} onChange={(e) => setO({ ...o, category: e.target.value, subcategory: "" })}><option value="">Category: {d.category}</option>{Object.keys(meta?.categories || {}).map((c) => <option key={c}>{c}</option>)}</Select>
                <Select aria-label="Subcategory" value={o.subcategory || ""} onChange={(e) => setO({ ...o, subcategory: e.target.value })}><option value="">Sub: {d.subcategory}</option>{subs.map((c: string) => <option key={c}>{c}</option>)}</Select>
                <Select aria-label="Severity" value={o.severity || ""} onChange={(e) => setO({ ...o, severity: e.target.value })}><option value="">Severity: S{d.severity}</option>{[1, 2, 3, 4].map((s) => <option key={s} value={s}>S{s}</option>)}</Select>
                <Select aria-label="Assignee" value={o.assigned_org_id || ""} onChange={(e) => setO({ ...o, assigned_org_id: e.target.value })}><option value="">To: {d.stakeholder}</option>{meta?.orgs.map((x: any) => <option key={x.id} value={x.id}>{x.name}</option>)}</Select>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="green" onClick={() => run(() => api(`/pacr/drafts/${d.id}/approve`, { body: { category: o.category || null, subcategory: o.subcategory || null, severity: o.severity ? Number(o.severity) : null, assigned_org_id: o.assigned_org_id ? Number(o.assigned_org_id) : null } }), "Approved - ticket created, SLA timers started")}>Approve → create ticket</Button>
                <Input aria-label="Reject reason" placeholder="Reject reason" value={reason} onChange={(e) => setReason(e.target.value)} className="max-w-[220px]" />
                <Button variant="danger" onClick={() => run(() => api(`/pacr/drafts/${d.id}/reject`, { body: { reason: reason || "Not a valid grievance" } }), "Rejected")}>Reject</Button>
              </div>
              <div className="flex flex-wrap gap-2">
                <Input aria-label="Merge target" placeholder="Merge into draft # or ticket ID" value={mergeTo} onChange={(e) => setMergeTo(e.target.value)} className="max-w-[260px]" />
                <Button variant="outline" disabled={!mergeTo} onClick={() => run(() => api(`/pacr/drafts/${d.id}/merge`, { body: mergeTo.startsWith("AS-") ? { target_ticket_no: mergeTo } : { target_draft_id: Number(mergeTo.replace("#", "")) } }), "Merged (agent-confirmed)")}>Confirm merge</Button>
                {d.dup_of_ticket_id && <Button variant="outline" onClick={() => setMergeTo(d.dup_reason?.match(/AS-\d+-\d+/)?.[0] || "")}>Use suggested duplicate</Button>}
              </div>
            </div>
          )}
          {d.status === "approved" && (
            <div className="space-y-2 rounded border border-india/40 bg-india-50 p-3">
              <div>✔ Ticket <Link className="font-bold text-navy underline" href={`/tickets/${d.ticket_no}`}>{d.ticket_no}</Link> created and SLA started.</div>
              <b>Acknowledgment reply {d.reply_sent ? "(sent)" : "(draft)"}</b>
              <Input aria-label="Reply" value={reply} onChange={(e) => setReply(e.target.value)} disabled={d.reply_sent} />
              {!readOnly && <Button disabled={d.reply_sent} onClick={() => run(() => api(`/pacr/drafts/${d.id}/reply`, { body: { text: reply } }), "Reply sent to the user's notifications (Simulated)")}>{d.reply_sent ? "Reply sent ✓" : "Send reply as @AirSewa_Official"}</Button>}
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

export default function PacrFeed({ compact, readOnly, showFiltered = true }: { compact?: boolean; readOnly?: boolean; showFiltered?: boolean }) {
  const { push } = useToast();
  const [rows, setRows] = useState<any[] | null>(null);
  const [tab, setTab] = useState("live");
  const [stats, setStats] = useState<any>(null);
  const [meta, setMeta] = useState<any>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [sound, setSound] = useState(false);
  const [fresh, setFresh] = useState<Set<number>>(new Set());
  const soundRef = useRef(false);
  soundRef.current = sound;

  const load = useCallback(() => api(`/pacr/drafts${qs({ status: tab === "queue" ? "queue" : tab === "filtered" ? "filtered" : undefined, limit: compact ? 25 : 80 })}`).then((r) => setRows(r)).catch(() => setRows([])), [tab, compact]);
  const loadStats = useCallback(() => api("/pacr/stats").then(setStats).catch(() => {}), []);
  useEffect(() => { load(); loadStats(); api("/meta").then(setMeta); }, [load, loadStats]);
  useEffect(() => { const i = setInterval(loadStats, 15000); return () => clearInterval(i); }, [loadStats]);

  useSSE(["pacr"], (_n, ev) => {
    const d = ev.draft;
    if (!d) return;
    if (ev.type === "draft") {
      setRows((r) => (r ? [d, ...r.filter((x) => x.id !== d.id)] : [d]));
      setFresh((f) => new Set(f).add(d.id)); setTimeout(() => setFresh((f) => { const n = new Set(f); n.delete(d.id); return n; }), 2500);
      if (d.is_complaint && d.severity === 1 && d.status !== "grouped") {
        push(`🚨 S1 CRITICAL complaint detected: ${d.category}/${d.subcategory} - ${d.original_text.slice(0, 80)}`, "alert");
        if (soundRef.current) beep();
      }
      loadStats();
    } else if (ev.type === "draft_update" || ev.type === "viral") {
      setRows((r) => (r ? r.map((x) => (x.id === d.id ? { ...x, ...d } : x)) : r));
      if (ev.type === "viral") push(`🔥 Viral complaint: priority raised to S${d.severity} (${d.related_count} related posts)`, "alert");
    }
  });

  const shown = (rows || []).filter((r) => (showFiltered || r.is_complaint) && (tab === "live" || tab === "filtered" || r.status === "pending" || r.status === "grouped"));
  const sparkX = stats?.sparkline?.social_x || [], sparkI = stats?.sparkline?.social_instagram || [];
  return (
    <div className="space-y-3">
      <div className={cn("grid gap-3", compact ? "grid-cols-2" : "grid-cols-2 lg:grid-cols-5")}>
        <Card><CardBody className="pt-3"><div className="text-xs uppercase text-slate-500">Detected (last 5 min)</div><div className="text-3xl font-bold text-red-600" data-testid="detected-5m">{stats?.detected_5m ?? "-"}</div><div className="text-xs text-slate-500">{stats?.filtered_5m ?? 0} filtered</div></CardBody></Card>
        <Card><CardBody className="pt-3"><div className="text-xs uppercase text-slate-500">Awaiting review</div><div className="text-3xl font-bold text-navy">{stats?.pending ?? "-"}</div></CardBody></Card>
        <Card><CardBody className="pt-3"><div className="flex items-center justify-between text-xs uppercase text-slate-500">X / 30 min</div><Sparkline data={sparkX} color="#111" /></CardBody></Card>
        <Card><CardBody className="pt-3"><div className="text-xs uppercase text-slate-500">Instagram / 30 min</div><Sparkline data={sparkI} color="#c026d3" /></CardBody></Card>
        {!compact && <Card><CardBody className="pt-3"><div className="text-xs uppercase text-slate-500">Trending issues (24h)</div><ul className="text-xs">{(stats?.trending || []).slice(0, 3).map((t: any) => <li key={t.issue}>{t.issue} <b>{t.count}</b></li>)}</ul></CardBody></Card>}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Tabs value={tab} onChange={setTab} tabs={[{ id: "live", label: "Live feed" }, { id: "queue", label: "Review queue" }, ...(showFiltered ? [{ id: "filtered", label: "Filtered (with reason)" }] : [])]} className="flex-1" />
        <Button size="sm" variant={sound ? "green" : "outline"} onClick={() => { setSound(!sound); if (!sound) beep(); }} aria-pressed={sound}>{sound ? "🔊 Sound on" : "🔇 Enable S1 alert sound"}</Button>
      </div>
      {rows === null ? <Spinner /> : (
        <ul className="space-y-2" aria-live="polite">
          {shown.map((d) => <DraftRow key={d.id} d={d} fresh={fresh.has(d.id)} onOpen={(x) => setOpen(x.id)} compact={compact} />)}
          {shown.length === 0 && <li className="p-6 text-center text-slate-500">Nothing here yet - post a complaint in the simulator.</li>}
        </ul>
      )}
      <DraftModal id={open} onClose={() => setOpen(null)} onChange={() => { load(); loadStats(); }} meta={meta} readOnly={readOnly} />
    </div>
  );
}

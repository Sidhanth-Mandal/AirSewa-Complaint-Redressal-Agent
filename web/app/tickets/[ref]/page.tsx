"use client";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { SevBadge, SourceChip, StatusBadge } from "@/components/badges";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Select, Simulated, Spinner, Textarea, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import { useSession } from "@/lib/session";
import { fmtDate, fmtHours, relTime } from "@/lib/utils";

const FLOW = ["Under Assessment", "Assigned", "In-Progress", "Provisionally Resolved", "Resolved", "Closed"];
const LVL: Record<number, string> = { 1: "L1", 2: "L2", 3: "L3", 4: "Nodal Officer" };

export default function TicketPage() {
  const { ref } = useParams<{ ref: string }>();
  const { me } = useSession();
  const t = useTranslations("ticket");
  const ts = useTranslations("status");
  const { push } = useToast();
  const [d, setD] = useState<any>(null);
  const [meta, setMeta] = useState<any>(null);
  const [err, setErr] = useState("");
  const load = useCallback(() => api(`/tickets/${ref}`).then(setD).catch((e) => setErr(e.message)), [ref]);
  useEffect(() => { load(); api("/meta").then(setMeta); }, [load]);
  useSSE(["tickets"], (_n, ev) => { if (ev.ticket_no === ref || ev.type === "sla") load(); }, !!me && me.role !== "passenger");

  async function act(body: any, okMsg = "Done") {
    try {
      const r = await api(`/tickets/${ref}/action`, { body });
      push(okMsg + (r.status ? ` → ${r.status}` : ""), "success");
      await load();
      return r;
    } catch (e: any) {
      push(e.message, "error");
      if (e.detail?.compliance) await load();
      throw e;
    }
  }
  if (err) return <Shell roles={["passenger", "redressor", "nodal", "agent", "admin", "manager"]}><p role="alert" className="rounded bg-red-50 p-4 text-red-800">{err}</p></Shell>;
  if (!d || !me) return <Shell roles={["passenger", "redressor", "nodal", "agent", "admin", "manager"]}><Spinner /></Shell>;
  const role = me.role;
  const staff = role === "redressor" || role === "nodal";
  const idx = FLOW.indexOf(d.status === "Resolved" || d.status === "Closed" || d.status === "Provisionally Resolved" ? d.status : ["Reopened", "Escalated", "On Hold - Awaiting Passenger Inputs"].includes(d.status) ? "In-Progress" : d.status);
  return (
    <Shell roles={["passenger", "redressor", "nodal", "agent", "admin", "manager"]} wide>
      <div className="grid gap-5 lg:grid-cols-[1fr_380px]">
        <div className="space-y-4">
          <Card>
            <CardBody className="pt-4">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-bold text-navy">{d.ticket_no}</h1>
                <StatusBadge s={d.status} /> <SevBadge s={d.severity} reason={d.severity_reason} />
                {d.breached && <Badge className="bg-red-600 text-white">SLA breached</Badge>}
                {d.queue === "committee" && <Badge className="bg-purple-600 text-white">Case Closure Committee</Badge>}
                {d.queue === "pacr" && <Badge className="bg-orange-500 text-white">With PACR</Badge>}
                <SourceChip ch={d.source_channel} type={d.source_type} />
                {d.parent_ticket_no && <Badge className="bg-blue-100 text-blue-800">Child of {d.parent_ticket_no}</Badge>}
              </div>
              <ol className="mt-4 flex flex-wrap gap-1 text-xs" aria-label="Lifecycle">
                {FLOW.map((s, i) => (
                  <li key={s} className={`rounded-full px-3 py-1 ${i < idx ? "bg-india text-white" : i === idx ? "bg-navy text-white" : "bg-slate-100 text-slate-500"}`} aria-current={i === idx ? "step" : undefined}>{ts(s as any)}</li>
                ))}
              </ol>
              {d.status === "On Hold - Awaiting Passenger Inputs" && role === "passenger" && <p className="mt-3 rounded bg-yellow-50 p-2 text-sm">{t("holdNote")} <b>{d.hold_reason}</b></p>}
              {["Resolved", "Provisionally Resolved"].includes(d.status) && role === "passenger" && <p className="mt-3 rounded bg-green-50 p-2 text-sm">{t("resolvedNote")}</p>}
              {d.status === "Closed" && role === "passenger" && <p className="mt-3 rounded bg-slate-100 p-2 text-sm">{t("closedNote")}</p>}
            </CardBody>
          </Card>

          <Card>
            <CardHeader><CardTitle>{t("details")}</CardTitle></CardHeader>
            <CardBody>
              <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
                <Row k="Category" v={`${d.category} / ${d.subcategory}`} /><Row k={t("assigned")} v={`${d.assigned_org || "-"} · ${d.team || ""}${d.assigned_user ? ` · ${d.assigned_user}` : ""}`} />
                <Row k={t("level")} v={LVL[d.level]} /><Row k="Created" v={fmtDate(d.created_at)} />
                {d.airline && <Row k="Airline" v={d.airline} />}{d.flight_no && <Row k="Flight" v={d.flight_no} />}
                {d.airport && <Row k="Airport" v={d.airport} />}{d.pnr && <Row k="PNR" v={d.pnr} />}
                {d.service_request_no && <Row k="Service request no." v={d.service_request_no} />}{d.event_at && <Row k="Event time" v={fmtDate(d.event_at)} />}
                <Row k="Contact" v={`${d.contact_name || "-"} · ${d.contact_mobile || ""} ${d.contact_email || ""}`} />
                {d.social_handle && <Row k="Social handle" v={d.social_handle} />}
                {d.confidence != null && <Row k="AI confidence" v={String(d.confidence)} />}
                <Row k="Language" v={d.lang} /><Row k="First response" v={d.first_response_at ? fmtDate(d.first_response_at) : "-"} />
              </dl>
              <div className="mt-3 rounded bg-slate-50 p-3">
                <div className="mb-1 text-xs font-semibold uppercase text-slate-500">Description</div>
                <p className="whitespace-pre-wrap">{d.description}</p>
                {d.lang !== "en" && d.description_en && <p className="mt-2 border-t pt-2 text-sm text-slate-700"><span className="text-xs font-semibold uppercase text-slate-500">Auto-translated to English <Simulated /></span><br />{d.description_en}</p>}
              </div>
              <div className="mt-3 rounded border border-orange-200 bg-orange-50 p-3 text-sm"><b>{t("severityReason")}:</b> {d.severity_reason}</div>
              {d.sla && (
                <div className="mt-3 rounded border p-3 text-sm">
                  <b>{t("sla")}:</b> {d.sla.policy} · L1→L2 {d.sla.e1_hours}h · L2→L3 {d.sla.e2_hours}h · L3→Nodal {d.sla.e3_hours}h
                  {d.sla.state && <div className={`mt-1 font-semibold ${d.sla.state.breached ? "text-red-700" : "text-india-700"}`}>
                    {t("deadline")}: {fmtDate(d.sla.deadline)} · {d.sla.state.breached ? `overdue by ${fmtHours(-d.sla.state.remaining_h)}` : `${fmtHours(d.sla.state.remaining_h)} remaining`}
                  </div>}
                </div>
              )}
              {d.compliance && <div className={`mt-3 rounded border p-3 text-sm ${d.compliance.passed ? "border-green-300 bg-green-50" : "border-red-300 bg-red-50"}`}>
                <b>AI compliance check (CAR/DGCA rule base, illustrative):</b> {d.compliance.passed ? "✔ Passed" : "✘ Failed"} - {d.compliance.reason} {d.compliance.rule && <code className="ml-1 text-xs">[{d.compliance.rule}]</code>}
              </div>}
              {d.resolution_text && <div className="mt-3 rounded bg-green-50 p-3 text-sm"><b>Resolution:</b> {d.resolution_text}</div>}
              {d.children?.length > 0 && <div className="mt-3 text-sm"><b>{t("related")}:</b> {d.children.map((c: any) => <a key={c.ticket_no} className="mr-2 underline text-navy" href={`/tickets/${c.ticket_no}`}>{c.ticket_no}</a>)}</div>}
              {d.related_count > 0 && <p className="mt-2 text-sm"><Badge className="bg-blue-100 text-blue-800">{d.related_count} related posts / follow-ups</Badge></p>}
            </CardBody>
          </Card>

          <Card>
            <CardHeader><CardTitle>{t("timeline")}</CardTitle></CardHeader>
            <CardBody>
              <ol className="relative ml-2 border-l-2 border-slate-200">
                {d.events.map((e: any, i: number) => (
                  <li key={i} className="mb-3 ml-4">
                    <span className={`absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full ${["escalation", "sla_breach", "compliance_fail", "disputed"].includes(e.type) ? "bg-red-500" : e.type === "closed" || e.type === "compliance_pass" ? "bg-india" : "bg-navy"}`} />
                    <div className="text-xs text-slate-500">{fmtDate(e.at)} · {e.actor}{e.to ? <> · <b>{e.to}</b></> : null} · <i>{e.type}</i></div>
                    <div className="text-sm">{e.note}</div>
                  </li>
                ))}
              </ol>
            </CardBody>
          </Card>

          <Card>
            <CardHeader><CardTitle>{t("notifications")}</CardTitle><Simulated /></CardHeader>
            <CardBody className="space-y-2 text-sm">
              {d.notifications.length === 0 && <p className="text-slate-500">No notifications.</p>}
              {d.notifications.map((n: any, i: number) => <div key={i} className="rounded border p-2"><span className="mr-2 rounded bg-slate-100 px-1 text-xs uppercase">{n.channel}</span><span className="text-xs text-slate-500">to {n.to} · {relTime(n.at)}</span><div className="font-medium">{n.subject}</div><div className="text-slate-700">{n.body}</div></div>)}
            </CardBody>
          </Card>
        </div>

        <aside className="space-y-4">
          <Attachments d={d} onChange={load} role={role} />
          {role === "passenger" && <PassengerActions d={d} act={act} t={t} />}
          {staff && <StaffActions d={d} act={act} meta={meta} me={me} reload={load} />}
          {(role === "agent" || role === "admin") && <AgentActions d={d} act={act} meta={meta} />}
          
        </aside>
      </div>
    </Shell>
  );
}

const Row = ({ k, v }: { k: string; v: React.ReactNode }) => <div><dt className="text-xs uppercase text-slate-500">{k}</dt><dd>{v}</dd></div>;

function Attachments({ d, onChange, role }: any) {
  const { push } = useToast();
  async function up(e: React.ChangeEvent<HTMLInputElement>, kind: string) {
    const f = e.target.files?.[0]; if (!f) return;
    const fd = new FormData(); fd.append("file", f); fd.append("kind", kind);
    try { await api(`/tickets/${d.ticket_no}/attachments`, { form: fd }); push("File uploaded", "success"); onChange(); } catch (x: any) { push(x.message, "error"); }
    e.target.value = "";
  }
  return (
    <Card><CardHeader><CardTitle className="text-base">Attachments</CardTitle></CardHeader><CardBody className="space-y-2 text-sm">
      {d.attachments.length === 0 && <p className="text-slate-500">None</p>}
      {d.attachments.map((a: any) => <div key={a.id}><a className="text-navy underline" href={`/api/tickets/${d.ticket_no}/attachments/${a.id}`} target="_blank">{a.filename}</a> <Badge className={a.kind === "evidence" ? "bg-green-100 text-green-800" : "bg-slate-100"}>{a.kind}</Badge> <span className="text-xs text-slate-500">{Math.round(a.size / 1024)} KB</span></div>)}
      <label className="block text-xs text-slate-600">Add file (PDF/JPG/PNG ≤10MB)<Input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => up(e, "upload")} /></label>
      {role !== "passenger" && <label className="block text-xs text-slate-600">Add resolution evidence file<Input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => up(e, "evidence")} /></label>}
    </CardBody></Card>
  );
}

function PassengerActions({ d, act, t }: any) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [msg, setMsg] = useState("");
  const resolved = ["Resolved", "Provisionally Resolved"].includes(d.status);
  return (
    <Card><CardHeader><CardTitle className="text-base">Your options</CardTitle></CardHeader><CardBody className="space-y-4 text-sm">
      {d.status === "On Hold - Awaiting Passenger Inputs" && (
        <div><Field label={t("provideInfo")}>{(i) => <Textarea id={i} value={msg} onChange={(e) => setMsg(e.target.value)} />}</Field>
          <Button className="mt-2" onClick={() => act({ action: "provide_info", note: msg }, "Information sent").then(() => setMsg("")).catch(() => {})}>{t("send")}</Button></div>
      )}
      {resolved && (
        <div className="space-y-2">
          <p className="font-medium">{t("rating")}</p>
          <div role="radiogroup" aria-label="Rating" className="flex gap-1">{[1, 2, 3, 4, 5].map((n) => <button key={n} role="radio" aria-checked={rating === n} aria-label={`${n} star`} onClick={() => setRating(n)} className={`text-3xl ${n <= rating ? "text-saffron" : "text-slate-300"}`}>★</button>)}</div>
          <Textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Comments (optional)" aria-label="Comments" />
          <div className="flex flex-wrap gap-2">
            <Button variant="green" onClick={() => act({ action: "feedback", rating, confirms: true, note: comment }, "Thank you").catch(() => {})}>{t("confirm")}</Button>
            <Button variant="outline" onClick={() => act({ action: "feedback", rating, confirms: false, note: comment }, "Feedback recorded").catch(() => {})}>{t("notSatisfied")}</Button>
          </div>
        </div>
      )}
      {["Resolved", "Provisionally Resolved", "Closed"].includes(d.status) && (
        <div className="space-y-2 border-t pt-3">
          <p className="text-xs text-slate-600">{t("reopensLeft", { n: d.reopen_count, max: d.max_reopens })}</p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" disabled={!d.can_reopen} onClick={() => act({ action: "reopen", note: comment || "Issue persists" }, "Reopened").catch(() => {})}>{t("reopen")}</Button>
            <Button size="sm" variant="outline" onClick={() => act({ action: "dispute", note: comment || "I disagree with the resolution" }, "Referred to Case Closure Committee").catch(() => {})}>{t("dispute")}</Button>
          </div>
          {!d.can_reopen && <p className="text-xs text-amber-800">Reopen limit reached - you can dispute the resolution to refer it to the Case Closure Committee / PACR.</p>}
        </div>
      )}
      {["Assigned", "In-Progress", "Under Assessment", "On Hold - Awaiting Passenger Inputs", "Reopened", "Escalated"].includes(d.status) && d.level < 4 && (
        <div className="border-t pt-3"><Field label={t("reason")}>{(i) => <Input id={i} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Why do you want to escalate?" />}</Field>
          <Button className="mt-2" size="sm" variant="danger" onClick={() => act({ action: "escalate", note: comment }, "Escalated").catch(() => {})}>{t("escalate")}</Button></div>
      )}
    </CardBody></Card>
  );
}

function StaffActions({ d, act, meta, me, reload }: any) {
  const [note, setNote] = useState("");
  const [res, setRes] = useState({ text: "", txn: "", amount: "", ref: "", remedy: true });
  const [sev, setSev] = useState({ v: "", reason: "" });
  const [org, setOrg] = useState("");
  const [add, setAdd] = useState("");
  const [assign, setAssign] = useState("");
  const [fail, setFail] = useState<any>(null);
  const open = ["Assigned", "In-Progress", "Escalated", "Reopened", "On Hold - Awaiting Passenger Inputs"].includes(d.status);
  const canApprove = me.role === "nodal" || me.level === 3;
  return (
    <Card><CardHeader><CardTitle className="text-base">Redressor actions</CardTitle></CardHeader><CardBody className="space-y-4 text-sm">
      {me.access_type === "read" && <p className="rounded bg-yellow-50 p-2">Read-only account.</p>}
      {open && (
        <>
          <div className="space-y-2">
            <Input value={note} onChange={(e) => setNote(e.target.value)} aria-label="Note" placeholder="Note / question for passenger" />
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={() => act({ action: "comment", note }, "Note added").then(() => setNote("")).catch(() => {})}>Add note</Button>
              <Button size="sm" variant="outline" onClick={() => act({ action: "hold", note }, "On hold").then(() => setNote("")).catch(() => {})}>Hold - need passenger input</Button>
              {d.status === "On Hold - Awaiting Passenger Inputs" && <Button size="sm" onClick={() => act({ action: "resume" }, "Resumed").catch(() => {})}>Resume</Button>}
              {d.level < 4 && <Button size="sm" variant="danger" onClick={() => act({ action: "escalate", note }, "Escalated").catch(() => {})}>Escalate</Button>}
            </div>
          </div>
          <form className="space-y-2 rounded border border-green-300 bg-green-50 p-3" onSubmit={async (e) => {
            e.preventDefault(); setFail(null);
            try { await act({ action: "resolve", resolution_text: res.text, txn_id: res.txn || null, reference: res.ref || null, amount: res.amount ? Number(res.amount) : null, remedy_complete: res.remedy }, "Resolved"); }
            catch (x: any) { setFail(x.detail); }
          }}>
            <div className="font-semibold">Resolve (evidence required)</div>
            {d.car_rule && <p className="text-xs text-slate-700">CAR rule applied: {d.car_rule.title} <Simulated text="Illustrative" /></p>}
            <Textarea value={res.text} onChange={(e) => setRes({ ...res, text: e.target.value })} placeholder="Resolution details" aria-label="Resolution details" required />
            <div className="grid grid-cols-2 gap-2">
              <Input value={res.txn} onChange={(e) => setRes({ ...res, txn: e.target.value })} placeholder="Transaction / refund ID" aria-label="Transaction ID" />
              <Input type="number" value={res.amount} onChange={(e) => setRes({ ...res, amount: e.target.value })} placeholder="Amount ₹ (if monetary)" aria-label="Amount" />
            </div>
            <Input value={res.ref} onChange={(e) => setRes({ ...res, ref: e.target.value })} placeholder="Other reference (job no., receipt)" aria-label="Reference" />
            <p className="text-xs text-slate-600">Or upload an evidence file in the Attachments box above.</p>
            <label className="flex items-center gap-2"><input type="checkbox" checked={res.remedy} onChange={(e) => setRes({ ...res, remedy: e.target.checked })} /> Remedy complete (else “Provisionally Resolved”)</label>
            {fail && <div role="alert" className="rounded bg-red-100 p-2 text-red-900">{fail.message || String(fail)}</div>}
            <Button variant="green" size="sm">Resolve</Button>
          </form>
          <div className="space-y-2 border-t pt-3">
            <div className="font-semibold">Divert / add redressor</div>
            <div className="flex gap-2"><Select value={org} onChange={(e) => setOrg(e.target.value)} aria-label="Divert to"><option value="">Divert to…</option>{meta?.orgs.filter((o: any) => !["pacr"].includes(o.type)).map((o: any) => <option key={o.id} value={o.id}>{o.name}</option>)}</Select>
              <Button size="sm" variant="outline" disabled={!org} onClick={() => act({ action: "divert", to_org_id: Number(org), note }, "Diverted").catch(() => {})}>Divert</Button></div>
            <div className="flex gap-2"><Select value={add} onChange={(e) => setAdd(e.target.value)} aria-label="Add redressor"><option value="">Add redressor…</option>{meta?.orgs.map((o: any) => <option key={o.id} value={o.id}>{o.name}</option>)}</Select>
              <Button size="sm" variant="outline" disabled={!add} onClick={() => act({ action: "add_redressor", org_id: Number(add), note }, "Redressor added").catch(() => {})}>Add</Button></div>
          </div>
        </>
      )}
      <div className="space-y-2 border-t pt-3">
        <div className="font-semibold">Severity override (L2+)</div>
        <p className="text-xs text-slate-600">Upgrade is immediate. A downgrade needs approval by L3 / Nodal Officer.</p>
        <div className="flex gap-2"><Select value={sev.v} onChange={(e) => setSev({ ...sev, v: e.target.value })} aria-label="New severity"><option value="">New severity…</option>{[1, 2, 3, 4].map((s) => <option key={s} value={s}>S{s}</option>)}</Select>
          <Input value={sev.reason} onChange={(e) => setSev({ ...sev, reason: e.target.value })} placeholder="Reason" aria-label="Reason" /></div>
        <Button size="sm" variant="outline" disabled={!sev.v || !sev.reason} onClick={() => act({ action: "severity", severity: Number(sev.v), note: sev.reason }, "Severity request processed").catch(() => {})}>Apply</Button>
        {d.downgrade_request && (
          <div className="rounded border border-amber-300 bg-amber-50 p-2">Downgrade to S{d.downgrade_request.to} requested by {d.downgrade_request.by}: {d.downgrade_request.reason}
            {canApprove && <div className="mt-1 flex gap-2"><Button size="sm" onClick={() => act({ action: "approve_downgrade" }, "Downgrade approved").catch(() => {})}>Approve</Button><Button size="sm" variant="outline" onClick={() => act({ action: "reject_downgrade", note: "Rejected" }, "Rejected").catch(() => {})}>Reject</Button></div>}
          </div>
        )}
      </div>
      {(me.role === "nodal" || me.level === 3) && d.staff_in_org?.length > 0 && (
        <div className="flex gap-2 border-t pt-3"><Select value={assign} onChange={(e) => setAssign(e.target.value)} aria-label="Assign to"><option value="">Assign to staff…</option>{d.staff_in_org.map((s: any) => <option key={s.id} value={s.id}>{s.name} (L{s.level})</option>)}</Select>
          <Button size="sm" variant="outline" disabled={!assign} onClick={() => act({ action: "assign", user_id: Number(assign) }, "Assigned").catch(() => {})}>Assign</Button></div>
      )}
    </CardBody></Card>
  );
}

function AgentActions({ d, act, meta, committeeOnly }: any) {
  const [f, setF] = useState<any>({ category: "", subcategory: "", severity: "", to_org_id: "", note: "" });
  const [parent, setParent] = useState("");
  const [note, setNote] = useState("");
  const subs = meta?.subcategories?.[f.category || d.category] || [];
  return (
    <Card><CardHeader><CardTitle className="text-base">{committeeOnly ? "Case Closure Committee" : "AirSewa Agent actions"}</CardTitle></CardHeader><CardBody className="space-y-4 text-sm">
      {d.queue === "committee" && (
        <div className="space-y-2 rounded border border-purple-300 bg-purple-50 p-3">
          <b>Disputed closure - committee decision</b>
          <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Decision note" aria-label="Decision note" />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="green" onClick={() => act({ action: "committee", decision: "uphold", note }, "Closed (resolution upheld)").catch(() => {})}>Uphold & close</Button>
            <Button size="sm" variant="danger" onClick={() => act({ action: "committee", decision: "reinstate", note }, "Reinstated to stakeholder").catch(() => {})}>Reinstate</Button>
            <Button size="sm" variant="outline" onClick={() => act({ action: "committee", decision: "ingenuine", note }, "Closed as not genuine").catch(() => {})}>Close - ingenuine</Button>
          </div>
        </div>
      )}
      {!committeeOnly && (
        <>
          <div className="space-y-2">
            <div className="font-semibold">Override classification / allocation / severity</div>
            <div className="grid grid-cols-2 gap-2">
              <Select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value, subcategory: "" })} aria-label="Category"><option value="">Category: {d.category}</option>{Object.keys(meta?.categories || {}).map((c) => <option key={c}>{c}</option>)}</Select>
              <Select value={f.subcategory} onChange={(e) => setF({ ...f, subcategory: e.target.value })} aria-label="Subcategory"><option value="">Sub: {d.subcategory}</option>{subs.map((c: string) => <option key={c}>{c}</option>)}</Select>
              <Select value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value })} aria-label="Severity"><option value="">Severity: S{d.severity}</option>{[1, 2, 3, 4].map((s) => <option key={s} value={s}>S{s}</option>)}</Select>
              <Select value={f.to_org_id} onChange={(e) => setF({ ...f, to_org_id: e.target.value })} aria-label="Assign to"><option value="">Org: {d.assigned_org}</option>{meta?.orgs.map((o: any) => <option key={o.id} value={o.id}>{o.name}</option>)}</Select>
            </div>
            <Input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} placeholder="Reason for override" aria-label="Reason" />
            <Button size="sm" variant="danger" onClick={() => act({ action: "escalate", note: f.note }, "Escalated one level").catch(() => {})}>Escalate +1 level</Button> <Button size="sm" onClick={() => act({ action: "reclassify", category: f.category || null, subcategory: f.subcategory || null, severity: f.severity ? Number(f.severity) : null, to_org_id: f.to_org_id ? Number(f.to_org_id) : null, note: f.note }, "Override applied").catch(() => {})}>Apply override</Button>
          </div>
          <div className="space-y-2 border-t pt-3">
            <div className="font-semibold">Merge as child of (parent ticket ID)</div>
            <div className="flex gap-2"><Input value={parent} onChange={(e) => setParent(e.target.value)} placeholder="AS-2026-000123" aria-label="Parent ticket" /><Button size="sm" variant="outline" disabled={!parent} onClick={() => act({ action: "merge", parent_ref: parent, note: "Duplicate follow-up" }, "Merged").catch(() => {})}>Merge</Button></div>
          </div>
          <div className="space-y-2 border-t pt-3">
            <div className="font-semibold">Closure re-verification</div>
            <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Verification note" aria-label="Verification note" />
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="green" disabled={!["Resolved", "Closed", "Provisionally Resolved"].includes(d.status)} onClick={() => act({ action: "reverify", ok: true, note }, "Verified").catch(() => {})}>Verified OK</Button>
              <Button size="sm" variant="danger" disabled={!["Resolved", "Closed", "Provisionally Resolved"].includes(d.status)} onClick={() => act({ action: "reverify", ok: false, note }, "Reinstated").catch(() => {})}>Wrongful closure - reinstate</Button>
              <Button size="sm" variant="outline" onClick={() => act({ action: "to_committee", note }, "Referred").catch(() => {})}>Refer to committee</Button>
            </div>
          </div>
        </>
      )}
    </CardBody></Card>
  );
}

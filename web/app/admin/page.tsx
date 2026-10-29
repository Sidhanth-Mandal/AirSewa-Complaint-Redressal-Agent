"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Shell } from "@/components/Shell";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Input, Select, Simulated, Spinner, Tabs } from "@/components/ui";
import { api, qs } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import { useSession } from "@/lib/session";
import { fmtHours } from "@/lib/utils";

const C = ["#0b3d91", "#ff9933", "#138808", "#dc2626", "#7c3aed", "#0891b2", "#ca8a04", "#64748b", "#db2777"];
const fmtKpi = (v: any, suffix = "") => (v === undefined || v === null ? "-" : `${v}${suffix}`);

function Kpi({ label, value, sub, tone }: { label: string; value: any; sub?: string; tone?: "red" | "green" | "navy" }) {
  return (
    <Card><CardBody className="pt-3">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`text-2xl font-bold ${tone === "red" ? "text-red-600" : tone === "green" ? "text-india-700" : "text-navy"}`}>{value}</div>
      {sub && <div className="text-xs text-slate-500">{sub}</div>}
    </CardBody></Card>
  );
}
const CC = ({ title, children, h = 260, right, className }: { title: string; children: React.ReactNode; h?: number; right?: React.ReactNode; className?: string }) => (
  <Card className={className}><CardHeader><CardTitle className="text-base">{title}</CardTitle>{right}</CardHeader><CardBody><div style={{ height: h }}><ResponsiveContainer>{children as any}</ResponsiveContainer></div></CardBody></Card>
);

export default function Dashboard() {
  const { me } = useSession();
  const [meta, setMeta] = useState<any>(null);
  const [f, setF] = useState<Record<string, any>>({ preset: "365" });
  const [s, setS] = useState<any>(null);
  const [pulse, setPulse] = useState<any>(null);
  const [fc, setFc] = useState<any>(null);
  const [tab, setTab] = useState("overview");
  const [seats, setSeats] = useState(12);
  const [wi, setWi] = useState<any>(null);
  const [live, setLive] = useState(0);

  const params = useMemo(() => {
    const p: any = { airport: f.airport, channel: f.channel, category: f.category, severity: f.severity, status: f.status, org: f.org, lang: f.lang };
    if (f.preset === "custom") { p.from = f.from; p.to = f.to; }
    else if (f.preset !== "all") { const d = new Date(Date.now() - Number(f.preset) * 86400000); p.from = d.toISOString().slice(0, 10); }
    return p;
  }, [f]);
  const load = useCallback(() => api(`/dashboard/summary${qs(params)}`).then(setS), [params]);
  const loadPulse = useCallback(() => api("/dashboard/social-pulse").then(setPulse).catch(() => {}), []);
  useEffect(() => { api("/meta").then(setMeta); api("/dashboard/forecast").then(setFc).catch(() => {}); }, []);
  useEffect(() => { load(); loadPulse(); }, [load, loadPulse]);
  const debounce = useRef<any>(undefined);
  useSSE(["tickets", "social_pulse"], (n) => { setLive((x) => x + 1); clearTimeout(debounce.current); debounce.current = setTimeout(() => { load(); if (n === "social_pulse") loadPulse(); }, 800); });
  useEffect(() => { if (me?.role === "manager" || me?.role === "admin") api(`/manager/whatif?seats=${seats}`).then(setWi).catch(() => {}); }, [seats, me]);

  const k = s?.kpis;
  const exportUrl = (fmt: string) => `/api/dashboard/export${qs({ fmt, ...params })}`;
  const sel = (key: string, label: string, opts: [string, string][]) => (
    <Select aria-label={label} value={f[key] || ""} onChange={(e) => setF({ ...f, [key]: e.target.value || undefined })} className="!min-h-[38px] text-sm"><option value="">{label}: all</option>{opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select>
  );
  return (
    <Shell roles={["admin", "agent", "manager", "nodal"]} wide>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div><h1 className="text-2xl font-bold text-navy">MoCA / AAI Dashboard</h1><p className="text-xs text-slate-500">Live: updates arrive over SSE ({live} events since load){me?.role === "nodal" ? " · Showing your organisation only" : ""}</p></div>
        <div className="flex gap-2">{["csv", "xlsx", "pdf"].map((x) => <a key={x} href={exportUrl(x)}><Button size="sm" variant="outline">⬇ {x.toUpperCase()}</Button></a>)}<Button size="sm" onClick={load}>Refresh</Button></div>
      </div>
      <Card className="mb-4"><CardBody className="grid grid-cols-2 gap-2 pt-3 md:grid-cols-5 xl:grid-cols-9">
        <Select aria-label="Time range" value={f.preset} onChange={(e) => setF({ ...f, preset: e.target.value })} className="!min-h-[38px] text-sm"><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option><option value="365">Last 12 months</option><option value="all">All</option><option value="custom">Custom…</option></Select>
        {f.preset === "custom" && <><Input type="date" aria-label="From" value={f.from || ""} onChange={(e) => setF({ ...f, from: e.target.value })} className="!min-h-[38px]" /><Input type="date" aria-label="To" value={f.to || ""} onChange={(e) => setF({ ...f, to: e.target.value })} className="!min-h-[38px]" /></>}
        {sel("airport", "Airport", (meta?.airports || []).map((a: any) => [a.code, `${a.city} (${a.code})`]))}
        {sel("channel", "Channel", ["portal", "social_x", "social_instagram", "whatsapp", "email", "ivr", "cpgrams", "letter"].map((x) => [x, x]))}
        {sel("category", "Category", Object.keys(meta?.categories || {}).map((x) => [x, x]))}
        {sel("severity", "Priority", [1, 2, 3, 4].map((x) => [String(x), `S${x}`]))}
        {sel("status", "Status", (meta?.statuses || []).map((x: string) => [x, x]))}
        {me?.role !== "nodal" && sel("org", "Stakeholder", (meta?.orgs || []).map((o: any) => [o.code, o.name]))}
        {sel("lang", "Language", [["en", "English"], ["hinglish", "Hinglish"], ["hi", "Hindi"]])}
      </CardBody></Card>
      {!s ? <Spinner /> : (
        <>
          {s.alerts.length > 0 && <div role="alert" className="mb-3 space-y-1">{s.alerts.map((a: any, i: number) => <div key={i} className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm">⚠ {a.text}</div>)}</div>}
          <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
            <Kpi label="Total grievances" value={k.total.toLocaleString()} /><Kpi label="Pending" value={k.pending} tone="red" sub={`${k.critical_open} critical open`} />
            <Kpi label="Resolved" value={k.resolved.toLocaleString()} tone="green" sub={`${k.closed} closed`} /><Kpi label="Reopened" value={k.reopened} sub={`${fmtKpi(k.reopen_rate, "%")} reopen rate`} />
            <Kpi label="SLA breach" value={fmtKpi(k.sla_breach_pct, "%")} tone="red" sub={`${k.breached} tickets`} /><Kpi label="Escalation rate" value={fmtKpi(k.escalation_rate, "%")} />
            <Kpi label="FCR" value={fmtKpi(k.fcr_pct, "%")} sub="first contact resolution" /><Kpi label="CSAT" value={`${k.csat}/5`} /><Kpi label="Avg TAT" value={fmtHours(k.avg_tat_h)} sub={`1st response ${fmtHours(k.avg_first_response_h)}`} />
            <Kpi label="Sentiment" value={k.sentiment} sub="NLP score -1…+1" /><Kpi label="Transfer rate" value={k.transfer_rate} sub="avg hops" /><Kpi label="Committee / PACR" value={`${k.committee_queue} / ${k.pacr_queue}`} sub="disputed / SLA-escalated" />
          </div>
          <Tabs value={tab} onChange={setTab} className="mb-4" tabs={[{ id: "overview", label: "Overview" }, { id: "sla", label: "SLA & performance" }, { id: "queue", label: "Live queue" }, { id: "geo", label: "Geography" }, { id: "cohorts", label: "Cohorts & watchlist" }, { id: "social", label: "Social Media Pulse" }, { id: "predict", label: "Predictive" }, { id: "quality", label: "Quality & channels" }]} />

          {tab === "overview" && (
            <div className="grid gap-4 lg:grid-cols-2">
              <CC title="Category-wise complaints"><BarChart data={s.by_category}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Bar dataKey="count" fill={C[0]}>{s.by_category.map((_: any, i: number) => <Cell key={i} fill={C[i % C.length]} />)}</Bar></BarChart></CC>
              <CC title="Daily trend (last 45 days)"><LineChart data={s.trend_daily}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} /><YAxis /><Tooltip /><Legend /><Line dataKey="tickets" stroke={C[0]} dot={false} /><Line dataKey="resolved" stroke={C[2]} dot={false} /><Line dataKey="breached" stroke={C[3]} dot={false} /></LineChart></CC>
              <CC title="Monthly volume & growth rate"><ComposedChart data={s.trend_monthly}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="month" /><YAxis yAxisId="l" /><YAxis yAxisId="r" orientation="right" unit="%" /><Tooltip /><Legend /><Bar yAxisId="l" dataKey="tickets" fill={C[0]} /><Bar yAxisId="l" dataKey="breached" fill={C[3]} /><Line yAxisId="r" dataKey="growth_pct" stroke={C[1]} name="growth %" /></ComposedChart></CC>
              <CC title="Resolved vs pending vs reopened (status mix)"><PieChart><Pie data={s.status_mix} dataKey="count" nameKey="name" outerRadius={90}>{s.status_mix.map((_: any, i: number) => <Cell key={i} fill={C[i % C.length]} />)}</Pie><Tooltip /><Legend /></PieChart></CC>
              <Card className="lg:col-span-2"><CardHeader><CardTitle className="text-base">Stakeholder-wise complaints, pendency and SLA</CardTitle></CardHeader><CardBody className="overflow-x-auto">
                <table className="w-full min-w-[700px] text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th className="py-1">Stakeholder</th><th>Type</th><th>Total</th><th>Pending</th><th>Resolved</th><th>Breach %</th><th>Avg TAT</th></tr></thead>
                  <tbody>{s.stakeholders.map((x: any) => <tr key={x.name} className="border-t"><td className="py-1.5">{x.name}</td><td className="text-slate-500">{x.type}</td><td>{x.total}</td><td>{x.pending}</td><td>{x.resolved}</td>
                    <td><Badge className={x.breach_pct > 30 ? "bg-red-100 text-red-800" : x.breach_pct > 20 ? "bg-amber-100 text-amber-900" : "bg-green-100 text-green-800"}>{x.breach_pct}%</Badge></td><td>{fmtHours(x.avg_tat_h)}</td></tr>)}</tbody></table>
              </CardBody></Card>
              <CC title="Priority mix"><BarChart data={s.severity_mix}><XAxis dataKey="name" /><YAxis /><Tooltip /><Bar dataKey="count">{s.severity_mix.map((_: any, i: number) => <Cell key={i} fill={["#dc2626", "#f97316", "#fbbf24", "#94a3b8"][i]} />)}</Bar></BarChart></CC>
              <CC title="Subcategory (top 15)" h={300}><BarChart data={s.by_subcategory} layout="vertical" margin={{ left: 60 }}><XAxis type="number" /><YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="count" fill={C[5]} /></BarChart></CC>
            </div>
          )}

          {tab === "sla" && (
            <div className="grid gap-4 lg:grid-cols-2">
              <CC title="TAT distribution (resolved)"><BarChart data={s.tat_distribution}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="bucket" /><YAxis /><Tooltip /><Bar dataKey="count" fill={C[0]} /></BarChart></CC>
              <CC title="Resolved early / within TAT / delayed"><PieChart><Pie data={s.resolution_timing} dataKey="count" nameKey="name" outerRadius={90} label>{s.resolution_timing.map((_: any, i: number) => <Cell key={i} fill={[C[2], C[0], C[3]][i]} />)}</Pie><Tooltip /><Legend /></PieChart></CC>
              <CC title="SLA breach % by stakeholder"><BarChart data={[...s.stakeholders].filter((x: any) => x.total >= 20).sort((a: any, b: any) => b.breach_pct - a.breach_pct).slice(0, 12)} layout="vertical" margin={{ left: 70 }}><XAxis type="number" unit="%" /><YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="breach_pct" fill={C[3]} /></BarChart></CC>
              <CC title="Volume vs SLA attainment (daily)"><ComposedChart data={s.trend_daily}><XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} /><YAxis yAxisId="l" /><YAxis yAxisId="r" orientation="right" domain={[0, 100]} unit="%" /><Tooltip /><Legend /><Bar yAxisId="l" dataKey="tickets" fill={C[0]} /><Line yAxisId="r" dataKey="sla_attainment" stroke={C[2]} dot={false} name="SLA attainment" /></ComposedChart></CC>
              <CC title="Pareto - top categories by volume"><ComposedChart data={s.pareto_volume}><XAxis dataKey="name" tick={{ fontSize: 9 }} interval={0} angle={-25} textAnchor="end" height={70} /><YAxis yAxisId="l" /><YAxis yAxisId="r" orientation="right" domain={[0, 100]} unit="%" /><Tooltip /><Bar yAxisId="l" dataKey="count" fill={C[0]} /><Line yAxisId="r" dataKey="cum_pct" stroke={C[1]} name="cumulative %" /></ComposedChart></CC>
              <CC title="Pareto - categories by SLA breaches"><ComposedChart data={s.pareto_breach}><XAxis dataKey="name" tick={{ fontSize: 9 }} interval={0} angle={-25} textAnchor="end" height={70} /><YAxis yAxisId="l" /><YAxis yAxisId="r" orientation="right" domain={[0, 100]} unit="%" /><Tooltip /><Bar yAxisId="l" dataKey="count" fill={C[3]} /><Line yAxisId="r" dataKey="cum_pct" stroke={C[1]} name="cumulative %" /></ComposedChart></CC>
              <CC title="Escalations by level" h={220}><BarChart data={s.escalations.by_level}><XAxis dataKey="level" /><YAxis /><Tooltip /><Bar dataKey="count" fill={C[4]} /></BarChart></CC>
              <Card><CardHeader><CardTitle className="text-base">Escalation summary</CardTitle></CardHeader><CardBody className="text-sm"><p>{s.escalations.total} tickets escalated beyond L1 ({k.escalation_rate}%).</p><p>Avg resolution time of escalated tickets: <b>{fmtHours(s.escalations.avg_resolution_h)}</b></p></CardBody></Card>
              <Card><CardHeader><CardTitle className="text-base">Officer-wise pendency</CardTitle></CardHeader><CardBody><table className="w-full text-sm"><tbody>{s.officer_pendency.map((o: any) => <tr key={o.officer} className="border-t"><td className="py-1">{o.officer}</td><td>L{o.level}</td><td className="text-right font-semibold">{o.pending}</td></tr>)}</tbody></table></CardBody></Card>
              <CC title="Airline avg response time (h) - comparison"><BarChart data={s.agency_response}><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis /><Tooltip /><Bar dataKey="avg_tat_h" fill={C[1]} name="avg TAT (h)" /></BarChart></CC>
            </div>
          )}

          {tab === "queue" && (
            <div className="grid gap-4 lg:grid-cols-2">
              <CC title="Live queue - inflow vs outflow (last 24h)"><AreaChart data={s.live_queue.hourly}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="hour" /><YAxis allowDecimals={false} /><Tooltip /><Legend /><Area dataKey="inflow" stroke={C[0]} fill={C[0]} fillOpacity={0.3} /><Area dataKey="outflow" stroke={C[2]} fill={C[2]} fillOpacity={0.3} /></AreaChart></CC>
              <CC title="Backlog ageing buckets (open tickets)"><BarChart data={s.live_queue.ageing}><XAxis dataKey="bucket" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="count" fill={C[3]} /></BarChart></CC>
              <Card><CardHeader><CardTitle className="text-base">Active vs inactive queue</CardTitle></CardHeader><CardBody className="text-sm"><p>Active (open + awaiting confirmation): <b>{s.live_queue.active}</b></p><p>Inactive (closed): <b>{s.live_queue.inactive}</b></p></CardBody></Card>
              <Card><CardHeader><CardTitle className="text-base">Queue time by priority (avg age of open)</CardTitle></CardHeader><CardBody><table className="w-full text-sm"><tbody>{s.live_queue.queue_time_by_severity.map((x: any) => <tr key={x.severity} className="border-t"><td className="py-1">{x.severity}</td><td className="text-right">{fmtHours(x.avg_age_h)}</td></tr>)}</tbody></table></CardBody></Card>
            </div>
          )}

          {tab === "geo" && (
            <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
              <Card><CardHeader><CardTitle className="text-base">Grievance density by airport (grid map, N→S / W→E)</CardTitle><Simulated text="Schematic map" /></CardHeader><CardBody><GridMap data={s.airport_map} /></CardBody></Card>
              <div className="space-y-4">
                <Card><CardHeader><CardTitle className="text-base">State-wise grievances & SLA</CardTitle></CardHeader><CardBody><table className="w-full text-sm"><tbody>{s.state_map.map((x: any) => <tr key={x.state} className="border-t"><td className="py-1">{x.state}</td><td>{x.tickets}</td><td className="text-right"><Badge className={x.breach_pct > 30 ? "bg-red-100 text-red-800" : "bg-green-100 text-green-800"}>{x.breach_pct}% breach</Badge></td></tr>)}</tbody></table></CardBody></Card>
                <Card><CardBody className="pt-4 text-sm">Major airports: <b>{s.major_vs_small.major}</b> · Smaller airports: <b>{s.major_vs_small.smaller}</b></CardBody></Card>
              </div>
            </div>
          )}

          {tab === "cohorts" && (
            <div className="grid gap-4 lg:grid-cols-2">
              <CohortTable title="Breach cohorts (category × location × priority) - most SLA misses" rows={s.breach_cohorts} />
              <CohortTable title="Complaint cohorts - most complaints" rows={s.complaint_cohorts} />
              <Card className="lg:col-span-2"><CardHeader><CardTitle className="text-base">Watchlist - chronic stakeholders (≥25% breaches, ≥20 tickets)</CardTitle></CardHeader><CardBody>
                {s.watchlist.length === 0 ? <p className="text-sm text-slate-500">None for this filter.</p> : <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{s.watchlist.map((w: any) => <li key={w.name} className="rounded border border-red-200 bg-red-50 p-2 text-sm"><b>{w.name}</b><br />{w.breach_pct}% breached of {w.total}</li>)}</ul>}
              </CardBody></Card>
            </div>
          )}

          {tab === "social" && pulse && (
            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="lg:col-span-2"><CardBody className="flex flex-wrap items-center gap-6 pt-4"><div><div className="text-xs uppercase text-slate-500">Complaints (30d)</div><div className="text-3xl font-bold text-navy">{pulse.total}</div></div><div><div className="text-xs uppercase text-slate-500">Filtered (spam/praise)</div><div className="text-3xl font-bold">{pulse.filtered}</div></div><div><div className="text-xs uppercase text-slate-500">Viral threads</div><div className="text-3xl font-bold text-fuchsia-600">{pulse.viral}</div></div><Simulated text="Simulated X / Instagram" /></CardBody></Card>
              <CC title="Volume by platform and source type"><BarChart data={pulse.by_platform.map((x: any) => ({ ...x, name: `${x.platform}/${x.source_type}` }))}><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis /><Tooltip /><Bar dataKey="count" fill={C[4]} /></BarChart></CC>
              <CC title="Sentiment trend (social)"><LineChart data={pulse.sentiment_trend}><XAxis dataKey="date" tickFormatter={(d) => d.slice(5)} /><YAxis domain={[-1, 1]} /><Tooltip /><Line dataKey="sentiment" stroke={C[3]} dot={false} /></LineChart></CC>
              <CC title="Top airlines by complaints"><BarChart data={pulse.top_airlines} layout="vertical" margin={{ left: 60 }}><XAxis type="number" /><YAxis type="category" dataKey="name" width={110} /><Tooltip /><Bar dataKey="count" fill={C[0]} /></BarChart></CC>
              <CC title="Top airports by complaints"><BarChart data={pulse.top_airports}><XAxis dataKey="name" /><YAxis /><Tooltip /><Bar dataKey="count" fill={C[1]} /></BarChart></CC>
              <Card className="lg:col-span-2"><CardHeader><CardTitle className="text-base">Trending hashtags</CardTitle></CardHeader><CardBody className="flex flex-wrap gap-2">{pulse.hashtags.map((h: any) => <Badge key={h.tag} className="bg-navy-50 text-navy">{h.tag} · {h.count}</Badge>)}</CardBody></Card>
            </div>
          )}

          {tab === "predict" && (
            <div className="grid gap-4 lg:grid-cols-2">
              {fc && <CC title="Ticket volume forecast (weekly)" right={<Badge className="bg-slate-100">{fc.method}</Badge>}><ComposedChart data={[...fc.history.map((h: any) => ({ week: h.week, actual: h.tickets })), ...fc.forecast.map((x: any) => ({ week: x.week, forecast: x.forecast }))]}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="week" tickFormatter={(d) => d.slice(5)} /><YAxis /><Tooltip /><Legend /><Line dataKey="actual" stroke={C[0]} dot={false} /><Line dataKey="forecast" stroke={C[1]} strokeDasharray="5 3" /></ComposedChart></CC>}
              {fc && <Card><CardHeader><CardTitle className="text-base">SLA-breach risk by category</CardTitle></CardHeader><CardBody><table className="w-full text-sm"><tbody>{fc.breach_risk.map((r: any) => <tr key={r.category} className="border-t"><td className="py-1.5">{r.category}</td><td>{r.breach_rate_pct}%</td><td className="text-right"><Badge className={r.risk === "High" ? "bg-red-100 text-red-800" : r.risk === "Medium" ? "bg-amber-100 text-amber-900" : "bg-green-100 text-green-800"}>{r.risk}</Badge></td></tr>)}</tbody></table></CardBody></Card>}
              <Card className="lg:col-span-2"><CardHeader><CardTitle className="text-base">What-if: PACR seats <Simulated text="Simulated model" /></CardTitle></CardHeader><CardBody>
                <label className="block text-sm">PACR seats: <b>{seats}</b><input type="range" min={4} max={30} value={seats} onChange={(e) => setSeats(Number(e.target.value))} className="w-full" aria-label="PACR seats" /></label>
                {wi && <p className="mt-2 text-sm">Expected PU / seat / shift: <b>{wi.expected_pu_per_seat_shift}</b> (target 60) · penalty per shift ₹{wi.penalty_per_shift} · est. monthly penalty ₹{wi.monthly_penalty_estimate.toLocaleString()} · est. seat cost ₹{wi.monthly_cost_estimate.toLocaleString()}/month <span className="text-xs text-slate-500">({wi.note})</span></p>}
              </CardBody></Card>
            </div>
          )}

          {tab === "quality" && (
            <div className="grid gap-4 lg:grid-cols-2">
              <CC title="Sentiment vs CSAT (weekly)"><ComposedChart data={s.sentiment_trend}><XAxis dataKey="week" tickFormatter={(d) => d.slice(5)} /><YAxis yAxisId="l" domain={[-1, 1]} /><YAxis yAxisId="r" orientation="right" domain={[0, 5]} /><Tooltip /><Legend /><Line yAxisId="l" dataKey="sentiment" stroke={C[3]} dot={false} /><Line yAxisId="r" dataKey="csat" stroke={C[2]} dot={false} /></ComposedChart></CC>
              <CC title="Channel mix"><PieChart><Pie data={s.channel_mix} dataKey="count" nameKey="name" outerRadius={90} label={(e: any) => e.name}>{s.channel_mix.map((_: any, i: number) => <Cell key={i} fill={C[i % C.length]} />)}</Pie><Tooltip /></PieChart></CC>
              <CC title="Channel trend over time (stacked)"><AreaChart data={s.channel_trend}><XAxis dataKey="month" /><YAxis /><Tooltip /><Legend />{["portal", "social_x", "social_instagram", "whatsapp", "email", "ivr", "cpgrams", "letter"].map((c, i) => <Area key={c} dataKey={c} stackId="1" stroke={C[i]} fill={C[i]} />)}</AreaChart></CC>
              <Card><CardHeader><CardTitle className="text-base">Language-wise performance</CardTitle></CardHeader><CardBody><table className="w-full text-sm"><tbody>{s.language.map((l: any) => <tr key={l.lang} className="border-t"><td className="py-1">{l.lang}</td><td>{l.count}</td><td className="text-right">TAT {fmtHours(l.avg_tat_h)}</td></tr>)}</tbody></table></CardBody></Card>
              <CC title="Reopen reasons (by subcategory)"><BarChart data={s.reopen_reasons}><XAxis dataKey="name" tick={{ fontSize: 10 }} /><YAxis /><Tooltip /><Bar dataKey="count" fill={C[8]} /></BarChart></CC>
            </div>
          )}
        </>
      )}
    </Shell>
  );
}

function CohortTable({ title, rows }: { title: string; rows: any[] }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <Card><CardHeader><CardTitle className="text-base">{title}</CardTitle></CardHeader><CardBody><table className="w-full text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th>Category</th><th>Airport</th><th>Priority</th><th>Count</th><th>Share</th></tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i} className="border-t"><td className="py-1">{r.category}</td><td>{r.airport}</td><td>{r.priority}</td><td><div className="flex items-center gap-2"><span className="h-2 rounded bg-red-500" style={{ width: `${(r.count / max) * 80}px` }} />{r.count}</div></td><td>{r.share_pct}%</td></tr>)}</tbody></table></CardBody></Card>
  );
}

function GridMap({ data }: { data: any[] }) {
  const max = Math.max(1, ...data.map((d) => d.tickets));
  const cells: Record<string, any> = {};
  data.forEach((d) => (cells[`${d.row}-${d.col}`] = d));
  return (
    <div role="img" aria-label="Schematic grid map of airports coloured by grievance volume" className="grid gap-1" style={{ gridTemplateColumns: "repeat(7, minmax(0,1fr))" }}>
      {Array.from({ length: 9 * 7 }).map((_, i) => {
        const r = Math.floor(i / 7), c = i % 7; const d = cells[`${r}-${c}`];
        if (!d) return <div key={i} className="h-14 rounded bg-slate-50" />;
        const a = 0.15 + 0.85 * (d.tickets / max);
        return (
          <div key={i} title={`${d.city}: ${d.tickets} grievances, ${d.breach_pct}% SLA breach, ${d.pending} pending`} tabIndex={0}
            className="flex h-14 flex-col items-center justify-center rounded border text-center text-xs" style={{ background: `rgba(11,61,145,${a})`, color: a > 0.5 ? "#fff" : "#0f172a", borderColor: d.breach_pct > 30 ? "#dc2626" : "transparent", borderWidth: 2 }}>
            <b>{d.code}</b><span>{d.tickets}</span>
          </div>
        );
      })}
      <p className="col-span-7 mt-1 text-xs text-slate-500">Colour = grievance volume. Red border = SLA breach &gt; 30%.</p>
    </div>
  );
}

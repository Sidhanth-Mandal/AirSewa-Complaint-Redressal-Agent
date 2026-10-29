"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Shell } from "@/components/Shell";
import { SevBadge } from "@/components/badges";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Select, Tabs, Textarea, useToast } from "@/components/ui";
import { api } from "@/lib/api";

const TARGETS = ["airline", "airport_operator", "gsp", "regulator", "aai", "ota"];

export default function Rules() {
  const { push } = useToast();
  const [tab, setTab] = useState("alloc");
  const [data, setData] = useState<any>({ rules: [], severity: [] });
  const [meta, setMeta] = useState<any>(null);
  const [q, setQ] = useState("");
  const blank = { keyword: "", category: "flight", subcategory: "other", target_type: "airline", target_org_code: "", weight: 1, active: true };
  const [r, setR] = useState<any>(blank);
  const [editing, setEditing] = useState<number | null>(null);
  const [sv, setSv] = useState({ keyword: "", severity: 1 });
  const [test, setTest] = useState({ text: "My father's medicine was in the checked bag and the airline lost my baggage", res: null as any });
  const load = useCallback(() => api("/admin/rules").then(setData), []);
  useEffect(() => { load(); api("/meta").then(setMeta); }, [load]);
  const rules = useMemo(() => data.rules.filter((x: any) => !q || x.keyword.includes(q.toLowerCase()) || x.subcategory.includes(q)), [data, q]);
  const sevs = useMemo(() => data.severity.filter((x: any) => !q || x.keyword.includes(q.toLowerCase())), [data, q]);
  const wrap = (p: Promise<any>, msg: string) => p.then(() => { push(msg, "success"); load(); }).catch((e) => push(e.message, "error"));
  async function runTest() {
    try { setTest({ ...test, res: await api("/admin/rules/test", { body: { text: test.text } }) }); } catch (e: any) { push(e.message, "error"); }
  }
  return (
    <Shell roles={["admin", "agent"]} wide>
      <h1 className="mb-1 text-2xl font-bold text-navy">Allocation rules & severity matrix</h1>
      <p className="mb-3 text-sm text-slate-600">Configured at runtime - no code change. The same engine classifies portal grievances, social posts and every PACR channel. Changes apply immediately.</p>
      <Card className="mb-4"><CardHeader><CardTitle className="text-base">Try the engine</CardTitle></CardHeader><CardBody className="space-y-2">
        <Textarea aria-label="Test text" value={test.text} onChange={(e) => setTest({ ...test, text: e.target.value })} />
        <Button onClick={runTest}>Classify</Button>
        {test.res && <div className="rounded border bg-slate-50 p-3 text-sm">
          <p>Language: <b>{test.res.lang}</b>{test.res.lang !== "en" && <> → “{test.res.translated}”</>}</p>
          <p>Category: <b>{test.res.category}/{test.res.subcategory}</b> → <b>{test.res.target_type}</b> {test.res.target_org_code && `(${test.res.target_org_code})`} · confidence {test.res.confidence} · sentiment {test.res.sentiment}</p>
          <p><SevBadge s={test.res.severity} /> {test.res.severity_reason}</p>
          <p className="text-xs text-slate-600">Matched: {test.res.matched_keywords.join(", ")} · Entities: {JSON.stringify(test.res.entities)}</p>
        </div>}
      </CardBody></Card>
      <Tabs value={tab} onChange={setTab} tabs={[{ id: "alloc", label: `Keyword → category → redressor (${data.rules.length})` }, { id: "sev", label: `Severity matrix S1–S4 (${data.severity.length})` }]} />
      <div className="my-3 max-w-sm"><Input aria-label="Filter" placeholder="Filter keywords…" value={q} onChange={(e) => setQ(e.target.value)} /></div>
      {tab === "alloc" ? (
        <div className="grid gap-4 xl:grid-cols-[340px_1fr]">
          <Card className="h-fit"><CardHeader><CardTitle className="text-base">{editing ? "Edit rule" : "Add rule"}</CardTitle></CardHeader><CardBody className="space-y-3">
            <Field label="Keyword / phrase">{(i) => <Input id={i} value={r.keyword} onChange={(e) => setR({ ...r, keyword: e.target.value })} />}</Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Category">{(i) => <Select id={i} value={r.category} onChange={(e) => setR({ ...r, category: e.target.value, subcategory: meta?.subcategories[e.target.value][0] })}>{Object.keys(meta?.categories || {}).map((c) => <option key={c}>{c}</option>)}</Select>}</Field>
              <Field label="Subcategory">{(i) => <Select id={i} value={r.subcategory} onChange={(e) => setR({ ...r, subcategory: e.target.value })}>{(meta?.subcategories[r.category] || []).map((c: string) => <option key={c}>{c}</option>)}</Select>}</Field>
              <Field label="Route to (type)">{(i) => <Select id={i} value={r.target_type} onChange={(e) => setR({ ...r, target_type: e.target.value })}>{TARGETS.map((c) => <option key={c}>{c}</option>)}</Select>}</Field>
              <Field label="Fixed org">{(i) => <Select id={i} value={r.target_org_code || ""} onChange={(e) => setR({ ...r, target_org_code: e.target.value || null })}><option value="">(by airline/airport)</option>{meta?.orgs.map((o: any) => <option key={o.id} value={o.code}>{o.code}</option>)}</Select>}</Field>
            </div>
            <Field label="Weight">{(i) => <Input id={i} type="number" step="0.1" value={r.weight} onChange={(e) => setR({ ...r, weight: Number(e.target.value) })} />}</Field>
            <div className="flex gap-2">
              <Button disabled={r.keyword.length < 2} onClick={() => wrap(editing ? api(`/admin/rules/${editing}`, { method: "PUT", body: r }) : api("/admin/rules", { body: r }), editing ? "Rule updated" : "Rule added").then(() => { setR(blank); setEditing(null); })}>{editing ? "Save" : "Add"}</Button>
              {editing && <Button variant="outline" onClick={() => { setR(blank); setEditing(null); }}>Cancel</Button>}
            </div>
          </CardBody></Card>
          <Card><CardBody className="max-h-[640px] overflow-auto pt-4"><table className="w-full text-sm"><thead className="sticky top-0 bg-white text-left text-xs uppercase text-slate-500"><tr><th>Keyword</th><th>Category / sub</th><th>Routes to</th><th>Wt</th><th>On</th><th></th></tr></thead>
            <tbody>{rules.map((x: any) => <tr key={x.id} className="border-t"><td className="py-1 font-mono">{x.keyword}</td><td>{x.category}/{x.subcategory}</td><td>{x.target_org_code || x.target_type}</td><td>{x.weight}</td><td>{x.active ? "✓" : "–"}</td>
              <td className="whitespace-nowrap"><Button size="sm" variant="ghost" onClick={() => { setR(x); setEditing(x.id); }}>Edit</Button><Button size="sm" variant="ghost" onClick={() => wrap(api(`/admin/rules/${x.id}`, { method: "DELETE" }), "Deleted")}>✕</Button></td></tr>)}</tbody></table></CardBody></Card>
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[340px_1fr]">
          <Card className="h-fit"><CardHeader><CardTitle className="text-base">Add severity keyword</CardTitle></CardHeader><CardBody className="space-y-3">
            <Field label="Keyword / phrase">{(i) => <Input id={i} value={sv.keyword} onChange={(e) => setSv({ ...sv, keyword: e.target.value })} />}</Field>
            <Field label="Severity">{(i) => <Select id={i} value={sv.severity} onChange={(e) => setSv({ ...sv, severity: Number(e.target.value) })}>{[1, 2, 3, 4].map((s) => <option key={s} value={s}>S{s}{s === 1 ? " - critical (routes to L2+)" : ""}</option>)}</Select>}</Field>
            <Button disabled={sv.keyword.length < 2} onClick={() => wrap(api("/admin/severity", { body: sv }), "Added").then(() => setSv({ keyword: "", severity: 1 }))}>Add</Button>
            <p className="text-xs text-slate-600">The highest matching severity wins. The matched keywords are shown to redressors as the “severity reason”.</p>
          </CardBody></Card>
          <div className="grid gap-3 md:grid-cols-2">
            {[1, 2, 3, 4].map((s) => (
              <Card key={s}><CardHeader><CardTitle className="text-base"><SevBadge s={s} /></CardTitle></CardHeader><CardBody className="flex flex-wrap gap-1.5">
                {sevs.filter((x: any) => x.severity === s).map((x: any) => <Badge key={x.id} className="bg-slate-100 text-slate-800">{x.keyword}<button aria-label={`Delete ${x.keyword}`} className="ml-1 font-bold" onClick={() => wrap(api(`/admin/severity/${x.id}`, { method: "DELETE" }), "Deleted")}>×</button></Badge>)}
                {s === 3 && <span className="text-xs text-slate-500">(default when nothing matches)</span>}
              </CardBody></Card>
            ))}
          </div>
        </div>
      )}
    </Shell>
  );
}

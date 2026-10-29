"use client";
import { useCallback, useEffect, useState } from "react";
import { api, qs } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import { Button, Card, CardBody, Input, Select, Spinner, useToast } from "./ui";
import { TicketRow, TicketTable } from "./TicketTable";

export default function TicketList({ base = {}, bulk, live = true, cols }: { base?: Record<string, any>; bulk?: boolean; live?: boolean; cols?: string[] }) {
  const [f, setF] = useState<Record<string, any>>({ status: "open", sort: "severity", ...base });
  const [data, setData] = useState<{ total: number; items: TicketRow[] } | null>(null);
  const [page, setPage] = useState(1);
  const [sel, setSel] = useState<number[]>([]);
  const [bsev, setBsev] = useState("");
  const [meta, setMeta] = useState<any>(null);
  const [borg, setBorg] = useState("");
  const { push } = useToast();
  const load = useCallback(() => api(`/tickets${qs({ ...f, page, limit: 25 })}`).then(setData).catch(() => setData({ total: 0, items: [] })), [f, page]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (bulk) api("/meta").then(setMeta); }, [bulk]);
  useSSE(["tickets"], () => load(), live);
  const set = (k: string, v: any) => { setPage(1); setF((x) => ({ ...x, [k]: v })); };
  async function doBulk(action: string, value: number | null, note: string) {
    try { const r = await api("/tickets/bulk", { body: { ids: sel, action, value, note } }); push(`${r.updated} tickets updated`, "success"); setSel([]); load(); } catch (e: any) { push(e.message, "error"); }
  }
  return (
    <div className="space-y-3">
      <Card><CardBody className="grid gap-2 pt-4 sm:grid-cols-3 lg:grid-cols-7">
        <Input aria-label="Search" placeholder="Search ID / PNR / text" value={f.q || ""} onChange={(e) => set("q", e.target.value)} className="lg:col-span-2" />
        <Select aria-label="Status" value={f.status || ""} onChange={(e) => set("status", e.target.value)}>
          <option value="">All statuses</option><option value="open">Open</option>{["Assigned", "In-Progress", "On Hold - Awaiting Passenger Inputs", "Escalated", "Reopened", "Provisionally Resolved", "Resolved", "Closed"].map((s) => <option key={s}>{s}</option>)}
        </Select>
        <Select aria-label="Severity" value={f.severity || ""} onChange={(e) => set("severity", e.target.value)}><option value="">All priorities</option>{[1, 2, 3, 4].map((s) => <option key={s} value={s}>S{s}</option>)}</Select>
        <Select aria-label="Category" value={f.category || ""} onChange={(e) => set("category", e.target.value)}><option value="">All categories</option>{["flight", "airport", "ground", "govt", "other"].map((s) => <option key={s}>{s}</option>)}</Select>
        <Select aria-label="SLA" value={f.breached === undefined ? "" : String(f.breached)} onChange={(e) => set("breached", e.target.value === "" ? undefined : e.target.value)}><option value="">SLA: all</option><option value="true">Breached</option><option value="false">Within SLA</option></Select>
        <Select aria-label="Sort" value={f.sort} onChange={(e) => set("sort", e.target.value)}><option value="severity">Sort: priority</option><option value="newest">Newest</option><option value="oldest">Oldest</option><option value="due">Due soonest</option></Select>
      </CardBody></Card>
      {bulk && sel.length > 0 && (
        <Card className="border-navy"><CardBody className="flex flex-wrap items-center gap-2 pt-4">
          <b>{sel.length} selected</b>
          <Select aria-label="Bulk severity" value={bsev} onChange={(e) => setBsev(e.target.value)} className="w-40"><option value="">Set severity…</option>{[1, 2, 3, 4].map((s) => <option key={s} value={s}>S{s}</option>)}</Select>
          <Button size="sm" disabled={!bsev} onClick={() => doBulk("severity", Number(bsev), "Bulk assessment")}>Apply severity</Button>
          <Select aria-label="Bulk assign" value={borg} onChange={(e) => setBorg(e.target.value)} className="w-56"><option value="">Assign to org…</option>{meta?.orgs.map((o: any) => <option key={o.id} value={o.id}>{o.name}</option>)}</Select>
          <Button size="sm" variant="outline" disabled={!borg} onClick={() => doBulk("assign_org", Number(borg), "Bulk reassignment")}>Assign</Button>
          <Button size="sm" variant="danger" onClick={() => doBulk("escalate", null, "Bulk escalation on triage")}>Escalate +1 level</Button>
        </CardBody></Card>
      )}
      <Card>
        {data === null ? <Spinner /> : <TicketTable rows={data.items} selectable={bulk} selected={sel} onSelect={setSel} cols={cols} />}
        {data && (
          <div className="flex items-center justify-between border-t p-3 text-sm">
            <span>{data.total} grievances</span>
            <span className="flex items-center gap-2"><Button size="sm" variant="outline" disabled={page === 1} onClick={() => setPage(page - 1)}>Prev</Button>Page {page}<Button size="sm" variant="outline" disabled={page * 25 >= data.total} onClick={() => setPage(page + 1)}>Next</Button></span>
          </div>
        )}
      </Card>
    </div>
  );
}

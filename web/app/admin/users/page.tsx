"use client";
import { useCallback, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Select, Tabs, useToast } from "@/components/ui";
import { api } from "@/lib/api";

export default function Users() {
  const { push } = useToast();
  const [tab, setTab] = useState("users");
  const [rows, setRows] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [masters, setMasters] = useState<any>(null);
  const [f, setF] = useState<any>({ name: "", email: "", mobile: "", designation: "", org_id: "", role: "nodal", level: 3, backup_email: "", backup_mobile: "", authorisation_letter: "" });
  const [org, setOrg] = useState({ code: "", name: "", type: "airline", handle: "", has_crm: false });
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const load = useCallback(() => { api("/admin/users").then(setRows); api("/admin/masters").then(setMasters); }, []);
  useEffect(() => { load(); api("/meta").then(setMeta); }, [load]);
  async function create(e: React.FormEvent) {
    e.preventDefault(); setErr("");
    try { await api("/admin/users", { body: { ...f, org_id: f.org_id ? Number(f.org_id) : null, level: Number(f.level), password: "Welcome@123" } }); push("Account created (temporary password Welcome@123)", "success"); load(); }
    catch (x: any) { setErr(x.message); }
  }
  const patch = (id: number, b: any, m: string) => api(`/admin/users/${id}`, { method: "PATCH", body: b }).then(() => { push(m, "success"); load(); }).catch((x) => push(x.message, "error"));
  const shown = rows.filter((r) => !q || (r.name + r.email + (r.org || "")).toLowerCase().includes(q.toLowerCase()));
  return (
    <Shell roles={["admin"]} wide>
      <h1 className="mb-3 text-2xl font-bold text-navy">Users & master data</h1>
      <Tabs value={tab} onChange={setTab} tabs={[{ id: "users", label: "Staff & officers" }, { id: "masters", label: "Organisations & airports (masters)" }]} />
      {tab === "users" ? (
        <div className="mt-3 grid gap-4 xl:grid-cols-[380px_1fr]">
          <Card className="h-fit"><CardHeader><CardTitle className="text-base">Create account</CardTitle></CardHeader><CardBody>
            <form onSubmit={create} className="space-y-2">
              <Field label="Role">{(i) => <Select id={i} value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="nodal">Redressor Nodal Officer</option><option value="redressor">Redressor staff</option><option value="agent">AirSewa Agent</option><option value="manager">Control Room Manager</option></Select>}</Field>
              <Field label="Name" required>{(i) => <Input id={i} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />}</Field>
              <Field label="E-mail" required>{(i) => <Input id={i} type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} required />}</Field>
              <Field label="Phone" required>{(i) => <Input id={i} value={f.mobile} onChange={(e) => setF({ ...f, mobile: e.target.value })} required />}</Field>
              <Field label="Organisation">{(i) => <Select id={i} value={f.org_id} onChange={(e) => setF({ ...f, org_id: e.target.value })}><option value="">-</option>{meta?.orgs.map((o: any) => <option key={o.id} value={o.id}>{o.name}</option>)}</Select>}</Field>
              <Field label="Designation">{(i) => <Input id={i} value={f.designation} onChange={(e) => setF({ ...f, designation: e.target.value })} />}</Field>
              {f.role === "nodal" && <>
                <Field label="Backup delegate e-mail" required>{(i) => <Input id={i} type="email" value={f.backup_email} onChange={(e) => setF({ ...f, backup_email: e.target.value })} />}</Field>
                <Field label="Backup delegate mobile" required>{(i) => <Input id={i} value={f.backup_mobile} onChange={(e) => setF({ ...f, backup_mobile: e.target.value })} />}</Field>
                <Field label="Authorisation letter (from organisation)" required hint="Attach file name for the prototype (the letter is recorded in the audit log)">{(i) => <Input id={i} type="file" accept=".pdf,.jpg,.png" onChange={(e) => setF({ ...f, authorisation_letter: e.target.files?.[0]?.name || "" })} />}</Field>
              </>}
              {err && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-800">{err}</p>}
              <Button className="w-full">Create</Button>
            </form>
          </CardBody></Card>
          <Card><CardBody className="overflow-x-auto pt-4">
            <Input aria-label="Filter users" placeholder="Filter by name / e-mail / organisation" value={q} onChange={(e) => setQ(e.target.value)} className="mb-2 max-w-sm" />
            <table className="w-full min-w-[760px] text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th>Name</th><th>Organisation</th><th>Role</th><th>Lvl</th><th>Status</th><th></th></tr></thead>
              <tbody>{shown.slice(0, 120).map((u) => <tr key={u.id} className="border-t"><td className="py-1">{u.name}<div className="text-xs text-slate-500">{u.email}</div></td><td>{u.org}</td><td>{u.role}</td><td>{u.role === "redressor" ? `L${u.level}` : ""}</td>
                <td><Badge className={u.status === "active" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}>{u.status}</Badge></td>
                <td className="space-x-1 whitespace-nowrap">{u.status === "active" ? <><Button size="sm" variant="outline" onClick={() => patch(u.id, { status: "suspended" }, "Suspended")}>Suspend</Button><Button size="sm" variant="outline" onClick={() => patch(u.id, { status: "disabled" }, "Disabled")}>Disable</Button></> : <Button size="sm" onClick={() => patch(u.id, { status: "active" }, "Released")}>Release</Button>}<Button size="sm" variant="ghost" onClick={() => patch(u.id, { reset_password: true }, "Password reset")}>Reset pwd</Button></td></tr>)}</tbody></table>
          </CardBody></Card>
        </div>
      ) : masters && (
        <div className="mt-3 grid gap-4 lg:grid-cols-2">
          <Card><CardHeader><CardTitle className="text-base">Organisations ({masters.orgs.length})</CardTitle></CardHeader><CardBody className="max-h-[480px] overflow-auto"><table className="w-full text-sm"><tbody>{masters.orgs.map((o: any) => <tr key={o.id} className="border-t"><td className="py-1 font-mono">{o.code}</td><td>{o.name}</td><td>{o.type}</td><td>{o.handle}</td><td>{o.has_crm && <Badge className="bg-purple-100 text-purple-800">CRM</Badge>}</td></tr>)}</tbody></table></CardBody></Card>
          <div className="space-y-4">
            <Card><CardHeader><CardTitle className="text-base">Add organisation</CardTitle></CardHeader><CardBody className="space-y-2">
              <div className="grid grid-cols-2 gap-2"><Input aria-label="Code" placeholder="Code" value={org.code} onChange={(e) => setOrg({ ...org, code: e.target.value.toUpperCase() })} /><Input aria-label="Name" placeholder="Name" value={org.name} onChange={(e) => setOrg({ ...org, name: e.target.value })} />
                <Select aria-label="Type" value={org.type} onChange={(e) => setOrg({ ...org, type: e.target.value })}>{["airline", "airport_operator", "gsp", "regulator", "ota", "aai"].map((x) => <option key={x}>{x}</option>)}</Select><Input aria-label="Handle" placeholder="@social_handle" value={org.handle} onChange={(e) => setOrg({ ...org, handle: e.target.value })} /></div>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={org.has_crm} onChange={(e) => setOrg({ ...org, has_crm: e.target.checked })} /> Has native CRM (webhook flow, Simulated)</label>
              <Button disabled={!org.code || !org.name} onClick={() => api("/admin/masters/org", { body: org }).then(() => { push("Organisation added", "success"); load(); }).catch((e) => push(e.message, "error"))}>Add</Button>
            </CardBody></Card>
            <Card><CardHeader><CardTitle className="text-base">Airports ({masters.airports.length})</CardTitle></CardHeader><CardBody className="max-h-64 overflow-auto"><table className="w-full text-sm"><tbody>{masters.airports.map((a: any) => <tr key={a.id} className="border-t"><td className="py-1 font-mono">{a.code}</td><td>{a.name}</td><td>{a.city}, {a.state}</td></tr>)}</tbody></table></CardBody></Card>
          </div>
        </div>
      )}
    </Shell>
  );
}

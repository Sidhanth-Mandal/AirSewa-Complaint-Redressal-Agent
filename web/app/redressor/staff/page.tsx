"use client";
import { useCallback, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Select, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

export default function Staff() {
  const { me } = useSession();
  const { push } = useToast();
  const [rows, setRows] = useState<any[]>([]);
  const [f, setF] = useState({ name: "", email: "", mobile: "", designation: "", level: 1, access_type: "write", password: "Welcome@123" });
  const [err, setErr] = useState("");
  const load = useCallback(() => api("/admin/users").then(setRows), []);
  useEffect(() => { load(); }, [load]);
  async function create(e: React.FormEvent) {
    e.preventDefault(); setErr("");
    try { await api("/admin/users", { body: { ...f, level: Number(f.level), role: "redressor" } }); push("Staff account created (organisation auto-filled)", "success"); setF({ ...f, name: "", email: "", mobile: "" }); load(); }
    catch (x: any) { setErr(x.message); push(x.message, "error"); }
  }
  const patch = (id: number, body: any, msg: string) => api(`/admin/users/${id}`, { method: "PATCH", body }).then(() => { push(msg, "success"); load(); }).catch((x) => push(x.message, "error"));
  return (
    <Shell roles={["nodal"]} wide>
      <h1 className="mb-3 text-2xl font-bold text-navy">Staff accounts - {me?.org}</h1>
      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card><CardHeader><CardTitle>Create redressor staff</CardTitle></CardHeader><CardBody>
          <form onSubmit={create} className="space-y-3">
            <Field label="Name" required>{(i) => <Input id={i} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />}</Field>
            <Field label="E-mail" required>{(i) => <Input id={i} type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} required />}</Field>
            <Field label="Phone (10 digits)" required>{(i) => <Input id={i} value={f.mobile} onChange={(e) => setF({ ...f, mobile: e.target.value })} required inputMode="numeric" />}</Field>
            <Field label="Designation">{(i) => <Input id={i} value={f.designation} onChange={(e) => setF({ ...f, designation: e.target.value })} />}</Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="Access level">{(i) => <Select id={i} value={f.level} onChange={(e) => setF({ ...f, level: Number(e.target.value) })}><option value={1}>L1</option><option value={2}>L2</option><option value={3}>L3</option></Select>}</Field>
              <Field label="Access type">{(i) => <Select id={i} value={f.access_type} onChange={(e) => setF({ ...f, access_type: e.target.value })}><option>write</option><option>read</option></Select>}</Field>
            </div>
            <Field label="Organisation">{(i) => <Input id={i} value={me?.org || ""} readOnly />}</Field>
            {err && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-800">{err}</p>}
            <Button className="w-full">Create account</Button>
          </form>
        </CardBody></Card>
        <Card><CardHeader><CardTitle>Team</CardTitle></CardHeader><CardBody className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm"><thead className="text-left text-xs uppercase text-slate-500"><tr><th>Name</th><th>Role</th><th>Level</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>{rows.map((u) => (
              <tr key={u.id} className="border-t align-top"><td className="py-2">{u.name}<div className="text-xs text-slate-500">{u.email}</div></td><td>{u.role}</td>
                <td>{u.role === "redressor" ? <Select aria-label="Level" value={u.level} onChange={(e) => patch(u.id, { level: Number(e.target.value) }, "Level changed")} className="w-20 !min-h-[34px]"><option value={1}>L1</option><option value={2}>L2</option><option value={3}>L3</option></Select> : "-"}</td>
                <td><Badge className={u.status === "active" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}>{u.status}</Badge></td>
                <td className="space-x-1 whitespace-nowrap">{u.role === "redressor" && <>
                  {u.status === "active" ? <><Button size="sm" variant="outline" onClick={() => patch(u.id, { status: "suspended" }, "Suspended")}>Suspend</Button><Button size="sm" variant="outline" onClick={() => patch(u.id, { status: "disabled" }, "Disabled")}>Disable (exit)</Button></> :
                    u.status === "suspended" ? <Button size="sm" onClick={() => patch(u.id, { status: "active" }, "Released")}>Release</Button> : <span className="text-xs text-slate-500">disabled</span>}
                  <Button size="sm" variant="ghost" onClick={() => patch(u.id, { reset_password: true }, "Password reset to default")}>Reset pwd</Button></>}</td></tr>
            ))}</tbody></table>
        </CardBody></Card>
      </div>
    </Shell>
  );
}

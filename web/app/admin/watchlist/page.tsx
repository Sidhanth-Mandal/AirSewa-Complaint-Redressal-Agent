"use client";
import { useCallback, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, Input, Select, Simulated, useToast } from "@/components/ui";
import { api } from "@/lib/api";

export default function Watchlist() {
  const { push } = useToast();
  const [items, setItems] = useState<any[]>([]);
  const [n, setN] = useState({ kind: "handle", value: "", label: "" });
  const load = useCallback(() => api("/admin/watchlist").then(setItems), []);
  useEffect(() => { load(); }, [load]);
  const wrap = (p: Promise<any>, m: string) => p.then(() => { push(m, "success"); load(); }).catch((e) => push(e.message, "error"));
  return (
    <Shell roles={["admin", "agent"]} wide>
      <div className="mb-1 flex items-center gap-2"><h1 className="text-2xl font-bold text-navy">Social watch list</h1><Simulated text="Simulated X / Instagram" /></div>
      <p className="mb-3 text-sm text-slate-600">Detection triggers only when a post mentions a monitored handle, uses a monitored hashtag, or contains a monitored/aviation keyword. Edits take effect on the very next post - try it in the simulator.</p>
      <Card className="mb-4"><CardBody className="flex flex-wrap items-end gap-2 pt-4">
        <label className="text-sm">Type<Select value={n.kind} onChange={(e) => setN({ ...n, kind: e.target.value })}><option value="handle">Handle</option><option value="hashtag">Hashtag</option><option value="keyword">Keyword</option></Select></label>
        <label className="min-w-[220px] flex-1 text-sm">Value<Input value={n.value} onChange={(e) => setN({ ...n, value: e.target.value })} placeholder="@handle, #tag or keyword" /></label>
        <label className="min-w-[200px] text-sm">Label<Input value={n.label} onChange={(e) => setN({ ...n, label: e.target.value })} /></label>
        <Button disabled={n.value.length < 2} onClick={() => wrap(api("/admin/watchlist", { body: n }), "Added to watch list").then(() => setN({ ...n, value: "", label: "" }))}>Add</Button>
      </CardBody></Card>
      <div className="grid gap-4 md:grid-cols-3">
        {[["handle", "Monitored handles (ministry, minister, regulators, airlines, airports)"], ["hashtag", "Monitored hashtags"], ["keyword", "Monitored keywords"]].map(([k, title]) => (
          <Card key={k}><CardHeader><CardTitle className="text-base">{title}</CardTitle></CardHeader><CardBody className="space-y-1.5">
            {items.filter((i) => i.kind === k).map((i) => (
              <div key={i.id} className="flex items-center justify-between gap-2 rounded border px-2 py-1 text-sm">
                <span className={i.active ? "" : "text-slate-400 line-through"}><b>{i.value}</b> <span className="text-xs text-slate-500">{i.label}</span></span>
                <span className="flex gap-1"><Button size="sm" variant="ghost" onClick={() => wrap(api(`/admin/watchlist/${i.id}?active=${!i.active}`, { method: "PATCH" }), i.active ? "Disabled" : "Enabled")}>{i.active ? "Pause" : "Resume"}</Button>
                  <Button size="sm" variant="ghost" aria-label={`Delete ${i.value}`} onClick={() => wrap(api(`/admin/watchlist/${i.id}`, { method: "DELETE" }), "Removed")}>✕</Button></span>
              </div>
            ))}
          </CardBody></Card>
        ))}
      </div>
    </Shell>
  );
}

"use client";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { Button, Card, CardBody, CardHeader, CardTitle, Input, Simulated, useToast } from "@/components/ui";
import { api } from "@/lib/api";

export default function Settings() {
  const { push } = useToast();
  const [c, setC] = useState<any>(null);
  useEffect(() => { api("/admin/config").then(setC); }, []);
  if (!c) return <Shell roles={["admin"]}><p>Loading…</p></Shell>;
  const save = (values: any, m = "Saved") => api("/admin/config", { method: "PUT", body: { values } }).then(() => push(m, "success")).catch((e) => push(e.message, "error"));
  const set = (k: string, v: any) => setC({ ...c, [k]: v });
  return (
    <Shell roles={["admin"]}>
      <h1 className="mb-3 text-2xl font-bold text-navy">Settings</h1>
      <div className="grid gap-4 md:grid-cols-2">
        <Card><CardHeader><CardTitle className="text-base">Business rules (RFP inconsistency flags)</CardTitle></CardHeader><CardBody className="space-y-3 text-sm">
          <label className="flex items-start gap-2"><input type="checkbox" className="mt-1 h-5 w-5" checked={c.allow_pre_breach_filing} onChange={(e) => set("allow_pre_breach_filing", e.target.checked)} />
            <span><b>Allow filing before TAT breach</b> (permissive). FRS 3.2 #16 says grievances may be filed only after the airline TAT breach unless critical; the rest of the RFP implies immediate filing. Default: ON. Switch off to enforce the strict reading.</span></label>
          <label className="block">Maximum reopens per ticket<Input type="number" min={0} max={5} value={c.max_reopens} onChange={(e) => set("max_reopens", Number(e.target.value))} /></label>
          <Button onClick={() => save({ allow_pre_breach_filing: c.allow_pre_breach_filing, max_reopens: c.max_reopens })}>Save</Button>
        </CardBody></Card>
        <Card><CardHeader><CardTitle className="text-base">Crisis banner (e.g. fog advisory)</CardTitle></CardHeader><CardBody className="space-y-2 text-sm">
          <label className="flex items-center gap-2"><input type="checkbox" checked={c.crisis_banner.active} onChange={(e) => set("crisis_banner", { ...c.crisis_banner, active: e.target.checked })} /> Show banner on every page</label>
          <Input aria-label="Banner text (English)" placeholder="English text" value={c.crisis_banner.text} onChange={(e) => set("crisis_banner", { ...c.crisis_banner, text: e.target.value })} />
          <Input aria-label="Banner text (Hindi)" placeholder="हिंदी पाठ" value={c.crisis_banner.text_hi} onChange={(e) => set("crisis_banner", { ...c.crisis_banner, text_hi: e.target.value })} />
          <Button variant="outline" onClick={() => set("crisis_banner", { active: true, text: "Fog advisory: flights at Delhi and Lucknow may be delayed. Check your flight status before leaving for the airport.", text_hi: "कोहरे की चेतावनी: दिल्ली और लखनऊ की उड़ानों में देरी हो सकती है। हवाई अड्डे जाने से पहले उड़ान की स्थिति देखें।" })}>Fill fog advisory sample</Button>
          <div><Button onClick={() => save({ crisis_banner: c.crisis_banner }, "Banner updated")}>Save</Button></div>
        </CardBody></Card>
        <Card><CardHeader><CardTitle className="text-base">Social listening</CardTitle></CardHeader><CardBody className="space-y-2 text-sm">
          <label className="block">Minister handle (configurable)<Input value={c.minister_handle} onChange={(e) => set("minister_handle", e.target.value)} /></label>
          <label className="block">Viral threshold (related posts + engagement)<Input type="number" value={c.viral_threshold} onChange={(e) => set("viral_threshold", Number(e.target.value))} /></label>
          <label className="block">Duplicate window (hours)<Input type="number" value={c.dedup_window_hours} onChange={(e) => set("dedup_window_hours", Number(e.target.value))} /></label>
          <label className="block">Text similarity threshold (0-1)<Input type="number" step="0.05" value={c.dup_similarity} onChange={(e) => set("dup_similarity", Number(e.target.value))} /></label>
          <Button onClick={() => save({ minister_handle: c.minister_handle, viral_threshold: c.viral_threshold, dedup_window_hours: c.dedup_window_hours, dup_similarity: c.dup_similarity })}>Save</Button>
        </CardBody></Card>
        <Card><CardHeader><CardTitle className="text-base">Data retention & privacy</CardTitle></CardHeader><CardBody className="space-y-2 text-sm">
          <label className="block">Social data retention (days)<Input type="number" value={c.social_retention_days} onChange={(e) => set("social_retention_days", Number(e.target.value))} /></label>
          <label className="block">Ticket retention (days)<Input type="number" value={c.retention_days} onChange={(e) => set("retention_days", Number(e.target.value))} /></label>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => save({ social_retention_days: c.social_retention_days, retention_days: c.retention_days })}>Save</Button>
            <Button variant="outline" onClick={() => api("/admin/apply-retention", { method: "POST" }).then((r) => push(`Deleted ${r.deleted_posts} posts older than ${r.older_than_days} days`, "success"))}>Apply retention now</Button>
            <Button variant="danger" onClick={() => confirm("Delete ALL simulated social posts, notifications and unapproved social drafts, and anonymise handles on tickets?") && api("/admin/purge-social", { method: "POST" }).then((r) => push(`Purged ${r.posts} posts, ${r.notifications} notifications, ${r.drafts} drafts`, "success"))}>Purge social data</Button>
          </div>
        </CardBody></Card>
        <Card><CardHeader><CardTitle className="text-base">PACR commercials (RFP 2.28) <Simulated /></CardTitle></CardHeader><CardBody className="space-y-2 text-sm">
          <label className="block">Monthly PACR invoice (₹) - penalty cap = 10%<Input type="number" value={c.monthly_invoice_inr} onChange={(e) => set("monthly_invoice_inr", Number(e.target.value))} /></label>
          <label className="block">PU target per shift<Input type="number" value={c.pu_target} onChange={(e) => set("pu_target", Number(e.target.value))} /></label>
          <Button onClick={() => save({ monthly_invoice_inr: c.monthly_invoice_inr, pu_target: c.pu_target })}>Save</Button>
        </CardBody></Card>
      </div>
    </Shell>
  );
}

"use client";
import { useState } from "react";
import { Shell } from "@/components/Shell";
import { DraftModal, DraftRow } from "@/components/PacrFeed";
import { Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Simulated, Tabs, Textarea, useToast } from "@/components/ui";
import { api } from "@/lib/api";

const CH: Record<string, { label: string; sender: string; senderLabel: string; subject?: boolean; sample: any; note?: string }> = {
  whatsapp: { label: "WhatsApp message", sender: "+919810011223", senderLabel: "WhatsApp number", sample: { name: "Rohan Gupta", text: "Hi, my flight AI 101 got cancelled and refund not received for 18 days. PNR AB12CD. Please help" } },
  email: { label: "E-mail", sender: "meera.k@mail.demo", senderLabel: "From e-mail", subject: true, sample: { name: "Meera K", subject: "Lost baggage on 6E 204", text: "My checked bag did not arrive at Mumbai after flight 6E 204. It has medicines. PNR XK92LM. Please trace it urgently." } },
  ivr: { label: "IVR call transcript", sender: "+919899887766", senderLabel: "Caller number", note: "Speech-to-text is simulated; paste the transcript.", sample: { name: "Caller", text: "wheelchair was not available for my mother at Kolkata airport, we waited one hour, she is a senior citizen" } },
  cpgrams: { label: "CPGRAMS record", sender: "PMOPG/E/2026/0045123", senderLabel: "CPGRAMS registration no.", sample: { name: "Citizen", text: "The washroom at Lucknow airport is dirty and there is no drinking water. Forwarded for necessary action." } },
  letter: { label: "Physical letter (scan)", sender: "LTR/445", senderLabel: "Letter reference", note: "OCR of the scanned letter is simulated; paste the extracted text.", sample: { name: "S. K. Banerjee", text: "Respected Sir, at Kolkata airport customs officers demanded unfair duty on my gift items. Kindly look into this malpractice." } },
};

export default function Channels() {
  const [tab, setTab] = useState("whatsapp");
  const c = CH[tab];
  const [f, setF] = useState<any>({ sender: c.sender, ...c.sample });
  const [res, setRes] = useState<any[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const [meta, setMeta] = useState<any>(null);
  const { push } = useToast();
  const pick = (t: string) => { setTab(t); setF({ sender: CH[t].sender, ...CH[t].sample }); };
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (!meta) setMeta(await api("/meta"));
      const d = await api(`/channels/${tab}`, { body: { sender: f.sender, name: f.name, subject: f.subject, text: f.text } });
      setRes((r) => [d, ...r]);
      push(d.status === "grouped" ? `Duplicate detected (${d.dup_reason}) - grouped` : "Draft ticket created in the review queue", "success");
    } catch (x: any) { push(x.message, "error"); }
  }
  return (
    <Shell roles={["agent", "admin"]} wide>
      <div className="mb-3 flex items-center gap-2"><h1 className="text-2xl font-bold text-navy">PACR channel simulators</h1><Simulated /></div>
      <p className="mb-3 text-sm text-slate-600">Each channel feeds the same detection pipeline (translation, classification, severity, de-duplication by PNR / service request / text similarity) and lands as a draft ticket in the agent review queue. No real telephony, WhatsApp, e-mail or CPGRAMS connection exists.</p>
      <div className="grid gap-4 lg:grid-cols-[420px_1fr]">
        <Card><CardHeader><CardTitle>Send a test message</CardTitle></CardHeader><CardBody>
          <Tabs value={tab} onChange={pick} tabs={Object.entries(CH).map(([k, v]) => ({ id: k, label: v.label.split(" ")[0] }))} />
          <form onSubmit={submit} className="mt-3 space-y-3">
            <p className="text-sm font-semibold">{c.label}</p>
            {c.note && <p className="text-xs text-purple-800">{c.note}</p>}
            <Field label={c.senderLabel}>{(i) => <Input id={i} value={f.sender} onChange={(e) => setF({ ...f, sender: e.target.value })} required />}</Field>
            <Field label="Name">{(i) => <Input id={i} value={f.name || ""} onChange={(e) => setF({ ...f, name: e.target.value })} />}</Field>
            {c.subject && <Field label="Subject">{(i) => <Input id={i} value={f.subject || ""} onChange={(e) => setF({ ...f, subject: e.target.value })} />}</Field>}
            <Field label="Message / transcript">{(i) => <Textarea id={i} value={f.text} onChange={(e) => setF({ ...f, text: e.target.value })} required minLength={5} />}</Field>
            <Button className="w-full">Send to PACR</Button>
          </form>
        </CardBody></Card>
        <div>
          <h2 className="mb-2 font-semibold text-navy">Resulting drafts</h2>
          <ul className="space-y-2">{res.map((d) => <DraftRow key={d.id} d={d} onOpen={(x) => setOpen(x.id)} fresh />)}</ul>
          {res.length === 0 && <p className="text-sm text-slate-500">Nothing sent yet. Try the same PNR on WhatsApp and then e-mail to see cross-channel duplicate detection.</p>}
        </div>
      </div>
      <DraftModal id={open} onClose={() => setOpen(null)} onChange={() => {}} meta={meta} />
    </Shell>
  );
}

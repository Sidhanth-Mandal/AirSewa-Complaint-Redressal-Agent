"use client";
import { useLocale } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button, Simulated } from "./ui";

type Msg = { from: "bot" | "me"; text: string };

export default function Chatbot() {
  const locale = useLocale();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [quick, setQuick] = useState<string[]>([]);
  const [state, setState] = useState<any>({});
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, open]);
  useEffect(() => {
    if (open && msgs.length === 0) send(locale === "hi" ? "नमस्ते" : "hello", true);
  }, [open]);

  async function send(text: string, silent = false) {
    if (!text.trim()) return;
    if (!silent) setMsgs((m) => [...m, { from: "me", text }]);
    setInput("");
    setBusy(true);
    try {
      const r = await api("/chatbot", { body: { message: text, lang: locale, state } });
      setState(r.state || {});
      setQuick(r.quick_replies || []);
      setMsgs((m) => [...m, { from: "bot", text: r.reply.replace(/\*\*/g, "") }]);
      if (r.action?.type === "open_form") router.push(`/passenger/new?category=${r.action.category}&description=${encodeURIComponent(r.action.description)}`);
    } catch (e: any) {
      setMsgs((m) => [...m, { from: "bot", text: "Sorry, something went wrong." }]);
    }
    setBusy(false);
  }

  return (
    <>
      <button onClick={() => setOpen(!open)} aria-expanded={open} aria-label="Open assistant chat"
        className="fixed bottom-4 left-4 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-navy text-2xl text-white shadow-lg hover:bg-navy-700">💬</button>
      {open && (
        <section aria-label="AirSewa assistant" className="fixed bottom-20 left-4 z-40 flex h-[480px] w-[min(92vw,360px)] flex-col rounded-lg border bg-white shadow-xl">
          <div className="flex items-center justify-between rounded-t-lg bg-navy px-3 py-2 text-white">
            <span className="font-semibold">AirSewa Assistant</span>
            <span className="flex items-center gap-2"><Simulated text="Rule-based" /><button onClick={() => setOpen(false)} aria-label="Close chat" className="text-xl">×</button></span>
          </div>
          <div className="flex-1 space-y-2 overflow-y-auto p-3 text-sm scroll-thin" aria-live="polite">
            {msgs.map((m, i) => (
              <div key={i} className={m.from === "me" ? "text-right" : ""}>
                <span className={`inline-block max-w-[85%] rounded-lg px-3 py-2 ${m.from === "me" ? "bg-navy text-white" : "bg-slate-100"}`}>{m.text}</span>
              </div>
            ))}
            <div ref={end} />
          </div>
          <div className="flex flex-wrap gap-1 px-3 pb-1">
            {quick.map((q) => <button key={q} onClick={() => send(q)} className="rounded-full border border-navy px-2 py-1 text-xs text-navy hover:bg-navy-50">{q}</button>)}
          </div>
          <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2 border-t p-2">
            <input value={input} onChange={(e) => setInput(e.target.value)} aria-label="Message" placeholder={locale === "hi" ? "संदेश लिखें…" : "Type a message…"} className="flex-1 rounded border border-slate-400 px-2 py-2" />
            <Button size="sm" disabled={busy}>{locale === "hi" ? "भेजें" : "Send"}</Button>
          </form>
        </section>
      )}
    </>
  );
}

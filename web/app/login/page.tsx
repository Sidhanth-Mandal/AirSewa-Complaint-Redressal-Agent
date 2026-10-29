"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Suspense, useState } from "react";
import { Shell } from "@/components/Shell";
import { Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Simulated, Tabs, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { HOME, useSession } from "@/lib/session";

const DEMO = [
  ["Passenger (registered)", "passenger@demo.in", "passenger"], ["AirSewa Agent (PACR)", "agent1@pacr.demo", "agent"], ["Admin / MoCA-AAI", "admin@moca.demo", "admin"],
  ["Control Room Manager", "manager@pacr.demo", "manager"], ["IndiGo Nodal Officer", "nodal.6e@demo.in", "redressor"], ["IndiGo Redressor L1", "6e.l1a@demo.in", "redressor"],
  ["IndiGo Redressor L2", "6e.l2@demo.in", "redressor"], ["Air India L2 (S1 desk)", "ai.l2@demo.in", "redressor"], ["Delhi Airport (DIAL) L1", "dial.l1a@demo.in", "redressor"],
];

function LoginInner() {
  const t = useTranslations("auth");
  const tc = useTranslations("common");
  const router = useRouter();
  const sp = useSearchParams();
  const { refresh } = useSession();
  const { push } = useToast();
  const [tab, setTab] = useState(sp.get("as") === "passenger" || !sp.get("as") ? "otp" : "pw");
  const [id, setId] = useState("");
  const [pw, setPw] = useState("");
  const [otp, setOtp] = useState("");
  const [sent, setSent] = useState(false);
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(false);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function done(me: any) {
    await refresh();
    const next = sp.get("next");
    router.replace(next && next.startsWith("/") ? next : HOME[me.role] || "/");
  }
  async function submitPw(e: React.FormEvent) {
    e.preventDefault(); setErr(""); setBusy(true);
    try { done(await api("/auth/login", { body: { username: id, password: pw } })); } catch (x: any) { setErr(x.message); }
    setBusy(false);
  }
  async function sendOtp() {
    setErr(""); setBusy(true);
    try {
      const r = await api("/auth/otp/request", { body: { identifier: id } });
      setSent(true);
      push(`📱 Simulated SMS/e-mail: your AirSewa OTP is ${r.dev_otp}`, "info", true);
      setOtp(r.dev_otp || "");
    } catch (x: any) { setErr(x.message); }
    setBusy(false);
  }
  async function verify(e: React.FormEvent) {
    e.preventDefault(); setErr(""); setBusy(true);
    try { done(await api("/auth/otp/verify", { body: { identifier: id, otp, mode: tab === "guest" ? "guest" : "login", name: name || undefined, consent_save: consent } })); } catch (x: any) { setErr(x.message); }
    setBusy(false);
  }
  return (
    <div className="mx-auto grid max-w-4xl gap-5 md:grid-cols-[1fr_300px]">
      <Card>
        <CardHeader><CardTitle>{t("loginTitle")}</CardTitle></CardHeader>
        <CardBody>
          <Tabs value={tab} onChange={(v) => { setTab(v); setSent(false); setErr(""); }} tabs={[{ id: "otp", label: t("withOtp") }, { id: "pw", label: t("withPassword") }, { id: "guest", label: t("guest") }]} />
          <div className="mt-4 space-y-4">
            {tab === "pw" ? (
              <form onSubmit={submitPw} className="space-y-4">
                <Field label={t("username")} required>{(i) => <Input id={i} value={id} onChange={(e) => setId(e.target.value)} autoComplete="username" inputMode="email" required />}</Field>
                <Field label={t("password")} required>{(i) => <Input id={i} type="password" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="current-password" required />}</Field>
                {err && <p role="alert" className="text-sm text-red-700">{err}</p>}
                <Button disabled={busy} className="w-full">{tc("login")}</Button>
                <p className="text-xs text-slate-600">{t("staffNote")} <Link className="text-navy underline" href="/register?reset=1">{t("forgot")}</Link></p>
              </form>
            ) : (
              <form onSubmit={verify} className="space-y-4">
                <Field label={t("username")} required hint={t("guestNote")}>{(i) => <Input id={i} value={id} onChange={(e) => { setId(e.target.value); setSent(false); }} inputMode="email" autoComplete="username" required />}</Field>
                {tab === "guest" && <Field label={t("name")}>{(i) => <Input id={i} value={name} onChange={(e) => setName(e.target.value)} />}</Field>}
                {!sent ? <Button type="button" onClick={sendOtp} disabled={busy || !id} className="w-full">{t("sendOtp")} <Simulated /></Button> : (
                  <>
                    <Field label={t("otp")} required hint={t("otpSent", { otp: "123456" })}>{(i) => <Input id={i} value={otp} onChange={(e) => setOtp(e.target.value)} inputMode="numeric" maxLength={6} autoFocus required />}</Field>
                    {tab === "guest" && (
                      <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1 h-5 w-5" checked={consent} onChange={(e) => setConsent(e.target.checked)} />{t("guestConsent")}</label>
                    )}
                    <Button disabled={busy} className="w-full">{t("verify")}</Button>
                  </>
                )}
                {err && <p role="alert" className="text-sm text-red-700">{err}</p>}
              </form>
            )}
            <p className="text-sm">{t("noAccount")} <Link className="text-navy underline" href="/register">{tc("register")}</Link></p>
          </div>
        </CardBody>
      </Card>
      <Card className="h-fit border-dashed border-purple-400">
        <CardHeader><CardTitle className="text-base">Demo accounts <Simulated text="Prototype" /></CardTitle></CardHeader>
        <CardBody className="space-y-1 text-sm">
          <p className="text-xs text-slate-600">Password <code>Demo@1234</code>. Passenger OTP is <code>123456</code>. Click to fill.</p>
          {DEMO.map(([label, email]) => (
            <button key={email} type="button" onClick={() => { setTab("pw"); setId(email); setPw("Demo@1234"); }} className="block w-full rounded border border-slate-200 px-2 py-1.5 text-left hover:bg-slate-50">
              <b>{label}</b><br /><span className="text-xs text-slate-600">{email}</span>
            </button>
          ))}
        </CardBody>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return <Shell><Suspense><LoginInner /></Suspense></Shell>;
}

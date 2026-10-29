"use client";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Suspense, useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { Button, Card, CardBody, CardHeader, CardTitle, Field, Input, Select, Simulated, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { HOME, useSession } from "@/lib/session";

function Inner() {
  const t = useTranslations("auth");
  const tc = useTranslations("common");
  const router = useRouter();
  const reset = useSearchParams().get("reset") === "1";
  const { refresh } = useSession();
  const { push } = useToast();
  const [types, setTypes] = useState<string[]>(["Passenger"]);
  const [f, setF] = useState({ user_type: "Passenger", name: "", identifier: "", country_code: "+91", password: "", otp: "" });
  const [sent, setSent] = useState(false);
  const [err, setErr] = useState("");
  const set = (k: string, v: string) => setF((x) => ({ ...x, [k]: v }));
  useEffect(() => { api("/meta").then((m) => setTypes(m.user_types)).catch(() => {}); }, []);
  async function sendOtp() {
    setErr("");
    try {
      const r = await api("/auth/otp/request", { body: { identifier: f.identifier, country_code: f.country_code } });
      setSent(true); set("otp", r.dev_otp || "");
      push(`📱 Simulated SMS/e-mail: your AirSewa OTP is ${r.dev_otp}`, "info", true);
    } catch (x: any) { setErr(x.message); }
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr("");
    try {
      if (reset) { await api("/auth/password/reset", { body: { identifier: f.identifier, otp: f.otp, new_password: f.password } }); push(t("resetDone"), "success"); router.push("/login"); return; }
      const me = await api("/auth/register", { body: f });
      await refresh(); router.replace(HOME[me.role]);
    } catch (x: any) { setErr(x.message); }
  }
  return (
    <Card className="mx-auto max-w-lg">
      <CardHeader><CardTitle>{reset ? t("resetTitle") : t("registerTitle")}</CardTitle></CardHeader>
      <CardBody>
        <form onSubmit={submit} className="space-y-4">
          {!reset && (
            <>
              <Field label={t("userType")} required>{(i) => <Select id={i} value={f.user_type} onChange={(e) => set("user_type", e.target.value)}>{types.map((x) => <option key={x}>{x}</option>)}</Select>}</Field>
              <Field label={t("name")} required>{(i) => <Input id={i} value={f.name} onChange={(e) => set("name", e.target.value)} required minLength={2} autoComplete="name" />}</Field>
            </>
          )}
          <div className="grid grid-cols-[110px_1fr] gap-2">
            <Field label={t("countryCode")}>{(i) => <Input id={i} value={f.country_code} onChange={(e) => set("country_code", e.target.value)} />}</Field>
            <Field label={t("mobileOrEmail")} required>{(i) => <Input id={i} value={f.identifier} onChange={(e) => { set("identifier", e.target.value); setSent(false); }} inputMode="email" required />}</Field>
          </div>
          <Field label={reset ? t("newPassword") : t("password")} required hint={t("passwordHint")}>{(i) => <Input id={i} type="password" value={f.password} onChange={(e) => set("password", e.target.value)} autoComplete="new-password" required />}</Field>
          {!sent ? <Button type="button" onClick={sendOtp} className="w-full" disabled={!f.identifier}>{t("sendOtp")} <Simulated /></Button> : (
            <>
              <Field label={t("otp")} required hint={t("otpSent", { otp: "123456" })}>{(i) => <Input id={i} value={f.otp} onChange={(e) => set("otp", e.target.value)} inputMode="numeric" maxLength={6} required />}</Field>
              <Button className="w-full">{reset ? tc("save") : t("create")}</Button>
            </>
          )}
          {err && <p role="alert" className="text-sm text-red-700">{err}</p>}
        </form>
      </CardBody>
    </Card>
  );
}
export default function RegisterPage() { return <Shell><Suspense><Inner /></Suspense></Shell>; }

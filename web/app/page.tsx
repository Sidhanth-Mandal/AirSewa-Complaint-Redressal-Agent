"use client";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Shell } from "@/components/Shell";
import { Button, Card, CardBody, Simulated } from "@/components/ui";
import { useSession } from "@/lib/session";

export default function Landing() {
  const t = useTranslations("landing");
  const { me } = useSession();
  const portals = [
    ["/login?as=passenger", "pPassenger", "pPassengerD", "🧳"], ["/login?as=redressor", "pRedressor", "pRedressorD", "🏢"], ["/login?as=agent", "pAgent", "pAgentD", "🎧"],
    ["/login?as=admin", "pAdmin", "pAdminD", "📊"], ["/login?as=manager", "pManager", "pManagerD", "⏱"],
  ];
  return (
    <Shell>
      <section className="rounded-xl bg-gradient-to-br from-navy to-navy-700 px-5 py-10 text-white sm:px-10">
        <h1 className="max-w-3xl text-3xl font-bold leading-tight sm:text-4xl">{t("title")}</h1>
        <p className="mt-3 max-w-2xl text-lg text-white/90">{t("sub")}</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/passenger/new"><Button variant="saffron" size="lg">{t("file")}</Button></Link>
          <Link href="/track"><Button variant="outline" size="lg">{t("flight")}</Button></Link>
          <Link href="/track#ticket"><Button variant="outline" size="lg">{t("trackTicket")}</Button></Link>
        </div>
        <ol className="mt-8 grid gap-3 sm:grid-cols-3">
          {["step1", "step2", "step3"].map((s, i) => (
            <li key={s} className="flex items-center gap-3 rounded-lg bg-white/10 p-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-saffron font-bold text-slate-900">{i + 1}</span>{t(s as any)}
            </li>
          ))}
        </ol>
      </section>

      <h2 className="mb-3 mt-8 text-xl font-semibold text-navy">{t("portals")}</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {portals.map(([href, a, b, icon]) => (
          <Link key={a} href={href} className="group">
            <Card className="h-full transition group-hover:border-navy group-hover:shadow-md">
              <CardBody className="pt-4">
                <div className="text-3xl" aria-hidden="true">{icon}</div>
                <div className="mt-2 text-lg font-semibold text-navy">{t(a as any)}</div>
                <p className="text-sm text-slate-600">{t(b as any)}</p>
              </CardBody>
            </Card>
          </Link>
        ))}
        {[["/demo", "pDemo", "pDemoD", "🖥"], ["/simulator", "pSim", "pSimD", "🐦"]].map(([href, a, b, icon]) => (
          <Link key={a} href={href} className="group">
            <Card className="h-full border-dashed border-purple-400 transition group-hover:shadow-md">
              <CardBody className="pt-4">
                <div className="flex items-center justify-between"><span className="text-3xl" aria-hidden="true">{icon}</span><Simulated /></div>
                <div className="mt-2 text-lg font-semibold text-navy">{t(a as any)}</div>
                <p className="text-sm text-slate-600">{t(b as any)}</p>
              </CardBody>
            </Card>
          </Link>
        ))}
      </div>
      <p className="mt-6 rounded border border-purple-300 bg-purple-50 p-3 text-sm text-purple-900">{t("demoNote")}</p>
      {me && <p className="mt-2 text-sm text-slate-600">Signed in as {me.name}.</p>}
    </Shell>
  );
}

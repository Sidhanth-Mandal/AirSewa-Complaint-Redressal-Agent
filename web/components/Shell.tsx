"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { HOME, useSession } from "@/lib/session";
import { cn } from "@/lib/utils";
import { Button, Simulated, Spinner } from "./ui";
import Chatbot from "./Chatbot";

export const LOCALES = [{ code: "en", label: "English" }, { code: "hi", label: "हिन्दी" }]; // add languages here + messages/<code>.json

export function LangSwitch() {
  const locale = useLocale();
  const router = useRouter();
  const t = useTranslations("common");
  return (
    <label className="flex items-center gap-1 text-sm">
      <span className="sr-only">{t("language")}</span>
      <select aria-label={t("language")} value={locale} className="rounded border border-slate-400 bg-white px-2 py-1 min-h-[36px] text-sm"
        onChange={(e) => { document.cookie = `locale=${e.target.value}; path=/; max-age=31536000`; router.refresh(); }}>
        {LOCALES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
      </select>
    </label>
  );
}

const r3 = (n: number) => Math.round(n * 1000) / 1000;
function Chakra() {
  return (
    <svg width="38" height="38" viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="20" cy="20" r="17" fill="none" stroke="#0b3d91" strokeWidth="2.5" />
      {Array.from({ length: 24 }).map((_, i) => {
        const a = (i * 15 * Math.PI) / 180;
        return <line key={i} x1={r3(20 + 4 * Math.cos(a))} y1={r3(20 + 4 * Math.sin(a))} x2={r3(20 + 16 * Math.cos(a))} y2={r3(20 + 16 * Math.sin(a))} stroke="#0b3d91" strokeWidth="1" />;
      })}
      <circle cx="20" cy="20" r="3" fill="#0b3d91" />
    </svg>
  );
}

const NAV: Record<string, [string, string][]> = {
  passenger: [["/passenger", "passenger"], ["/passenger/new", "newGrievance"], ["/track", "track"]],
  redressor: [["/redressor", "queue"], ["/redressor/performance", "performance"]],
  nodal: [["/redressor", "queue"], ["/redressor/performance", "performance"], ["/redressor/staff", "staff"], ["/admin", "dashboard"]],
  agent: [["/agent", "review"], ["/agent/social", "social"], ["/agent/tickets", "allTickets"], ["/agent/closure", "closure"], ["/agent/channels", "channels"], ["/demo", "demo"], ["/admin", "dashboard"]],
  admin: [["/admin", "dashboard"], ["/admin/rules", "rules"], ["/admin/sla", "sla"], ["/admin/watchlist", "watchlist"], ["/admin/users", "users"], ["/agent/tickets", "allTickets"], ["/admin/clock", "clock"], ["/admin/settings", "settings"], ["/admin/audit", "audit"], ["/admin/api", "developer"]],
  manager: [["/manager", "control"], ["/admin", "dashboard"]],
};

export function Header({ roleNav = true }: { roleNav?: boolean }) {
  const t = useTranslations("common");
  const tn = useTranslations("nav");
  const { me, logout } = useSession();
  const path = usePathname();
  const [banner, setBanner] = useState<any>(null);
  useEffect(() => { api("/admin/public-config").then((r) => setBanner(r.crisis_banner)).catch(() => {}); }, []);
  const loc = useLocale();
  const items = me && roleNav ? NAV[me.role] || [] : [];
  return (
    <header className="bg-white shadow-sm">
      <a href="#main" className="skip-link">{t("skip")}</a>
      <div className="tricolor" />
      {banner?.active && (
        <div role="alert" className="bg-amber-100 border-b border-amber-300 text-amber-900 px-4 py-2 text-sm font-medium">
          ⚠ {loc === "hi" && banner.text_hi ? banner.text_hi : banner.text}
        </div>
      )}
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-2">
        <Link href={me ? HOME[me.role] : "/"} className="flex items-center gap-2">
          <Chakra />
          <div className="leading-tight">
            <div className="text-xl font-bold text-navy">{t("appName")} <span className="text-saffron-600">+ PACR</span></div>
            <div className="hidden text-xs text-slate-600 sm:block">{t("tagline")}</div>
          </div>
        </Link>
        <div className="flex items-center gap-3">
          <Simulated text={t("prototype")} />
          <LangSwitch />
          {me ? (
            <div className="flex items-center gap-2 text-sm">
              <span className="hidden md:inline">{t("hello")}, <b>{me.name}</b> <span className="text-slate-500">({me.role}{me.org_code ? `·${me.org_code}` : ""}{me.role === "redressor" ? `·L${me.level}` : ""})</span></span>
              <Button size="sm" variant="outline" onClick={logout}>{t("logout")}</Button>
            </div>
          ) : (
            <Link href="/login"><Button size="sm">{t("login")}</Button></Link>
          )}
        </div>
      </div>
      {items.length > 0 && (
        <nav aria-label="Main" className="border-t bg-navy">
          <ul className="mx-auto flex max-w-7xl flex-wrap gap-1 px-2">
            {items.map(([href, key]) => (
              <li key={href}>
                <Link href={href} aria-current={path === href ? "page" : undefined}
                  className={cn("block px-3 py-2.5 text-sm font-medium text-white/90 hover:bg-navy-700", path === href && "bg-navy-800 border-b-2 border-saffron text-white")}>
                  {tn(key as any)}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </header>
  );
}

export function Shell({ roles, children, wide, bot }: { roles?: string[]; children: React.ReactNode; wide?: boolean; bot?: boolean }) {
  const { me, loading } = useSession();
  const router = useRouter();
  const t = useTranslations("common");
  useEffect(() => {
    if (roles && !loading && !me) router.replace("/login?next=" + encodeURIComponent(location.pathname));
  }, [roles, loading, me, router]);
  const forbidden = roles && me && !roles.includes(me.role);
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main id="main" className={cn("mx-auto w-full flex-1 px-4 py-5", wide ? "max-w-[1600px]" : "max-w-7xl")}>
        {roles && loading ? <Spinner /> : forbidden ? (
          <div className="rounded border border-red-300 bg-red-50 p-6 text-red-900" role="alert">
            Your role ({me?.role}) cannot access this area. <Link className="underline" href={HOME[me!.role]}>Go to your home</Link>
          </div>
        ) : roles && !me ? null : children}
      </main>
      <footer className="border-t bg-white py-3 text-center text-xs text-slate-600">
        {t("appName")} + PACR · {t("prototype")} · Data shown is dummy data · WCAG 2.2 AA basics
      </footer>
      {(bot ?? true) && <Chatbot />}
    </div>
  );
}

"use client";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { StatusBadge, SevBadge } from "@/components/badges";
import { Button, Card, CardBody, Empty, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { relTime } from "@/lib/utils";

export default function PassengerHome() {
  const t = useTranslations("common");
  const tn = useTranslations("nav");
  const { me } = useSession();
  const [rows, setRows] = useState<any[] | null>(null);
  useEffect(() => { api("/tickets?limit=100").then((r) => setRows(r.items)).catch(() => setRows([])); }, []);
  return (
    <Shell roles={["passenger"]}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-navy">{tn("passenger")}</h1>
        <Link href="/passenger/new"><Button variant="saffron">{tn("newGrievance")}</Button></Link>
      </div>
      {me?.is_guest && <p className="mb-3 rounded border border-amber-300 bg-amber-50 p-3 text-sm">You are signed in as a guest. Register to keep your grievances across sessions.</p>}
      {rows === null ? <Spinner /> : rows.length === 0 ? <Card><Empty>{t("none")}</Empty></Card> : (
        <div className="grid gap-3 md:grid-cols-2">
          {rows.map((r) => (
            <Link key={r.id} href={`/tickets/${r.ticket_no}`}>
              <Card className="h-full transition hover:border-navy hover:shadow">
                <CardBody className="pt-4">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-navy">{r.ticket_no}</span><StatusBadge s={r.status} />
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm">{r.description}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                    <SevBadge s={r.severity} /> <span>{r.category}/{r.subcategory}</span> · <span>{r.assigned_org}</span> · <span>{relTime(r.created_at)}</span>
                  </div>
                </CardBody>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </Shell>
  );
}

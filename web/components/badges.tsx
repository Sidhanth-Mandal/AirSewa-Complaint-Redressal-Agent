"use client";
import { useTranslations } from "next-intl";
import { Badge } from "./ui";
import { SEV_LABEL, SEV_STYLE, STATUS_STYLE, cn } from "@/lib/utils";

export function SevBadge({ s, reason }: { s: number; reason?: string }) {
  return <Badge className={SEV_STYLE[s]} title={reason}>{SEV_LABEL[s] || `S${s}`}</Badge>;
}
export function StatusBadge({ s }: { s: string }) {
  const t = useTranslations("status");
  let label = s;
  try { label = t(s as any); } catch {}
  return <Badge className={cn(STATUS_STYLE[s] || "bg-slate-100")}>{label}</Badge>;
}
export const SourceChip = ({ ch, type }: { ch: string; type?: string | null }) => (
  <Badge className="bg-slate-100 text-slate-700">{ch.replace("social_", "").replace("_", " ")}{type ? `/${type}` : ""}</Badge>
);

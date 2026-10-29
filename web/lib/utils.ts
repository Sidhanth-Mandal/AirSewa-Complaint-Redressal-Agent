import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export const cn = (...i: ClassValue[]) => twMerge(clsx(i));

export function relTime(iso?: string | null, now = Date.now()): string {
  if (!iso) return "-";
  const s = Math.round((now - new Date(iso).getTime()) / 1000);
  if (s < 5) return "just now"; // also covers small client/server clock skew
  return fmtDur(s) + " ago";
}
export function fmtDur(s: number): string {
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}
export const fmtDate = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "-";
export const fmtHours = (h?: number | null) => (h == null ? "-" : h < 1 ? `${Math.round(h * 60)}m` : h < 48 ? `${h.toFixed(1)}h` : `${(h / 24).toFixed(1)}d`);
export const SEV_STYLE: Record<number, string> = {
  1: "bg-red-600 text-white", 2: "bg-orange-500 text-white", 3: "bg-amber-100 text-amber-900 border border-amber-300", 4: "bg-slate-100 text-slate-700 border border-slate-300",
};
export const SEV_LABEL: Record<number, string> = { 1: "S1 Critical", 2: "S2 High", 3: "S3 Medium", 4: "S4 Low" };
export const STATUS_STYLE: Record<string, string> = {
  "Under Assessment": "bg-slate-100 text-slate-800", Assigned: "bg-blue-100 text-blue-900", "In-Progress": "bg-indigo-100 text-indigo-900",
  "On Hold - Awaiting Passenger Inputs": "bg-yellow-100 text-yellow-900", "Provisionally Resolved": "bg-teal-100 text-teal-900", Resolved: "bg-green-100 text-green-900",
  Reopened: "bg-pink-100 text-pink-900", Escalated: "bg-red-100 text-red-900", Closed: "bg-slate-200 text-slate-800",
};

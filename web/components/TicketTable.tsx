"use client";
import Link from "next/link";
import { Badge } from "./ui";
import { SevBadge, SourceChip, StatusBadge } from "./badges";
import { relTime } from "@/lib/utils";

export type TicketRow = {
  id: number; ticket_no: string; category: string; subcategory: string; severity: number; status: string; source_channel: string; source_type?: string;
  created_at: string; due_at?: string; level: number; assigned_org?: string; assigned_user?: string; airport?: string; breached: boolean; description: string;
  queue: string; reopen_count: number; related_count: number; disputed: boolean;
};

export function TicketTable({ rows, selectable, selected, onSelect, cols = ["org", "assignee"] }: {
  rows: TicketRow[]; selectable?: boolean; selected?: number[]; onSelect?: (ids: number[]) => void; cols?: string[];
}) {
  const sel = selected || [];
  const toggle = (id: number) => onSelect?.(sel.includes(id) ? sel.filter((x) => x !== id) : [...sel, id]);
  return (
    <div className="overflow-x-auto scroll-thin">
      <table className="w-full min-w-[760px] text-left text-sm">
        <caption className="sr-only">Grievances</caption>
        <thead className="bg-slate-100 text-xs uppercase text-slate-600">
          <tr>
            {selectable && <th className="w-8 p-2"><input type="checkbox" aria-label="Select all" onChange={(e) => onSelect?.(e.target.checked ? rows.map((r) => r.id) : [])} checked={rows.length > 0 && sel.length === rows.length} /></th>}
            <th className="p-2">Ticket</th><th className="p-2">Issue</th><th className="p-2">Priority</th><th className="p-2">Status</th>
            {cols.includes("org") && <th className="p-2">Stakeholder</th>}{cols.includes("assignee") && <th className="p-2">Level / owner</th>}
            <th className="p-2">Source</th><th className="p-2">Created</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t hover:bg-slate-50 align-top">
              {selectable && <td className="p-2"><input type="checkbox" aria-label={`Select ${r.ticket_no}`} checked={sel.includes(r.id)} onChange={() => toggle(r.id)} /></td>}
              <td className="p-2 whitespace-nowrap">
                <Link href={`/tickets/${r.ticket_no}`} className="font-semibold text-navy underline">{r.ticket_no}</Link>
                <div className="mt-1 flex flex-wrap gap-1">
                  {r.breached && <Badge className="bg-red-100 text-red-800">SLA breach</Badge>}
                  {r.queue === "committee" && <Badge className="bg-purple-100 text-purple-800">Committee</Badge>}
                  {r.queue === "pacr" && <Badge className="bg-orange-100 text-orange-800">PACR</Badge>}
                  {r.reopen_count > 0 && <Badge className="bg-pink-100 text-pink-800">Reopened ×{r.reopen_count}</Badge>}
                  {r.related_count > 0 && <Badge className="bg-blue-100 text-blue-800">{r.related_count} related</Badge>}
                </div>
              </td>
              <td className="max-w-[320px] p-2"><div className="text-xs font-semibold text-slate-600">{r.category}/{r.subcategory}{r.airport ? ` · ${r.airport}` : ""}</div><div className="line-clamp-2">{r.description}</div></td>
              <td className="p-2"><SevBadge s={r.severity} /></td>
              <td className="p-2"><StatusBadge s={r.status} /></td>
              {cols.includes("org") && <td className="p-2">{r.assigned_org}</td>}
              {cols.includes("assignee") && <td className="p-2 whitespace-nowrap">L{r.level > 3 ? "N" : r.level}{r.assigned_user ? ` · ${r.assigned_user}` : ""}</td>}
              <td className="p-2"><SourceChip ch={r.source_channel} type={r.source_type} /></td>
              <td className="whitespace-nowrap p-2 text-slate-600">{relTime(r.created_at)}</td>
            </tr>
          ))}
          {rows.length === 0 && <tr><td colSpan={9} className="p-6 text-center text-slate-500">No grievances found.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

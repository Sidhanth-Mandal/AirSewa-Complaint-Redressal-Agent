"use client";
import { Shell } from "@/components/Shell";
import TicketList from "@/components/TicketList";

export default function AllTickets() {
  return (
    <Shell roles={["agent", "admin"]} wide>
      <h1 className="mb-1 text-2xl font-bold text-navy">All tickets - search, override, bulk assess</h1>
      <p className="mb-3 text-sm text-slate-600">Select multiple tickets to override severity or reassign in bulk. Open a ticket to reclassify, merge duplicates (parent/child) or re-verify closure.</p>
      <TicketList base={{ status: "open", sort: "severity" }} bulk />
    </Shell>
  );
}

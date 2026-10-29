"use client";
import Link from "next/link";
import { Shell } from "@/components/Shell";
import Simulator from "@/components/Simulator";
import { Button, Simulated } from "@/components/ui";

export default function SimulatorPage() {
  return (
    <Shell wide bot={false}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div><h1 className="flex items-center gap-2 text-2xl font-bold text-navy">Social Simulator <Simulated /></h1>
          <p className="text-sm text-slate-600">Two generic social apps (own icons, no brand assets). Post a complaint tagging a watched handle - PACR detects it instantly. No real X/Instagram API is used.</p></div>
        <Link href="/demo"><Button variant="saffron">Open split-screen demo</Button></Link>
      </div>
      <div className="mx-auto max-w-3xl"><Simulator /></div>
    </Shell>
  );
}

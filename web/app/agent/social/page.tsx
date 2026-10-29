"use client";
import Link from "next/link";
import { Shell } from "@/components/Shell";
import PacrFeed from "@/components/PacrFeed";
import { Button, Simulated } from "@/components/ui";

export default function Social() {
  return (
    <Shell roles={["agent", "admin", "manager"]} wide>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold text-navy">PACR Live Social Feed <Simulated /></h1>
        <div className="flex gap-2"><Link href="/demo"><Button variant="saffron">Open split-screen demo</Button></Link><Link href="/simulator" target="_blank"><Button variant="outline">Open social simulator</Button></Link></div>
      </div>
      <PacrFeed readOnly={false} />
    </Shell>
  );
}

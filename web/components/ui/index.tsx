"use client";
// Minimal shadcn/ui-style primitives (Button, Card, Badge, Input, Select, Tabs, Modal, Toaster) - local copies, no external CLI.
import { cva, type VariantProps } from "class-variance-authority";
import { createContext, useCallback, useContext, useEffect, useId, useState } from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px] px-4 text-base",
  {
    variants: {
      variant: {
        default: "bg-navy text-white hover:bg-navy-700",
        saffron: "bg-saffron text-slate-900 hover:bg-orange-400",
        green: "bg-india text-white hover:bg-india-700",
        danger: "bg-red-600 text-white hover:bg-red-700",
        outline: "border border-slate-300 bg-white hover:bg-slate-100 text-slate-900",
        ghost: "hover:bg-slate-100 text-slate-800",
      },
      size: { default: "", sm: "min-h-[34px] px-3 text-sm", lg: "min-h-[52px] px-6 text-lg" },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);
export function Button({ className, variant, size, ...p }: React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonVariants>) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...p} />;
}

export function Card({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-lg border border-slate-200 bg-white shadow-sm", className)} {...p} />;
}
export const CardHeader = ({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) => <div className={cn("px-4 pt-4 pb-2 flex items-center justify-between gap-2", className)} {...p} />;
export const CardTitle = ({ className, ...p }: React.HTMLAttributes<HTMLHeadingElement>) => <h2 className={cn("font-semibold text-navy text-lg", className)} {...p} />;
export const CardBody = ({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) => <div className={cn("px-4 pb-4", className)} {...p} />;

export function Badge({ className, ...p }: React.HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap", className)} {...p} />;
}
export const Simulated = ({ text = "Simulated" }: { text?: string }) => (
  <span className="inline-flex items-center rounded border border-dashed border-purple-500 bg-purple-50 px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-purple-700" title="Simulated: no real external system is connected">{text}</span>
);

export const Label = ({ className, ...p }: React.LabelHTMLAttributes<HTMLLabelElement>) => <label className={cn("block text-sm font-medium text-slate-800 mb-1", className)} {...p} />;
const fieldCls = "w-full rounded-md border border-slate-400 bg-white px-3 py-2 min-h-[44px] text-base focus:border-navy placeholder:text-slate-500";
export const Input = ({ className, ...p }: React.InputHTMLAttributes<HTMLInputElement>) => <input className={cn(fieldCls, className)} {...p} />;
export const Textarea = ({ className, ...p }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) => <textarea className={cn(fieldCls, "min-h-[96px]", className)} {...p} />;
export const Select = ({ className, ...p }: React.SelectHTMLAttributes<HTMLSelectElement>) => <select className={cn(fieldCls, className)} {...p} />;

export function Field({ label, error, hint, children, required }: { label: string; error?: string; hint?: string; children: (id: string) => React.ReactNode; required?: boolean }) {
  const id = useId();
  return (
    <div>
      <Label htmlFor={id}>
        {label} {required && <span className="text-red-600" aria-hidden="true">*</span>}
      </Label>
      {children(id)}
      {hint && !error && <p className="text-xs text-slate-600 mt-1">{hint}</p>}
      {error && <p role="alert" className="text-sm text-red-700 mt-1">{error}</p>}
    </div>
  );
}

export function Tabs({ tabs, value, onChange, className }: { tabs: { id: string; label: React.ReactNode }[]; value: string; onChange: (v: string) => void; className?: string }) {
  return (
    <div role="tablist" className={cn("flex flex-wrap gap-1 border-b border-slate-300", className)}>
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={cn("px-4 py-2 min-h-[44px] -mb-px border-b-2 font-medium", value === t.id ? "border-navy text-navy" : "border-transparent text-slate-600 hover:text-navy")}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function Modal({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode; wide?: boolean }) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-4 overflow-y-auto" role="dialog" aria-modal="true" aria-label={title} onClick={onClose}>
      <div className={cn("mt-10 w-full rounded-lg bg-white p-5 shadow-xl", wide ? "max-w-3xl" : "max-w-lg")} onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-start justify-between gap-3">
          <h2 className="text-lg font-semibold text-navy">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded p-1 text-2xl leading-none hover:bg-slate-100">×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ---- toasts (also used to show the simulated OTP "dev toast")
type Toast = { id: number; text: string; kind: "info" | "error" | "success" | "alert"; sticky?: boolean };
const ToastCtx = createContext<{ push: (text: string, kind?: Toast["kind"], sticky?: boolean) => void }>({ push: () => {} });
export const useToast = () => useContext(ToastCtx);
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((text: string, kind: Toast["kind"] = "info", sticky = false) => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x.slice(-4), { id, text, kind, sticky }]);
    if (!sticky) setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), kind === "alert" ? 9000 : 5000);
  }, []);
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] flex w-[min(92vw,380px)] flex-col gap-2" aria-live="polite" role="status">
        {items.map((t) => (
          <div key={t.id} className={cn("animate-slidein rounded-lg border p-3 shadow-lg text-sm flex gap-2 justify-between",
            t.kind === "error" ? "bg-red-50 border-red-300 text-red-900" : t.kind === "success" ? "bg-green-50 border-green-300 text-green-900" :
            t.kind === "alert" ? "bg-red-600 border-red-700 text-white animate-pulsering" : "bg-white border-slate-300")}>
            <span>{t.text}</span>
            <button onClick={() => setItems((x) => x.filter((i) => i.id !== t.id))} aria-label="Dismiss" className="font-bold">×</button>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function Spinner() { return <div className="p-6 text-slate-500" role="status">Loading…</div>; }
export function Empty({ children }: { children: React.ReactNode }) { return <div className="p-6 text-center text-slate-500">{children}</div>; }

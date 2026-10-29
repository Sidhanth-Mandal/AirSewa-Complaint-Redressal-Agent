"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api";

export type Me = { id: number; name: string; role: string; email?: string; mobile?: string; org?: string; org_code?: string; org_id?: number; level: number; is_guest: boolean; lang: string; access_type: string; designation?: string } | null;
type Ctx = { me: Me; loading: boolean; refresh: () => Promise<void>; logout: () => Promise<void> };
const SessionCtx = createContext<Ctx>({ me: null, loading: true, refresh: async () => {}, logout: async () => {} });

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me>(null);
  const [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    try { setMe(await api("/auth/me")); } catch { setMe(null); }
    setLoading(false);
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  const logout = useCallback(async () => { await api("/auth/logout", { method: "POST" }); setMe(null); window.location.href = "/"; }, []);
  return <SessionCtx.Provider value={{ me, loading, refresh, logout }}>{children}</SessionCtx.Provider>;
}
export const useSession = () => useContext(SessionCtx);

export const HOME: Record<string, string> = { passenger: "/passenger", redressor: "/redressor", nodal: "/redressor", agent: "/agent", admin: "/admin", manager: "/manager" };

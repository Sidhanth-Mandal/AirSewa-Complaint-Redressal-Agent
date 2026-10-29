"use client";
import { useEffect, useRef } from "react";

/** Subscribe to server-sent events (real-time). Reconnects automatically (EventSource built-in). */
export function useSSE(topics: string[], onEvent: (name: string, data: any) => void, enabled = true) {
  const cb = useRef(onEvent);
  cb.current = onEvent;
  const key = topics.join(",");
  useEffect(() => {
    if (!enabled || !key) return;
    const es = new EventSource(`/api/stream?topics=${encodeURIComponent(key)}`, { withCredentials: true });
    const names = Array.from(new Set(key.split(",").map((t) => t.split(":")[0])));
    names.forEach((n) =>
      es.addEventListener(n, (ev: MessageEvent) => {
        try { cb.current(n, JSON.parse(ev.data)); } catch {}
      })
    );
    return () => es.close();
  }, [key, enabled]);
}

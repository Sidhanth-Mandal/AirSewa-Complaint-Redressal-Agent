"use client";
// Generic X-style and Instagram-style social apps used only to SIMULATE complaints. Own icons, no official logos or brand assets.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import { cn, relTime } from "@/lib/utils";
import { Badge, Button, Simulated, Tabs, useToast } from "./ui";

type U = { handle: string; name: string; color: string; lang: string; bio: string; is_official: boolean };
type P = { id: number; platform: string; source_type: string; author_handle: string; author_name: string; text: string; created_at: string; lang: string; mentions: string[]; hashtags: string[]; media: any[]; location?: string; parent_post_id?: number | null; target_handle?: string; likes: number; reposts: number; replies: number; pending?: boolean };

function useNow(ms = 1000) {
  const [n, setN] = useState(Date.now());
  useEffect(() => { const i = setInterval(() => setN(Date.now()), ms); return () => clearInterval(i); }, [ms]);
  return n;
}
const Avatar = ({ u, size = 40 }: { u?: { name: string; color: string }; size?: number }) => (
  <span aria-hidden="true" className="inline-flex shrink-0 items-center justify-center rounded-full font-bold text-white" style={{ width: size, height: size, background: u?.color || "#64748b", fontSize: size * 0.4 }}>{(u?.name || "?").replace(/[^\p{L}]/gu, "").slice(0, 1).toUpperCase()}</span>
);
function Rich({ text }: { text: string }) {
  return <>{text.split(/(@[\w.]+|#[\w\u0900-\u097f]+)/g).map((p, i) => (p.startsWith("@") ? <span key={i} className="text-sky-600">{p}</span> : p.startsWith("#") ? <span key={i} className="text-sky-600">{p}</span> : <span key={i}>{p}</span>))}</>;
}
function Media({ m }: { m: any }) {
  if (m.url) return <img src={`/api${m.url}`} alt={m.name || "attached image"} className="mt-2 max-h-72 w-full rounded-xl border object-cover" />;
  const g = /bag|luggage/.test(m.name || "") ? "from-orange-300 to-red-400" : /dirty|toilet/.test(m.name || "") ? "from-lime-300 to-emerald-500" : /queue/.test(m.name || "") ? "from-sky-300 to-indigo-400" : "from-fuchsia-300 to-purple-500";
  return <div className={`mt-2 flex h-40 items-center justify-center rounded-xl bg-gradient-to-br ${g} text-sm font-semibold text-white`} role="img" aria-label={`Sample image ${m.name}`}>🖼 {m.name || "photo"}</div>;
}
const XLogo = () => <span className="text-xl font-black" aria-hidden="true">✕</span>;

// --- mention autocomplete composer
function Composer({ users, placeholder, max, onSubmit, button = "Post", platform, autoFocus, initial = "" }: { users: U[]; placeholder: string; max?: number; onSubmit: (text: string, media: any[]) => Promise<void>; button?: string; platform: string; autoFocus?: boolean; initial?: string }) {
  const [text, setText] = useState(initial);
  const [media, setMedia] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [sug, setSug] = useState<U[]>([]);
  const [idx, setIdx] = useState(0);
  const ta = useRef<HTMLTextAreaElement>(null);
  const { push } = useToast();
  function onChange(v: string) {
    setText(v);
    const m = /@([\w.]*)$/.exec(v.slice(0, ta.current?.selectionStart ?? v.length));
    if (m) setSug(users.filter((u) => u.handle.toLowerCase().includes(m[1].toLowerCase())).slice(0, 6)), setIdx(0);
    else setSug([]);
  }
  function pick(u: U) {
    const pos = ta.current?.selectionStart ?? text.length;
    const before = text.slice(0, pos).replace(/@[\w.]*$/, u.handle + " ");
    setText(before + text.slice(pos)); setSug([]); ta.current?.focus();
  }
  async function attach(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    try { setMedia([...media, await api("/sim/media", { form: fd })]); } catch (x: any) { push(x.message, "error"); }
    e.target.value = "";
  }
  async function go() {
    if (!text.trim() || busy) return;
    setBusy(true);
    try { await onSubmit(text.trim(), media); setText(""); setMedia([]); } catch (x: any) { push(x.message, "error"); }
    setBusy(false);
  }
  const left = max ? max - text.length : null;
  return (
    <div className="relative">
      <textarea ref={ta} autoFocus={autoFocus} value={text} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={placeholder} rows={3}
        onKeyDown={(e) => {
          if (sug.length) { if (e.key === "ArrowDown") { e.preventDefault(); setIdx((idx + 1) % sug.length); } else if (e.key === "ArrowUp") { e.preventDefault(); setIdx((idx + sug.length - 1) % sug.length); } else if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); pick(sug[idx]); } else if (e.key === "Escape") setSug([]); }
          else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) go();
        }}
        className="w-full resize-none rounded-lg border border-slate-300 bg-white p-2 text-[15px] focus:border-sky-500" />
      {sug.length > 0 && (
        <ul role="listbox" className="absolute z-20 mt-0.5 w-72 rounded-lg border bg-white shadow-lg">
          {sug.map((u, i) => <li key={u.handle} role="option" aria-selected={i === idx} onMouseDown={(e) => { e.preventDefault(); pick(u); }} className={cn("flex cursor-pointer items-center gap-2 px-3 py-1.5 text-sm", i === idx && "bg-sky-50")}><Avatar u={u} size={24} /><span><b>{u.name}</b> <span className="text-slate-500">{u.handle}</span></span>{u.is_official && <Badge className="bg-sky-100 text-sky-700">official</Badge>}</li>)}
        </ul>
      )}
      {media.map((m, i) => <div key={i} className="mt-1 flex items-center gap-2 text-xs text-slate-600">🖼 {m.name} <button className="text-red-600" onClick={() => setMedia(media.filter((_, j) => j !== i))}>remove</button></div>)}
      <div className="mt-1 flex items-center justify-between">
        <label className="cursor-pointer rounded-full p-2 text-sky-600 hover:bg-sky-50" title="Attach image"><span aria-hidden="true">🖼</span><span className="sr-only">Attach image</span><input type="file" accept="image/*" className="sr-only" onChange={attach} /></label>
        <div className="flex items-center gap-3">
          {left !== null && <span className={cn("text-sm tabular-nums", left < 0 ? "font-bold text-red-600" : left < 20 ? "text-amber-600" : "text-slate-500")} aria-live="polite">{left}</span>}
          <button onClick={go} disabled={busy || !text.trim() || (left !== null && left < 0)} className="rounded-full bg-sky-500 px-5 py-1.5 font-bold text-white hover:bg-sky-600 disabled:opacity-50">{busy ? "…" : button}</button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- X-style app
function XApp({ me, users, officials, onPosted }: { me: U; users: U[]; officials: U[]; onPosted?: (r: any) => void }) {
  const all = useMemo(() => [...users, ...officials], [users, officials]);
  const by = useMemo(() => Object.fromEntries(all.map((u) => [u.handle, u])), [all]);
  const [posts, setPosts] = useState<P[]>([]);
  const [view, setView] = useState<"home" | "notif">("home");
  const [notifs, setNotifs] = useState<any[]>([]);
  const [unread, setUnread] = useState(0);
  const [threads, setThreads] = useState<Record<number, P[]>>({});
  const [reply, setReply] = useState<number | null>(null);
  const [quote, setQuote] = useState<P | null>(null);
  const now = useNow();
  const { push } = useToast();

  const loadFeed = useCallback(() => api("/sim/feed?platform=X&limit=50").then(setPosts), []);
  const loadNotifs = useCallback(() => api(`/sim/notifications?handle=${encodeURIComponent(me.handle)}`).then((n) => { setNotifs(n); setUnread(n.filter((x: any) => !x.read).length); }), [me.handle]);
  useEffect(() => { loadFeed(); }, [loadFeed]);
  useEffect(() => { loadNotifs(); setView("home"); }, [loadNotifs]);
  useSSE(["social_feed", `social_notif:${me.handle.toLowerCase()}`], (n, ev) => {
    if (n === "social_feed") {
      const p: P = ev.post;
      if (p.platform !== "X") return;
      if (ev.type === "post") {
        if (p.source_type === "post" || p.source_type === "quote") setPosts((x) => (x.some((y) => y.id === p.id) ? x : [p, ...x.filter((y) => !(y.pending && y.text === p.text && y.author_handle === p.author_handle))]));
        setThreads((t) => (p.parent_post_id && t[p.parent_post_id] && !t[p.parent_post_id].some((y) => y.id === p.id) ? { ...t, [p.parent_post_id]: [...t[p.parent_post_id], p] } : t));
        if (p.parent_post_id) setPosts((x) => x.map((y) => (y.id === p.parent_post_id ? { ...y, replies: Math.max(y.replies, (y.replies || 0)) } : y)));
      }
      if (ev.type === "engagement" || ev.type === "post") setPosts((x) => x.map((y) => (y.id === p.id ? { ...y, likes: p.likes, reposts: p.reposts, replies: p.replies } : y)));
    } else { loadNotifs(); push(`🔔 ${me.handle}: ${ev.text?.slice(0, 90)}`, "info"); }
  });

  async function submit(text: string, media: any[], extra: any = {}) {
    const temp: P = { id: -Date.now(), platform: "X", source_type: extra.source_type || "post", author_handle: me.handle, author_name: me.name, text, created_at: new Date().toISOString(), lang: "", mentions: [], hashtags: [], media, likes: 0, reposts: 0, replies: 0, pending: true, parent_post_id: extra.parent_post_id };
    if (!extra.parent_post_id || extra.source_type === "quote") setPosts((x) => [temp, ...x]);
    try {
      const r = await api("/sim/posts", { body: { platform: "X", source_type: "post", author_handle: me.handle, text, media, ...extra } });
      setPosts((x) => { const rest = x.filter((y) => y.id !== temp.id && y.id !== r.post.id); return !extra.parent_post_id || extra.source_type === "quote" ? [r.post, ...rest] : rest.map((y) => (y.id === extra.parent_post_id ? { ...y, replies: y.replies + 1 } : y)); });
      if (extra.parent_post_id && extra.source_type === "reply") setThreads((t) => (t[extra.parent_post_id] ? { ...t, [extra.parent_post_id]: [...t[extra.parent_post_id].filter((y) => y.id !== r.post.id), r.post] } : t));
      onPosted?.(r);
    } catch (e) { setPosts((x) => x.filter((y) => y.id !== temp.id)); throw e; }
  }
  async function engage(p: P, kind: "like" | "repost") {
    setPosts((x) => x.map((y) => (y.id === p.id ? { ...y, [kind === "like" ? "likes" : "reposts"]: (kind === "like" ? y.likes : y.reposts) + 1 } : y)));
    api(`/sim/posts/${p.id}/${kind}`, { method: "POST" }).catch(() => {});
  }
  async function toggleThread(p: P) {
    if (threads[p.id]) return setThreads(({ [p.id]: _, ...rest }) => rest);
    const r = await api(`/sim/posts/${p.id}`);
    setThreads((t) => ({ ...t, [p.id]: r.replies }));
  }
  const card = (p: P, nested = false) => {
    const u = by[p.author_handle];
    const quoted = p.source_type === "quote" && p.parent_post_id ? posts.find((y) => y.id === p.parent_post_id) : null;
    return (
      <article key={p.id} className={cn("flex gap-3 border-b border-slate-200 p-3", p.pending && "opacity-60", nested && "ml-10 border-l")} aria-label={`Post by ${p.author_name}`}>
        <Avatar u={u} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1 text-[15px]"><b>{p.author_name}</b>{u?.is_official && <span title="Official (simulated)" className="text-sky-500">✔</span>}<span className="text-slate-500">{p.author_handle}</span><span className="text-slate-400">· {p.pending ? "posting…" : relTime(p.created_at, now)}</span>{p.source_type === "reply" && <span className="text-xs text-slate-400">replying to {by[p.target_handle || ""]?.handle || "thread"}</span>}</div>
          <p className="whitespace-pre-wrap break-words text-[15px]"><Rich text={p.text} /></p>
          {p.media?.map((m, i) => <Media key={i} m={m} />)}
          {quoted && <div className="mt-2 rounded-xl border p-2 text-sm"><b>{quoted.author_name}</b> <span className="text-slate-500">{quoted.author_handle}</span><p><Rich text={quoted.text} /></p></div>}
          {!nested && (
            <div className="mt-1 flex items-center gap-5 text-sm text-slate-500">
              <button onClick={() => setReply(reply === p.id ? null : p.id)} className="hover:text-sky-600" aria-label={`Reply, ${p.replies} replies`}>💬 {p.replies}</button>
              <button onClick={() => engage(p, "repost")} className="hover:text-green-600" aria-label={`Repost, ${p.reposts}`}>🔁 {p.reposts}</button>
              <button onClick={() => engage(p, "like")} className="hover:text-pink-600" aria-label={`Like, ${p.likes}`}>♡ {p.likes}</button>
              <button onClick={() => setQuote(p)} className="hover:text-sky-600" aria-label="Quote">❝ quote</button>
              <button onClick={() => submit("+1 same issue happened to me", [], { source_type: "reply", parent_post_id: p.id }).catch((e) => push(e.message, "error"))} className="rounded border border-slate-300 px-2 py-0.5 text-xs hover:bg-slate-100">+1 same issue</button>
              {p.replies > 0 && <button onClick={() => toggleThread(p)} className="text-sky-600">{threads[p.id] ? "hide thread" : "show thread"}</button>}
            </div>
          )}
          {reply === p.id && <div className="mt-2"><Composer users={all} platform="X" placeholder={`Reply to ${p.author_handle}`} max={280} button="Reply" autoFocus onSubmit={async (t, m) => { await submit(t, m, { source_type: "reply", parent_post_id: p.id }); setReply(null); }} /></div>}
          {threads[p.id]?.map((r) => card(r, true))}
        </div>
      </article>
    );
  };
  return (
    <div className="grid min-h-[480px] grid-cols-1 bg-white text-slate-900 md:grid-cols-[170px_1fr]">
      <nav className="flex gap-1 border-b p-2 md:flex-col md:border-b-0 md:border-r" aria-label="X-style navigation">
        <div className="hidden p-2 md:block"><XLogo /></div>
        <button onClick={() => setView("home")} className={cn("rounded-full px-3 py-2 text-left font-semibold hover:bg-slate-100", view === "home" && "bg-slate-100")}>🏠 Home</button>
        <button onClick={() => { setView("notif"); loadNotifs(); api(`/sim/notifications?handle=${encodeURIComponent(me.handle)}&mark_read=true`).then(() => setUnread(0)); }} className={cn("rounded-full px-3 py-2 text-left font-semibold hover:bg-slate-100", view === "notif" && "bg-slate-100")}>🔔 Notifications {unread > 0 && <span className="ml-1 rounded-full bg-sky-500 px-1.5 text-xs text-white">{unread}</span>}</button>
      </nav>
      <div className="min-w-0">
        {view === "home" ? (
          <>
            <div className="flex gap-3 border-b border-slate-200 p-3"><Avatar u={me} /><div className="flex-1">
              <Composer users={all} platform="X" placeholder="What's happening? Tag @IndiGo6E, @AAI_Official, @MoCA_GoI …" max={280} onSubmit={(t, m) => submit(t, m)} />
              {quote && <div className="mt-2 rounded border p-2 text-sm">Quoting {quote.author_handle}: “{quote.text.slice(0, 80)}” <button className="text-red-600" onClick={() => setQuote(null)}>cancel</button>
                <Composer users={all} platform="X" placeholder="Add your comment" max={280} button="Quote" onSubmit={async (t) => { await submit(t, [], { source_type: "quote", parent_post_id: quote.id }); setQuote(null); }} /></div>}
            </div></div>
            <div aria-live="polite">{posts.map((p) => card(p))}</div>
            {posts.length === 0 && <p className="p-6 text-center text-slate-500">No posts yet.</p>}
          </>
        ) : (
          <div><h2 className="border-b p-3 text-lg font-bold">Notifications for {me.handle}</h2>
            {notifs.length === 0 && <p className="p-6 text-slate-500">No notifications yet. When PACR acknowledges your complaint, the official reply appears here.</p>}
            {notifs.map((n) => <div key={n.id} className={cn("flex gap-3 border-b p-3", !n.read && "bg-sky-50")}><Avatar u={by[n.from]} /><div><div className="text-sm"><b>{by[n.from]?.name || n.from}</b> <span className="text-slate-500">{n.from} · {relTime(n.at, now)}</span> {n.kind === "status" && <Badge className="bg-green-100 text-green-800">status update</Badge>}</div><p className="text-[15px]">{n.text}</p>{n.ticket_no && <span className="text-xs text-slate-500">Ticket {n.ticket_no}</span>}</div></div>)}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Instagram-style app
function IGApp({ me, users, officials, onPosted }: { me: U; users: U[]; officials: U[]; onPosted?: (r: any) => void }) {
  const all = useMemo(() => [...users, ...officials], [users, officials]);
  const by = useMemo(() => Object.fromEntries(all.map((u) => [u.handle, u])), [all]);
  const [tab, setTab] = useState("feed");
  const [posts, setPosts] = useState<P[]>([]);
  const [stories, setStories] = useState<P[]>([]);
  const [comments, setComments] = useState<Record<number, P[]>>({});
  const [airports, setAirports] = useState<any[]>([]);
  const [dmWith, setDmWith] = useState("@AirSewa_Official");
  const [dm, setDm] = useState<P[]>([]);
  const [cap, setCap] = useState({ loc: "", media: [] as any[], text: "" });
  const [story, setStory] = useState({ to: "@airindia", text: "" });
  const [notifs, setNotifs] = useState<any[]>([]);
  const now = useNow();
  const { push } = useToast();
  const loadFeed = useCallback(() => { api("/sim/feed?platform=Instagram&limit=40").then(setPosts); api("/sim/stories").then(setStories); }, []);
  const loadDm = useCallback(() => api(`/sim/dm?handle=${encodeURIComponent(me.handle)}`).then(setDm), [me.handle]);
  const loadNotifs = useCallback(() => api(`/sim/notifications?handle=${encodeURIComponent(me.handle)}`).then(setNotifs), [me.handle]);
  useEffect(() => { loadFeed(); api("/meta").then((m) => setAirports(m.airports)); }, [loadFeed]);
  useEffect(() => { loadDm(); loadNotifs(); }, [loadDm, loadNotifs]);
  useSSE(["social_feed", `social_notif:${me.handle.toLowerCase()}`], (n, ev) => {
    if (n === "social_notif") { loadNotifs(); loadDm(); push(`🔔 ${ev.text?.slice(0, 90)}`, "info"); return; }
    const p: P = ev.post;
    if (p.platform !== "Instagram") return;
    if (ev.type === "post") {
      if (p.source_type === "post") setPosts((x) => (x.some((y) => y.id === p.id) ? x : [p, ...x]));
      if (p.source_type === "story_mention") setStories((x) => (x.some((y) => y.id === p.id) ? x : [p, ...x]));
      if (p.source_type === "comment" && p.parent_post_id) setComments((c) => (c[p.parent_post_id!] && !c[p.parent_post_id!].some((y) => y.id === p.id) ? { ...c, [p.parent_post_id!]: [...c[p.parent_post_id!], p] } : c));
      if (p.source_type === "dm" && (p.author_handle === me.handle || p.target_handle === me.handle)) loadDm();
    }
  });
  const send = async (body: any) => { const r = await api("/sim/posts", { body: { platform: "Instagram", author_handle: me.handle, ...body } }); onPosted?.(r); return r; };
  async function loadComments(p: P) { const r = await api(`/sim/posts/${p.id}`); setComments((c) => ({ ...c, [p.id]: r.replies })); }
  const dmThread = dm.filter((m) => m.author_handle === dmWith || m.target_handle === dmWith);
  return (
    <div className="bg-white text-slate-900">
      <div className="flex items-center justify-between border-b p-2"><span className="bg-gradient-to-r from-fuchsia-600 to-orange-500 bg-clip-text text-xl font-extrabold text-transparent">Instasim</span>
        <Tabs value={tab} onChange={setTab} className="border-0" tabs={[{ id: "feed", label: "Feed" }, { id: "create", label: "＋ Create" }, { id: "story", label: "Story mention" }, { id: "dm", label: "✉ Inbox" }, { id: "act", label: `♡ Activity${notifs.length ? ` (${notifs.length})` : ""}` }]} /></div>
      {tab === "feed" && (
        <div>
          <div className="flex gap-3 overflow-x-auto border-b p-3" aria-label="Stories">{stories.length === 0 && <span className="text-sm text-slate-500">No stories yet - use “Story mention”.</span>}{stories.map((s) => <div key={s.id} className="w-16 shrink-0 text-center text-xs" title={s.text}><div className="mx-auto rounded-full bg-gradient-to-tr from-yellow-400 via-fuchsia-500 to-purple-600 p-0.5"><div className="rounded-full bg-white p-0.5"><Avatar u={by[s.author_handle]} size={52} /></div></div><div className="truncate">{s.author_handle.replace("@", "")}</div></div>)}</div>
          {posts.map((p) => {
            const u = by[p.author_handle];
            return (
              <article key={p.id} className="border-b pb-3" aria-label={`Post by ${p.author_name}`}>
                <div className="flex items-center gap-2 p-3"><Avatar u={u} size={32} /><div className="text-sm"><b>{p.author_name}</b> {u?.is_official && <span className="text-sky-500">✔</span>}{p.location && <div className="text-xs text-slate-500">📍 {p.location}</div>}</div><span className="ml-auto text-xs text-slate-400">{relTime(p.created_at, now)}</span></div>
                {(p.media?.length ? p.media : [{ name: "photo" }]).map((m, i) => <Media key={i} m={m} />)}
                <div className="flex gap-4 px-3 pt-2 text-xl"><button aria-label="Like" onClick={() => { setPosts((x) => x.map((y) => (y.id === p.id ? { ...y, likes: y.likes + 1 } : y))); api(`/sim/posts/${p.id}/like`, { method: "POST" }); }}>♡</button><button aria-label="Comments" onClick={() => loadComments(p)}>💬</button></div>
                <div className="px-3 text-sm font-semibold">{p.likes} likes</div>
                <p className="px-3 text-sm"><b>{p.author_handle.replace("@", "")}</b> <Rich text={p.text} /></p>
                {(p.replies > 0 || comments[p.id]) && <button className="px-3 text-xs text-slate-500" onClick={() => loadComments(p)}>View all {p.replies} comments</button>}
                {comments[p.id]?.map((c) => <p key={c.id} className="px-3 text-sm"><b>{c.author_handle.replace("@", "")}</b> <Rich text={c.text} /> <span className="text-xs text-slate-400">{relTime(c.created_at, now)}</span></p>)}
                <div className="px-3 pt-1">
                  <CommentBox placeholder={u?.is_official ? `Comment on ${p.author_handle}'s post (complaint path: comment)` : "Add a comment…"} onSend={async (t) => { const r = await send({ source_type: "comment", text: t, parent_post_id: p.id, target_handle: p.author_handle }); setComments((c) => ({ ...c, [p.id]: [...(c[p.id] || []), r.post] })); setPosts((x) => x.map((y) => (y.id === p.id ? { ...y, replies: y.replies + 1 } : y))); }} />
                </div>
              </article>
            );
          })}
        </div>
      )}
      {tab === "create" && (
        <div className="space-y-3 p-4">
          <p className="rounded bg-fuchsia-50 p-2 text-xs text-fuchsia-900">Path 1 - <b>caption tag</b>: tag an official account in your caption (e.g. @AirSewa_Official @airindia).</p>
          <Composer users={all} platform="Instagram" placeholder="Write a caption… use @tags and #hashtags" button="Share" onSubmit={async (t, m) => { await send({ source_type: "post", text: t, media: m, location: cap.loc || undefined }); setTab("feed"); }} />
          <label className="block text-sm">📍 Location tag (airport)<select value={cap.loc} onChange={(e) => setCap({ ...cap, loc: e.target.value })} className="mt-1 block w-full rounded border border-slate-300 p-2"><option value="">None</option>{airports.map((a) => <option key={a.code} value={a.code}>{a.name} ({a.code})</option>)}</select></label>
        </div>
      )}
      {tab === "story" && (
        <div className="space-y-3 p-4">
          <p className="rounded bg-fuchsia-50 p-2 text-xs text-fuchsia-900">Path 3 - <b>story mention</b>: your story mentions an official account.</p>
          <label className="block text-sm">Mention account<select value={story.to} onChange={(e) => setStory({ ...story, to: e.target.value })} className="mt-1 block w-full rounded border border-slate-300 p-2">{officials.map((o) => <option key={o.handle} value={o.handle}>{o.handle}</option>)}</select></label>
          <textarea aria-label="Story text" rows={3} value={story.text} onChange={(e) => setStory({ ...story, text: e.target.value })} placeholder="Story text overlay (e.g. Stuck at the airport for 6 hours, no food!)" className="w-full rounded border border-slate-300 p-2" />
          <button disabled={!story.text.trim()} onClick={() => send({ source_type: "story_mention", text: `${story.text} ${story.to}`, target_handle: story.to }).then(() => { setStory({ ...story, text: "" }); setTab("feed"); })} className="rounded-lg bg-fuchsia-600 px-4 py-2 font-semibold text-white disabled:opacity-50">Share to story</button>
        </div>
      )}
      {tab === "dm" && (
        <div className="grid min-h-[320px] md:grid-cols-[200px_1fr]">
          <ul className="max-h-72 overflow-y-auto border-r">{officials.map((o) => <li key={o.handle}><button onClick={() => setDmWith(o.handle)} className={cn("flex w-full items-center gap-2 p-2 text-left text-sm hover:bg-slate-50", dmWith === o.handle && "bg-slate-100")}><Avatar u={o} size={28} />{o.handle.replace("@", "")}</button></li>)}</ul>
          <div className="flex flex-col"><div className="flex-1 space-y-2 overflow-y-auto p-3 text-sm" style={{ maxHeight: 280 }}>
            <p className="text-center text-xs text-fuchsia-800">Path 4 - <b>DM</b> to an official account.</p>
            {dmThread.map((m) => <div key={m.id} className={m.author_handle === me.handle ? "text-right" : ""}><span className={cn("inline-block max-w-[80%] rounded-2xl px-3 py-1.5", m.author_handle === me.handle ? "bg-fuchsia-600 text-white" : "bg-slate-100")}>{m.text}</span></div>)}</div>
            <div className="border-t p-2"><CommentBox placeholder={`Message ${dmWith}`} onSend={async (t) => { await send({ source_type: "dm", text: t, target_handle: dmWith }); loadDm(); }} /></div></div>
        </div>
      )}
      {tab === "act" && <div>{notifs.length === 0 && <p className="p-6 text-slate-500">No activity yet.</p>}{notifs.map((n) => <div key={n.id} className="border-b p-3 text-sm"><b>{n.from}</b> <span className="text-slate-400">{relTime(n.at, now)}</span><p>{n.text}</p></div>)}</div>}
    </div>
  );
}

function CommentBox({ placeholder, onSend }: { placeholder: string; onSend: (t: string) => Promise<any> }) {
  const [t, setT] = useState("");
  const [busy, setBusy] = useState(false);
  const { push } = useToast();
  return (
    <form onSubmit={async (e) => { e.preventDefault(); if (!t.trim()) return; setBusy(true); try { await onSend(t.trim()); setT(""); } catch (x: any) { push(x.message, "error"); } setBusy(false); }} className="flex gap-2">
      <input value={t} onChange={(e) => setT(e.target.value)} placeholder={placeholder} aria-label={placeholder} className="flex-1 rounded border border-slate-300 px-2 py-1.5 text-sm" />
      <button disabled={busy || !t.trim()} className="font-semibold text-fuchsia-600 disabled:opacity-40">Post</button>
    </form>
  );
}

// ---------------------------------------------------------------- shell with user switcher
export default function Simulator({ embedded, onPosted }: { embedded?: boolean; onPosted?: (r: any) => void }) {
  const [users, setUsers] = useState<U[]>([]);
  const [officials, setOfficials] = useState<U[]>([]);
  const [handle, setHandle] = useState("");
  const [app, setApp] = useState("X");
  const [replay, setReplay] = useState<any>(null);
  const { push } = useToast();
  useEffect(() => {
    api("/sim/users").then((r) => { setUsers(r.users); setOfficials(r.officials); setHandle(localStorage.getItem("sim_user") || r.users[0]?.handle); });
  }, []);
  useEffect(() => { if (handle) localStorage.setItem("sim_user", handle); }, [handle]);
  useEffect(() => {
    if (!replay?.running) return;
    const i = setInterval(() => api("/sim/replay").then((r) => { setReplay(r); if (!r.running) push("Replay finished", "success"); }), 1500);
    return () => clearInterval(i);
  }, [replay?.running, push]);
  const me = users.find((u) => u.handle === handle);
  if (!me) return <p className="p-6">Loading simulator…</p>;
  return (
    <div className={cn("overflow-hidden rounded-xl border-2 border-dashed border-purple-400 bg-white", embedded && "flex h-full flex-col")}>
      <div className="flex flex-wrap items-center justify-between gap-2 bg-purple-50 px-3 py-2">
        <div className="flex items-center gap-2"><Simulated text="Simulated - no real social platform connected" /></div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="saffron" disabled={replay?.running} onClick={() => api("/sim/replay?delay=3", { method: "POST" }).then((r) => { setReplay(r); push("Replay started: 10 scripted complaints, one every 3 s", "info"); })}>{replay?.running ? `Replaying ${replay.step}/${replay.total}…` : "▶ Replay demo script"}</Button>
          <label className="flex items-center gap-1 text-sm"><span>Log in as</span>
            <select aria-label="Log in as" value={handle} onChange={(e) => setHandle(e.target.value)} className="rounded border border-slate-400 bg-white px-2 py-1">{users.map((u) => <option key={u.handle} value={u.handle}>{u.name} ({u.handle}) · {u.lang}</option>)}</select></label>
        </div>
      </div>
      <Tabs value={app} onChange={setApp} className="bg-white px-2" tabs={[{ id: "X", label: "✕ X-style" }, { id: "Instagram", label: "◎ Instagram-style" }]} />
      <div className={cn(embedded && "min-h-0 flex-1 overflow-y-auto")}>
        {app === "X" ? <XApp key={"x" + handle} me={me} users={users} officials={officials} onPosted={onPosted} /> : <IGApp key={"i" + handle} me={me} users={users} officials={officials} onPosted={onPosted} />}
      </div>
    </div>
  );
}

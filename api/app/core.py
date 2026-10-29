"""Core infrastructure: settings, DB engine, demo clock, SSE event bus, security helpers."""
import asyncio
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'airsewa.db'}")

# --- settings (no secrets in repo: JWT secret comes from env, dev default is random per install) ---
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
DEMO_OTP = "123456"
SESSION_IDLE_MINUTES = int(os.getenv("SESSION_IDLE_MINUTES", "30"))
COOKIE_NAME = "airsewa_session"


def _secret() -> str:
    s = os.getenv("JWT_SECRET")
    if s:
        return s
    p = BASE_DIR / ".jwt_secret"
    if not p.exists():
        p.write_text(os.urandom(32).hex())
    return p.read_text().strip()


JWT_SECRET = _secret()


class Base(DeclarativeBase):
    pass


engine = create_engine(DB_PATH, connect_args={"check_same_thread": False}, pool_size=20, max_overflow=30) \
    if not DB_PATH.startswith("sqlite") else create_engine(DB_PATH, connect_args={"check_same_thread": False, "timeout": 30})


@event.listens_for(engine, "connect")
def _pragmas(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA foreign_keys=OFF")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- demo clock -------------------------------------------------------------------
class _Clock:
    """Application time = real UTC + admin-controlled offset. All SLA logic uses clock.now()."""

    def __init__(self):
        self.offset = timedelta(0)

    def now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None) + self.offset

    @staticmethod
    def real_now() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)


clock = _Clock()


def iso(dt):
    return dt.isoformat() + "Z" if dt else None


# --- SSE bus ------------------------------------------------------------------------
class Bus:
    def __init__(self):
        self.subs: set = set()
        self.lock = threading.Lock()

    def subscribe(self, topics: set):
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        entry = (q, asyncio.get_running_loop(), topics)
        with self.lock:
            self.subs.add(entry)
        return entry

    def unsubscribe(self, entry):
        with self.lock:
            self.subs.discard(entry)

    def publish(self, topic: str, data: dict):
        with self.lock:
            subs = list(self.subs)
        for q, loop, topics in subs:
            if topic in topics or any(topic.startswith(t + ":") for t in topics):
                try:
                    loop.call_soon_threadsafe(_put, q, (topic, data))
                except RuntimeError:
                    pass


def _put(q, item):
    try:
        q.put_nowait(item)
    except asyncio.QueueFull:
        pass


bus = Bus()


# --- security ------------------------------------------------------------------------
def hash_password(pw: str, rounds: int = 12) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt(rounds)).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except Exception:
        return False


def make_token(user_id: int, role: str) -> str:
    return jwt.encode({"sub": str(user_id), "role": role, "last": clock.real_now().timestamp()}, JWT_SECRET, algorithm="HS256")


def read_token(tok: str):
    try:
        return jwt.decode(tok, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


def mask_mobile(m):
    if not m:
        return m
    return m[:-6] + "XXXX" + m[-2:] if len(m) >= 8 else "XXXX"


def mask_email(e):
    if not e or "@" not in e:
        return e
    n, d = e.split("@", 1)
    return (n[:1] + "***" + n[-1:] if len(n) > 2 else n[:1] + "***") + "@" + d


def mask_handle(h):
    if not h:
        return h
    t = h.lstrip("@")
    return "@" + (t[:2] + "***" + t[-1:] if len(t) > 3 else t[:1] + "***")


def mask_name(n):
    if not n:
        return n
    parts = n.split()
    return " ".join(p[:1] + "*" * (len(p) - 1) if i else p for i, p in enumerate(parts))

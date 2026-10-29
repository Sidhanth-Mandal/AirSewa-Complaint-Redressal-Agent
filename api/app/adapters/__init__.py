"""External integrations behind clean interfaces (adapter pattern).
Only simulated implementations exist. Real ones (SMS gateway, FlightAware, LLM API, X/Instagram APIs) can be
registered in the `registry` at the bottom without touching business logic."""
import hashlib
import os
import re
from abc import ABC, abstractmethod
from typing import Callable

from ..core import clock, mask_email, mask_mobile
from ..reference import HI_PHRASES, HI_WORDS, HINGLISH_MARKERS


# --------------------------------------------------------------------------- Translator
class Translator(ABC):
    @abstractmethod
    def detect(self, text: str) -> str: ...

    @abstractmethod
    def translate(self, text: str, lang: str) -> str: ...


class MockDictionaryTranslator(Translator):
    """Detects en / hi (Devanagari) / hinglish (romanised Hindi) and translates via a small mock dictionary."""
    _phr = sorted(HI_PHRASES, key=len, reverse=True)

    def detect(self, text: str) -> str:
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return "en"
        dev = sum(1 for c in letters if "\u0900" <= c <= "\u097f")
        if dev / len(letters) > 0.3:
            return "hi"
        toks = set(re.findall(r"[a-z]+", text.lower()))
        if len(toks & HINGLISH_MARKERS) >= 2:
            return "hinglish"
        return "en"

    def translate(self, text: str, lang: str) -> str:
        if lang == "en":
            return text
        out = text.lower() if lang == "hinglish" else text
        for p in self._phr:
            if p in out:
                out = out.replace(p, f" {HI_PHRASES[p]} ")
        if lang == "hinglish":
            out = " ".join(HI_WORDS.get(t, t) if re.fullmatch(r"[a-z]+", t) else t for t in out.split())
        return re.sub(r"\s+", " ", out).strip()


# --------------------------------------------------------------------------- Notifier
class Notifier(ABC):
    @abstractmethod
    def send(self, db, channel: str, to: str, subject: str, body: str, ticket_id=None, user_id=None): ...


class SimulatedNotifier(Notifier):
    """Writes to the in-app 'Notification Log'. No real SMS/e-mail/WhatsApp is sent. Recipient is stored masked."""

    def send(self, db, channel, to, subject, body, ticket_id=None, user_id=None):
        from ..models import Notification
        masked = mask_email(to) if "@" in (to or "") else mask_mobile(to)
        n = Notification(ticket_id=ticket_id, user_id=user_id, channel=channel, to=masked, subject=subject, body=body, at=clock.now())
        db.add(n)
        return n


# --------------------------------------------------------------------------- Flight provider
class FlightProvider(ABC):
    @abstractmethod
    def status(self, flight_no: str) -> dict | None: ...


class MockFlightProvider(FlightProvider):
    AIRPORT_PAIRS = [("DEL", "BOM"), ("BOM", "BLR"), ("BLR", "HYD"), ("MAA", "DEL"), ("CCU", "DEL"), ("AMD", "BOM"), ("COK", "BLR"), ("GOI", "DEL"), ("LKO", "DEL"), ("HYD", "DEL")]

    def status(self, flight_no):
        fn = re.sub(r"[\s-]", "", flight_no.upper())
        m = re.fullmatch(r"([A-Z0-9]{2})(\d{1,4})", fn)
        if not m:
            return None
        h = int(hashlib.md5(fn.encode()).hexdigest(), 16)
        dep, arr = self.AIRPORT_PAIRS[h % len(self.AIRPORT_PAIRS)]
        now = clock.now()
        std_min = (h // 7) % (24 * 60)
        std = now.replace(hour=std_min // 60, minute=std_min % 60, second=0, microsecond=0)
        state = ["On time", "Delayed", "Delayed", "Boarding", "Cancelled", "In air", "Landed"][(h // 13) % 7]
        delay = [0, 95, 190, 0, 0, 20, 5][(h // 13) % 7]
        dur = 90 + (h // 17) % 120
        from datetime import timedelta
        eta = std + timedelta(minutes=delay + dur)
        return {"flight_no": fn, "airline_code": m.group(1), "from": dep, "to": arr, "scheduled_departure": std.isoformat() + "Z",
                "estimated_arrival": eta.isoformat() + "Z", "status": state, "delay_minutes": delay,
                "gate": f"{chr(65 + h % 6)}{1 + h % 40}", "terminal": f"T{1 + h % 3}", "simulated": True}


# --------------------------------------------------------------------------- LLM provider
class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, prompt: str) -> str | None: ...


class NoLLM(LLMProvider):
    def complete(self, system, prompt):
        return None  # callers fall back to deterministic rules


class OpenAICompatibleLLM(LLMProvider):
    """Optional: set LLM_PROVIDER=openai and LLM_API_KEY (and LLM_BASE_URL / LLM_MODEL). Never used by tests."""

    def complete(self, system, prompt):
        import httpx
        try:
            r = httpx.post(os.getenv("LLM_BASE_URL", "https://api.openai.com/v1") + "/chat/completions", timeout=8,
                           headers={"Authorization": "Bearer " + os.environ["LLM_API_KEY"]},
                           json={"model": os.getenv("LLM_MODEL", "gpt-4o-mini"), "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]})
            return r.json()["choices"][0]["message"]["content"]
        except Exception:
            return None


# --------------------------------------------------------------------------- CRM webhook (simulated)
class CRMWebhook(ABC):
    @abstractmethod
    def push(self, db, ticket) -> dict: ...


class SimulatedCRMWebhook(CRMWebhook):
    """Pretends to POST a 'call to action' into an airline CRM. The 'fake CRM' page lets a user update it back."""

    def push(self, db, ticket):
        from ..models import Config
        row = db.get(Config, "crm_inbox") or Config(key="crm_inbox", value=[])
        items = list(row.value or [])
        if not any(i["ticket_no"] == ticket.ticket_no for i in items):
            items.append({"ticket_no": ticket.ticket_no, "org": ticket.assigned_org.code if ticket.assigned_org else None,
                          "subcategory": ticket.subcategory, "summary": (ticket.description_en or ticket.description)[:140], "crm_status": "Open",
                          "pushed_at": clock.now().isoformat() + "Z", "simulated": True})
        row.value = items
        db.merge(row)
        return {"delivered": True, "simulated": True}


# --------------------------------------------------------------------------- Social channel adapters
class SocialChannelAdapter(ABC):
    platform: str

    @abstractmethod
    def start(self): ...

    @abstractmethod
    def stop(self): ...

    @abstractmethod
    def on_post(self, handler: Callable): ...


class _SimulatedAdapter(SocialChannelAdapter):
    """Fires the instant a post/comment/DM is created inside the simulator (no polling)."""

    def __init__(self):
        self.handlers: list[Callable] = []
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def on_post(self, handler):
        self.handlers.append(handler)

    def emit(self, social_post: dict) -> list:
        return [h(social_post) for h in self.handlers] if self.running else []


class SimulatedXAdapter(_SimulatedAdapter):
    platform = "X"


class SimulatedInstagramAdapter(_SimulatedAdapter):
    platform = "Instagram"


class Registry:
    translator: Translator = MockDictionaryTranslator()
    notifier: Notifier = SimulatedNotifier()
    flights: FlightProvider = MockFlightProvider()
    llm: LLMProvider = OpenAICompatibleLLM() if os.getenv("LLM_PROVIDER") == "openai" and os.getenv("LLM_API_KEY") else NoLLM()
    crm: CRMWebhook = SimulatedCRMWebhook()
    social = {"X": SimulatedXAdapter(), "Instagram": SimulatedInstagramAdapter()}


registry = Registry()

import threading
import time
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core import Base, SessionLocal, clock, engine
from .models import Config
from .routers import admin, analytics, auth, misc, social_api, tickets
from .modules import sla


def load_clock():
    with SessionLocal() as db:
        row = db.get(Config, "clock_offset_s")
        clock.offset = timedelta(seconds=float(row.value)) if row and row.value else timedelta(0)


def sweeper():
    """Background SLA sweeper (real-time every 10s). Fast-forwarding the demo clock also sweeps immediately."""
    while True:
        time.sleep(10)
        try:
            with SessionLocal() as db:
                sla.sweep(db)
        except Exception as e:  # pragma: no cover
            print("sweeper error", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    load_clock()
    social_api.register_adapters()
    threading.Thread(target=sweeper, daemon=True).start()
    yield


app = FastAPI(title="AirSewa 3.0 + PACR Prototype API", version="1.0",
              description="Prototype only. All social platforms, telephony, SMS/e-mail, flight data and CRMs are SIMULATED behind adapters.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
for r in (auth.router, tickets.router, admin.router, analytics.router, social_api.router, misc.router):
    app.include_router(r)


@app.get("/health")
def health():
    return {"ok": True, "now": clock.now().isoformat() + "Z", "simulated": True}

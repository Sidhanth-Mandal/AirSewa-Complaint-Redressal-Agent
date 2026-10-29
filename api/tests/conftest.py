import os
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="airsewa_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp) / 'test.db'}"
os.environ["UPLOAD_DIR"] = str(Path(_tmp) / "uploads")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app import seed  # noqa: E402


@pytest.fixture(scope="session")
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed.seed_minimal(db)
    with TestClient(app) as c:
        yield c


def login(client, email, pw="Demo@1234"):
    c = TestClient(app)
    r = c.post("/auth/login", json={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    return c


@pytest.fixture(scope="session")
def admin(client):
    return login(client, "admin@moca.demo")


@pytest.fixture(scope="session")
def agent(client):
    return login(client, "agent1@pacr.demo")


@pytest.fixture(scope="session")
def pax(client):
    return login(client, "passenger@demo.in")

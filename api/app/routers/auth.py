import re

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..adapters import registry
from ..core import DEMO_MODE, DEMO_OTP, clock, get_db, hash_password, iso, verify_password
from ..deps import current_user, optional_user, set_session
from ..models import User
from ..modules import grievance as G
from ..core import COOKIE_NAME

router = APIRouter(prefix="/auth", tags=["auth"])

USER_TYPES = ["Passenger", "AAI", "Airline", "Airport Operator", "BCAS", "DGCA", "Airport Security Group (ASG)", "Flying Training Organization (FTO)", "Others"]


def detect_identifier(v: str, country_code: str = "+91"):
    """FRS 3.1 #13-18: auto-detect mobile/email; 10-digit validation for India; international numbers allowed."""
    v = v.strip()
    if "@" in v:
        if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}", v):
            raise HTTPException(422, "Enter a valid e-mail address (e.g. name@example.com)")
        return "email", v.lower()
    digits = re.sub(r"[\s-]", "", v)
    if not digits.isdigit():
        raise HTTPException(422, "Enter a 10-digit mobile number or an e-mail address")
    if country_code == "+91":
        if len(digits) != 10:
            raise HTTPException(422, "Mobile number must be exactly 10 digits")
    elif not 6 <= len(digits) <= 14:
        raise HTTPException(422, "Invalid international mobile number")
    return "mobile", digits


def check_password_policy(pw: str):
    errs = []
    if len(pw) < 8:
        errs.append("at least 8 characters")
    if not re.search(r"[A-Z]", pw):
        errs.append("an uppercase letter")
    if not re.search(r"[a-z]", pw):
        errs.append("a lowercase letter")
    if not re.search(r"\d", pw):
        errs.append("a digit")
    if not re.search(r"[^A-Za-z0-9]", pw):
        errs.append("a special character")
    if errs:
        raise HTTPException(422, "Password must contain " + ", ".join(errs))


def find_user(db, kind, ident):
    col = User.email if kind == "email" else User.mobile
    return db.query(User).filter(col == ident).first()


def me_out(u: User):
    return {"id": u.id, "name": u.name, "role": u.role, "email": u.email, "mobile": u.mobile, "org": u.org.name if u.org else None,
            "org_code": u.org.code if u.org else None, "org_id": u.org_id, "level": u.level, "is_guest": u.is_guest, "lang": u.lang,
            "access_type": u.access_type, "designation": u.designation, "user_type": u.user_type}


class OtpReq(BaseModel):
    identifier: str
    country_code: str = "+91"
    purpose: str = "login"


@router.post("/otp/request")
def otp_request(b: OtpReq, db: Session = Depends(get_db)):
    kind, ident = detect_identifier(b.identifier, b.country_code)
    registry.notifier.send(db, "sms" if kind == "mobile" else "email", ident, "AirSewa OTP", f"Your AirSewa OTP is {DEMO_OTP if DEMO_MODE else '******'} (valid 10 min)")
    db.commit()
    # Demo mode: the OTP is returned so the UI can show it in a dev toast. A real SMS/e-mail gateway plugs in via Notifier.
    return {"sent": True, "kind": kind, "dev_otp": DEMO_OTP if DEMO_MODE else None, "simulated": True}


class OtpVerify(BaseModel):
    identifier: str
    country_code: str = "+91"
    otp: str
    mode: str = "login"  # login | guest
    name: str | None = None
    consent_save: bool = False


@router.post("/otp/verify")
def otp_verify(b: OtpVerify, resp: Response, db: Session = Depends(get_db)):
    kind, ident = detect_identifier(b.identifier, b.country_code)
    if b.otp != DEMO_OTP:
        raise HTTPException(401, "Invalid OTP")
    u = find_user(db, kind, ident)
    if u and u.role != "passenger":
        raise HTTPException(403, "Staff accounts must sign in with password")
    if u and u.status != "active":
        raise HTTPException(403, f"Account is {u.status}")
    if not u:
        # guest login with mobile / e-mail; consent decides whether the data is retained as an account (FRS 3.1 #7-9)
        u = User(name=b.name or "Guest", role="passenger", user_type="Passenger", is_guest=True, consent_save=b.consent_save, lang="en",
                 created_at=clock.now(), country_code=b.country_code, **({"email": ident} if kind == "email" else {"mobile": ident}))
        db.add(u)
        db.flush()
    elif b.consent_save and u.is_guest:
        u.is_guest, u.consent_save = False, True
    u.last_login = clock.now()
    G.audit(db, u.name, "login.otp", str(u.id), "guest" if u.is_guest else "registered")
    db.commit()
    set_session(resp, u)
    return me_out(u)


class Register(BaseModel):
    user_type: str = "Passenger"
    name: str = Field(min_length=2, max_length=80)
    identifier: str
    country_code: str = "+91"
    password: str
    otp: str
    email: str | None = None


@router.post("/register")
def register(b: Register, resp: Response, db: Session = Depends(get_db)):
    if b.user_type not in USER_TYPES:
        raise HTTPException(422, "Select a valid user type")
    kind, ident = detect_identifier(b.identifier, b.country_code)
    check_password_policy(b.password)
    if b.otp != DEMO_OTP:
        raise HTTPException(401, "Invalid OTP")
    ex = find_user(db, kind, ident)
    if ex and not ex.is_guest:
        raise HTTPException(409, "An account already exists for this mobile/e-mail. Please login.")
    u = ex or User(role="passenger", created_at=clock.now())
    u.name, u.user_type, u.password_hash, u.is_guest, u.consent_save, u.country_code = b.name, b.user_type, hash_password(b.password), False, True, b.country_code
    if kind == "email":
        u.email = ident
    else:
        u.mobile = ident
    if b.email and kind == "mobile":
        u.email = b.email.lower()
    db.add(u)
    db.flush()
    registry.notifier.send(db, "sms" if kind == "mobile" else "email", ident, "Welcome to AirSewa", f"Hello {b.name}, your AirSewa account is registered.", user_id=u.id)
    G.audit(db, b.name, "register", str(u.id))
    db.commit()
    set_session(resp, u)
    return me_out(u)


class Login(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(b: Login, resp: Response, db: Session = Depends(get_db)):
    kind, ident = detect_identifier(b.username) if ("@" in b.username or b.username.strip().isdigit()) else (None, None)
    if not kind:
        raise HTTPException(422, "Enter your registered mobile number or e-mail")
    u = find_user(db, kind, ident)
    if not u or not u.password_hash:
        raise HTTPException(401, "Invalid credentials")
    if u.status != "active":
        raise HTTPException(403, f"Account {u.status}. Contact your Nodal Officer / administrator.")
    if u.failed_logins >= 5:
        raise HTTPException(423, "Account temporarily locked after repeated failures. Use 'Forgot password' with OTP.")
    if not verify_password(b.password, u.password_hash):
        u.failed_logins += 1
        db.commit()
        raise HTTPException(401, "Invalid credentials")
    u.failed_logins = 0
    u.last_login = clock.now()
    G.audit(db, u.name, "login.password", str(u.id), u.role)
    db.commit()
    set_session(resp, u)
    return me_out(u)


class Reset(BaseModel):
    identifier: str
    otp: str
    new_password: str


@router.post("/password/reset")
def reset(b: Reset, db: Session = Depends(get_db)):
    kind, ident = detect_identifier(b.identifier)
    if b.otp != DEMO_OTP:
        raise HTTPException(401, "Invalid OTP")
    check_password_policy(b.new_password)
    u = find_user(db, kind, ident)
    if not u:
        raise HTTPException(404, "No account for that mobile/e-mail")
    u.password_hash, u.failed_logins = hash_password(b.new_password), 0
    registry.notifier.send(db, "email" if u.email else "sms", u.email or u.mobile, "Password changed", "Your AirSewa password was changed.", user_id=u.id)
    G.audit(db, u.name, "password.reset", str(u.id))
    db.commit()
    return {"ok": True}


@router.post("/logout")
def logout(resp: Response):
    resp.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
def me(u: User | None = Depends(optional_user)):
    return me_out(u) if u else None


@router.post("/lang")
def set_lang(lang: str, u: User = Depends(current_user), db: Session = Depends(get_db)):
    u.lang = lang if lang in ("en", "hi") else "en"
    db.commit()
    return {"ok": True}

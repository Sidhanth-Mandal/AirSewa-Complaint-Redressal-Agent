from fastapi import Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .core import COOKIE_NAME, SESSION_IDLE_MINUTES, clock, get_db, make_token, read_token
from .models import User


def set_session(resp: Response, user: User):
    resp.set_cookie(COOKIE_NAME, make_token(user.id, user.role), httponly=True, samesite="lax", max_age=SESSION_IDLE_MINUTES * 60, path="/")


def optional_user(request: Request, response: Response, db: Session = Depends(get_db)) -> User | None:
    tok = request.cookies.get(COOKIE_NAME)
    if not tok:
        return None
    data = read_token(tok)
    if not data:
        return None
    if clock.real_now().timestamp() - data.get("last", 0) > SESSION_IDLE_MINUTES * 60:
        return None  # idle session expiry
    u = db.get(User, int(data["sub"]))
    if not u or u.status != "active":
        return None
    set_session(response, u)  # sliding expiry
    return u


def current_user(u: User | None = Depends(optional_user)) -> User:
    if not u:
        raise HTTPException(401, "Not authenticated or session expired")
    return u


def require(*roles):
    def dep(u: User = Depends(current_user)) -> User:
        if u.role not in roles:
            raise HTTPException(403, f"Role '{u.role}' is not permitted for this action")
        return u
    return dep

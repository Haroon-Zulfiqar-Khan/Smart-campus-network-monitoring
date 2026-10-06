from fastapi import Request
import hashlib
import secrets
from datetime import timedelta
import jwt
from fastapi import Depends
from .errors import DomainError as HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from .config import settings
from .db import get_db
from .models import User, LoginSession, now

passwords = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
DUMMY_HASH = passwords.hash("dummy-password-for-timing-only")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def issue(db, user):
    refresh = secrets.token_urlsafe(48)
    session = LoginSession(
        user_id=user.id,
        refresh_hash=digest(refresh),
        expires_at=now() + timedelta(days=settings.refresh_days),
    )
    db.add(session)
    db.flush()
    return tokens(user, session, refresh)


def tokens(user, session, refresh):
    access = jwt.encode(
        {
            "sub": user.id,
            "sid": session.id,
            "aud": "campus-api",
            "exp": now() + timedelta(minutes=settings.access_minutes),
            "iat": now(),
        },
        settings.secret_key,
        algorithm="HS256",
    )
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.access_minutes * 60,
    }


def decode(token, audience="campus-api"):
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
            audience=audience,
            options={"require": ["exp", "sub", "aud"]},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})


def current_user(
    request: Request,
    auth: HTTPAuthorizationCredentials | None = Depends(bearer),
    db=Depends(get_db),
):
    if not auth:
        raise HTTPException(401, "Authentication required")
    data = decode(auth.credentials)
    session = db.get(LoginSession, data.get("sid")) if data.get("sid") else None
    user = db.get(User, data["sub"])
    if (
        not session
        or session.revoked
        or session.expires_at < now()
        or session.user_id != data["sub"]
        or not user
        or not user.is_active
    ):
        raise HTTPException(401, "Session no longer active")
    from .models.extensions import allowed

    path = request.url.path
    if request.method == "GET" and user.role in ("support", "manager"):
        if path.startswith("/complaints") and not (
            allowed(db, user, "complaints") or allowed(db, user, "reports")
        ):
            raise HTTPException(
                403, "Your account does not have permission to view campus complaints."
            )
        if path.startswith("/tests") and not allowed(
            db, user, "tests" if user.role == "support" else "reports"
        ):
            raise HTTPException(
                403, "Your account does not have permission to view campus test results."
            )
        if path.startswith("/maintenance") and not (
            allowed(db, user, "maintenance") or allowed(db, user, "reports")
        ):
            raise HTTPException(
                403, "Your account does not have permission to view maintenance records."
            )
    capability = None
    if path.startswith("/complaints") and request.method != "GET":
        capability = "complaints" if user.role in ("support", "manager", "admin") else None
    elif path.startswith("/maintenance") and request.method != "GET":
        capability = "maintenance"
    elif path.startswith(("/analytics", "/reports")):
        capability = "reports"
    elif path.startswith("/tests") and request.query_params.get("mine") == "false":
        capability = (
            "tests" if user.role == "support" else "reports" if user.role == "manager" else None
        )
    if capability and not allowed(db, user, capability):
        raise HTTPException(403, "Your account does not have permission to perform this action.")
    return user


def roles(*allowed):
    def check(user=Depends(current_user)):
        if user.role not in allowed:
            raise HTTPException(403, "Permission denied")
        return user

    return check


operator = roles("support", "manager", "admin")
admin = roles("admin")

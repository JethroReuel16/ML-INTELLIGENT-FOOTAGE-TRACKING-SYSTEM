
import hashlib
import logging
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, AuthSession
from app.security import hash_password, verify_password


router = APIRouter(prefix="/api/auth", tags=["Authentication"])

logger = logging.getLogger(__name__)

COOKIE_NAME = settings.cookie_name
SESSION_DURATION_DAYS = settings.session_days


# ---------------------------------------------------------
# LOGIN THROTTLING (in-process; per client IP + email)
# ---------------------------------------------------------

_attempts = defaultdict(deque)
_attempts_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    # Behind a reverse proxy run uvicorn with --proxy-headers so this is the
    # real client address.
    return request.client.host if request.client else "unknown"


def _throttle_key(request: Request, email: str) -> str:
    return f"{_client_ip(request)}|{email}"


def check_login_allowed(key: str) -> None:
    now = time.monotonic()
    window = settings.login_window_seconds

    with _attempts_lock:
        bucket = _attempts[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()

        if len(bucket) >= settings.login_max_attempts:
            retry_after = int(window - (now - bucket[0])) + 1
            raise HTTPException(
                status_code=429,
                detail="Too many failed sign-in attempts. Please wait and try again.",
                headers={"Retry-After": str(retry_after)},
            )


def record_failed_login(key: str) -> None:
    with _attempts_lock:
        _attempts[key].append(time.monotonic())


def clear_failed_logins(key: str) -> None:
    with _attempts_lock:
        _attempts.pop(key, None)


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_session_cookie(response: Response, token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        max_age=SESSION_DURATION_DAYS * 24 * 60 * 60,
        path="/",
    )


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    token_hash = hash_session_token(token)

    auth_session = (
        db.query(AuthSession)
        .filter(
            AuthSession.token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if not auth_session:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid."
        )

    user = (
        db.query(User)
        .filter(
            User.id == auth_session.user_id,
            User.is_active.is_(True),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User account is unavailable."
        )

    return user


@router.post("/register", status_code=201)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    email = normalize_email(data.email)

    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid email address."
        )

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists."
        )

    user = User(
        full_name=data.full_name.strip(),
        email=email,
        hashed_password=hash_password(data.password),
        is_active=True,
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists."
        ) from error

    return {
        "message": "Account created successfully.",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
        },
    }


@router.post("/login")
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    email = normalize_email(data.email)
    throttle_key = _throttle_key(request, email)

    check_login_allowed(throttle_key)

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user or not verify_password(
        data.password,
        user.hashed_password
    ):
        record_failed_login(throttle_key)
        logger.info("Failed sign-in attempt from %s", _client_ip(request))
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="This account is inactive."
        )

    clear_failed_logins(throttle_key)

    token = generate_session_token()
    now = datetime.now(timezone.utc)

    # Housekeeping: drop this user's expired or revoked sessions.
    db.query(AuthSession).filter(
        AuthSession.user_id == user.id,
        (AuthSession.expires_at < now) | (AuthSession.revoked_at.isnot(None)),
    ).delete(synchronize_session=False)

    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=now + timedelta(days=SESSION_DURATION_DAYS),
    )

    db.add(auth_session)
    db.commit()

    set_session_cookie(response, token)

    return {
        "message": "Login successful.",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
        },
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(COOKIE_NAME)

    if token:
        auth_session = (
            db.query(AuthSession)
            .filter(
                AuthSession.token_hash == hash_session_token(token),
                AuthSession.revoked_at.is_(None),
            )
            .first()
        )

        if auth_session:
            auth_session.revoked_at = datetime.now(timezone.utc)
            db.commit()

    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )

    return {"message": "Logout successful."}


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "is_active": current_user.is_active,
    }

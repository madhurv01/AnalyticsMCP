import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User

ALGO = "HS256"


def issue_session(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.session_ttl_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGO)


def _decode(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGO])
        return uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid session") from exc


def _token_from_request(request: Request) -> str:
    token = request.cookies.get(settings.session_cookie)
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    return token


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = _decode(_token_from_request(request))
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return user


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        settings.session_cookie,
        token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.is_prod,
        samesite="lax",
        path="/",
    )

from datetime import datetime, timezone

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User
from app.ratelimit import limit
from app.schemas import UserOut
from app.security import current_user, issue_session, set_session_cookie

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google/login")
async def google_login(request: Request):
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/google/callback", dependencies=[Depends(limit("auth"))])
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as exc:
        raise HTTPException(400, f"oauth error: {exc.error}") from exc

    claims = token.get("userinfo") or {}
    sub, email = claims.get("sub"), claims.get("email")
    if not sub or not email:
        raise HTTPException(400, "google did not return an identity")

    user = db.scalar(select(User).where(User.google_sub == sub))
    if user is None:
        user = User(google_sub=sub, email=email)
        db.add(user)
    user.email = email
    user.name = claims.get("name")
    user.picture_url = claims.get("picture")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    resp = RedirectResponse(url=f"{settings.web_origin}/dashboard")
    set_session_cookie(resp, issue_session(user.id))
    return resp


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(settings.session_cookie, path="/")
    return resp

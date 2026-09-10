"""Symmetric encryption for stored third-party credentials (MCP auth tokens).

Key is derived from SECRET_KEY, so rotating SECRET_KEY invalidates stored tokens
(the user just re-enters them).
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest()))


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet.decrypt(token.encode()).decode()
    except InvalidToken:
        return ""

"""Data-source hub — register external MCP servers and import tables from them."""
import hashlib
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import mcpclient
from app.config import settings
from app.crypto import decrypt, encrypt
from app.db import get_db
from app.models import Dataset, McpConnection, User
from app.ratelimit import limit
from app.schemas import CatalogOut, ConnectionCreate, ConnectionOut, DatasetOut, ImportRequest
from app.security import current_user
from app.storage import put_bytes

router = APIRouter(prefix="/api/connections", tags=["data sources"])


def _owned(db: Session, user: User, conn_id: uuid.UUID) -> McpConnection:
    conn = db.get(McpConnection, conn_id)
    if conn is None or conn.user_id != user.id:
        raise HTTPException(404, "connection not found")
    return conn


@router.post("", response_model=CatalogOut, dependencies=[Depends(limit("upload"))])
async def create_connection(
    body: ConnectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if not re.match(r"^https?://", body.url):
        raise HTTPException(422, "url must start with http:// or https://")
    try:
        catalog = await mcpclient.probe(body.url, body.auth_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"could not reach the MCP server: {exc}") from exc

    conn = McpConnection(
        user_id=user.id,
        name=body.name.strip() or catalog["server_name"],
        url=body.url.rstrip("/"),
        auth_token_enc=encrypt(body.auth_token) if body.auth_token else None,
        server_name=catalog["server_name"],
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return CatalogOut(connection=ConnectionOut.model_validate(conn),
                      tools=catalog["tools"], resources=catalog["resources"])


@router.get("", response_model=list[ConnectionOut])
def list_connections(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.scalars(
        select(McpConnection).where(McpConnection.user_id == user.id)
        .order_by(McpConnection.created_at.desc())
    ).all()


@router.get("/{conn_id}/catalog", response_model=CatalogOut)
async def get_catalog(conn_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    conn = _owned(db, user, conn_id)
    token = decrypt(conn.auth_token_enc) if conn.auth_token_enc else None
    try:
        catalog = await mcpclient.probe(conn.url, token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"could not reach the MCP server: {exc}") from exc
    return CatalogOut(connection=ConnectionOut.model_validate(conn),
                      tools=catalog["tools"], resources=catalog["resources"])


@router.delete("/{conn_id}")
def delete_connection(conn_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.delete(_owned(db, user, conn_id))
    db.commit()
    return {"ok": True}


@router.post("/{conn_id}/import", response_model=DatasetOut, dependencies=[Depends(limit("upload"))])
async def import_dataset(
    conn_id: uuid.UUID,
    body: ImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    conn = _owned(db, user, conn_id)
    token = decrypt(conn.auth_token_enc) if conn.auth_token_enc else None

    try:
        if body.mode == "resource":
            if not body.resource_uri:
                raise HTTPException(422, "resource_uri is required")
            text = await mcpclient.fetch_resource(conn.url, token, body.resource_uri)
            label = body.resource_uri
        else:
            if not body.tool_name:
                raise HTTPException(422, "tool_name is required")
            text = await mcpclient.fetch_tool(conn.url, token, body.tool_name, body.arguments)
            label = body.tool_name
        df = mcpclient.to_dataframe(text)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"import failed: {exc}") from exc

    if df.empty:
        raise HTTPException(422, "the data source returned an empty table")

    raw = mcpclient.to_csv_bytes(df)
    if len(raw) > settings.upload_max_bytes:
        raise HTTPException(413, "imported table exceeds the size limit")

    slug = re.sub(r"[^a-z0-9]+", "-", f"{conn.name}-{label}".lower()).strip("-")[:60]
    filename = body.filename or f"{slug or 'import'}.csv"
    ds_id = uuid.uuid4()
    key = f"users/{user.id}/datasets/{ds_id}.csv"
    put_bytes(key, raw, "text/csv")

    ds = Dataset(
        id=ds_id, user_id=user.id, filename=filename, storage_key=key,
        size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), status="uploaded",
    )
    db.add(ds)
    conn.last_used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ds)
    return ds

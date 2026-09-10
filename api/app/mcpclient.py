"""InsightForge as an MCP *client* — connect to external MCP servers as data sources.

Given a server URL (+ optional bearer token) we can:
  * probe it — list its tools and resources,
  * call a tool or read a resource,
  * turn the returned text (JSON rows, {columns,rows}, or CSV) into a DataFrame.

Everything here is async (the MCP SDK client is async); routers await it directly.
"""
from __future__ import annotations

import io
import json

import pandas as pd
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

CONNECT_TIMEOUT = 20


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _text(content_list) -> str:
    parts = []
    for part in content_list or []:
        txt = getattr(part, "text", None)
        if txt is not None:
            parts.append(txt)
    return "\n".join(parts).strip()


async def probe(url: str, token: str | None) -> dict:
    async with streamablehttp_client(url, headers=_headers(token), timeout=CONNECT_TIMEOUT) as (
        read,
        write,
        _,
    ):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            tools = (await session.list_tools()).tools
            try:
                resources = (await session.list_resources()).resources
            except Exception:  # noqa: BLE001 — server may not support resources
                resources = []
            return {
                "server_name": getattr(init.serverInfo, "name", "unknown"),
                "tools": [
                    {
                        "name": t.name,
                        "description": (t.description or "")[:400],
                        "input_schema": t.inputSchema,
                    }
                    for t in tools
                ],
                "resources": [
                    {"uri": str(r.uri), "name": r.name or "", "mime_type": r.mimeType or ""}
                    for r in resources
                ],
            }


async def fetch_tool(url: str, token: str | None, name: str, arguments: dict | None) -> str:
    async with streamablehttp_client(url, headers=_headers(token), timeout=CONNECT_TIMEOUT) as (
        read,
        write,
        _,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments or {})
            if result.isError:
                raise ValueError(f"remote tool error: {_text(result.content)[:300]}")
            return _text(result.content)


async def fetch_resource(url: str, token: str | None, uri: str) -> str:
    async with streamablehttp_client(url, headers=_headers(token), timeout=CONNECT_TIMEOUT) as (
        read,
        write,
        _,
    ):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.read_resource(uri)
            return _text(result.contents)


def to_dataframe(text: str) -> pd.DataFrame:
    text = (text or "").strip()
    if not text:
        raise ValueError("the data source returned nothing")

    # 1) JSON
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None

    if payload is not None:
        for candidate in (payload, payload.get("data") if isinstance(payload, dict) else None,
                          payload.get("rows") if isinstance(payload, dict) else None,
                          payload.get("records") if isinstance(payload, dict) else None,
                          payload.get("result") if isinstance(payload, dict) else None):
            if isinstance(candidate, list) and candidate:
                if isinstance(candidate[0], dict):
                    return pd.DataFrame(candidate)
                if isinstance(candidate[0], (list, tuple)):
                    cols = payload.get("columns") if isinstance(payload, dict) else None
                    return pd.DataFrame(candidate, columns=cols)
        if isinstance(payload, dict) and isinstance(payload.get("columns"), list) \
                and isinstance(payload.get("rows"), list):
            return pd.DataFrame(payload["rows"], columns=payload["columns"])

    # 2) CSV / TSV
    for sep in (",", "\t", ";"):
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep, engine="python")
            if df.shape[1] > 1 or len(df) > 1:
                return df
        except Exception:  # noqa: BLE001
            continue

    raise ValueError("could not parse the data source response as a table "
                     "(expected JSON rows, {columns, rows}, or CSV)")


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

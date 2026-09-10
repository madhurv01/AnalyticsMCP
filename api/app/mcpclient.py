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


def _unwrap(exc: BaseException) -> str:
    """Flatten anyio TaskGroup ExceptionGroups into a readable one-liner."""
    seen: list[str] = []

    def walk(e: BaseException) -> None:
        inner = getattr(e, "exceptions", None)
        if inner:
            for sub in inner:
                walk(sub)
        else:
            msg = str(e).strip() or e.__class__.__name__
            if msg not in seen:
                seen.append(msg)

    walk(exc)
    return "; ".join(seen) or repr(exc)


class SourceError(RuntimeError):
    pass


def _text(content_list) -> str:
    parts = []
    for part in content_list or []:
        txt = getattr(part, "text", None)
        if txt is not None:
            parts.append(txt)
    return "\n".join(parts).strip()


async def probe(url: str, token: str | None) -> dict:
    try:
        async with streamablehttp_client(
            url, headers=_headers(token), timeout=CONNECT_TIMEOUT
        ) as (read, write, _):
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
    except BaseException as exc:  # noqa: BLE001 — includes anyio ExceptionGroup
        raise SourceError(_unwrap(exc)) from None


async def fetch_tool(url: str, token: str | None, name: str, arguments: dict | None) -> str:
    try:
        async with streamablehttp_client(
            url, headers=_headers(token), timeout=CONNECT_TIMEOUT
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments or {})
                if result.isError:
                    raise SourceError(f"remote tool error: {_text(result.content)[:400]}")
                return _text(result.content)
    except SourceError:
        raise
    except BaseException as exc:  # noqa: BLE001
        raise SourceError(_unwrap(exc)) from None


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


# keys real-world MCP servers wrap their row arrays in (GitHub uses "items", many
# REST-shaped tools use "data" / "results" / "records" / "hits" / "value" (OData)).
_ROW_KEYS = ("data", "rows", "records", "result", "results", "items", "hits",
             "value", "entries", "content")


def _find_rows(payload):
    """Depth-first search for the first list-of-dicts (or list-of-lists) in a JSON blob."""
    if isinstance(payload, list):
        return payload if payload and isinstance(payload[0], (dict, list, tuple)) else None
    if isinstance(payload, dict):
        for key in _ROW_KEYS:
            if key in payload:
                found = _find_rows(payload[key])
                if found is not None:
                    return found
        for value in payload.values():  # last resort: any nested list-of-dicts
            if isinstance(value, (dict, list)):
                found = _find_rows(value)
                if found is not None:
                    return found
    return None


def to_dataframe(text: str) -> pd.DataFrame:
    text = (text or "").strip()
    if not text:
        raise ValueError("the data source returned nothing")

    # strip a ```json fence if the server wrapped the payload in markdown
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0].strip()

    # 1) JSON
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None

    if payload is not None:
        if isinstance(payload, dict) and isinstance(payload.get("columns"), list) \
                and isinstance(payload.get("rows"), list):
            return pd.DataFrame(payload["rows"], columns=payload["columns"])
        rows = _find_rows(payload)
        if isinstance(rows, list) and rows:
            if isinstance(rows[0], dict):
                return pd.json_normalize(rows, sep=".")
            if isinstance(rows[0], (list, tuple)):
                cols = payload.get("columns") if isinstance(payload, dict) else None
                return pd.DataFrame(rows, columns=cols)
        if isinstance(payload, dict) and payload and all(
                not isinstance(v, (dict, list)) for v in payload.values()):
            return pd.DataFrame([payload])  # a single flat object → one row

    # 2) GitHub-flavoured markdown table
    md = _markdown_table(text)
    if md is not None:
        return md

    # 3) CSV / TSV
    for sep in (",", "\t", ";"):
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep, engine="python")
            if df.shape[1] > 1 and len(df) >= 1:
                return df
        except Exception:  # noqa: BLE001
            continue

    raise ValueError(
        "could not parse the data source response as a table. Expected JSON rows, "
        "{columns, rows}, a markdown table, or CSV — got "
        f"{text[:120]!r}…"
    )


def _markdown_table(text: str):
    import re

    lines = [ln for ln in text.splitlines() if ln.strip()]
    for i in range(len(lines) - 1):
        if "|" in lines[i] and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1]) and "-" in lines[i + 1]:
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows = []
            for ln in lines[i + 2:]:
                if "|" not in ln:
                    break
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if len(cells) == len(header):
                    rows.append(cells)
            if rows:
                return pd.DataFrame(rows, columns=header)
    return None


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

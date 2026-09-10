import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    name: str | None
    picture_url: str | None
    created_at: datetime


class DatasetOut(ORMModel):
    id: uuid.UUID
    filename: str
    size_bytes: int
    row_count: int | None
    col_count: int | None
    status: str
    created_at: datetime


class JobOut(ORMModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    mode: str
    status: str
    step: str | None
    progress: int
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class JobDetailOut(JobOut):
    profile_json: dict | None
    insights_json: dict | None


class ReportOut(ORMModel):
    id: uuid.UUID
    job_id: uuid.UUID
    size_bytes: int
    sheet_names: list
    created_at: datetime


class AnalyzeRequest(BaseModel):
    force_async: bool = False


class ConnectionCreate(BaseModel):
    name: str
    url: str
    auth_token: str | None = None


class ConnectionOut(ORMModel):
    id: uuid.UUID
    name: str
    url: str
    server_name: str | None
    created_at: datetime
    last_used_at: datetime | None


class CatalogOut(BaseModel):
    connection: ConnectionOut
    tools: list
    resources: list


class ImportRequest(BaseModel):
    mode: str = "tool"  # "tool" | "resource"
    tool_name: str | None = None
    arguments: dict | None = None
    resource_uri: str | None = None
    filename: str | None = None


class QueryRequest(BaseModel):
    expr: str


class Page(BaseModel):
    items: list
    total: int
    limit: int
    offset: int

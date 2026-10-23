from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["low", "medium", "high", "critical"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(ORM):
    id: int
    username: str
    role: str
    is_active: bool


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)
    role: Literal["viewer", "analyst", "admin"] = "analyst"


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SearchIn(BaseModel):
    query: str = Field(default="", max_length=2000)
    time_from: str = Field(default="now-24h", max_length=40, pattern=r"^(now(-\d+[smhdw])?|\d{4}-\d{2}-\d{2}T[\d:.+Z-]+)$")
    time_to: str = Field(default="now", max_length=40, pattern=r"^(now(-\d+[smhdw])?|\d{4}-\d{2}-\d{2}T[\d:.+Z-]+)$")
    size: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0, le=10000)


class AlertOut(ORM):
    id: int
    rule_id: str
    title: str
    description: str
    severity: str
    status: str
    mitre_tactic: str | None
    mitre_technique: str | None
    group_values: dict
    entities: list[str]
    event_count: int
    sample_events: list
    first_seen: datetime
    last_seen: datetime
    incident_id: int | None


class AlertPatch(BaseModel):
    status: Literal["open", "investigating", "closed", "false_positive"]


class IncidentOut(ORM):
    id: int
    title: str
    severity: str
    risk_score: int
    status: str
    tactics: list[str]
    entities: list[str]
    first_seen: datetime | None
    last_seen: datetime | None


class WatchlistIn(BaseModel):
    value: str = Field(min_length=1, max_length=1024)
    source: str = Field(default="manual", max_length=128)
    note: str = Field(default="", max_length=2000)


class WatchlistOut(ORM):
    id: int
    ioc_type: str
    value: str
    source: str
    note: str
    active: bool


class CaseCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=10000)
    severity: Severity = "medium"
    incident_id: int | None = None
    alert_ids: list[int] = []


class CasePatch(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    status: Literal["open", "in_progress", "closed"] | None = None
    severity: Severity | None = None


class EvidenceIn(BaseModel):
    kind: Literal["note", "log_event", "ioc"]
    title: str = Field(min_length=1, max_length=255)
    content: dict | None = None
    text: str | None = Field(default=None, max_length=20000)


class EvidenceOut(ORM):
    id: int
    kind: str
    title: str
    content: dict | None
    filename: str | None
    sha256: str
    size_bytes: int
    added_at: datetime


class FindingIn(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=10000)
    severity: Severity = "medium"
    confidence: Literal["low", "medium", "high"] = "medium"
    mitre_technique: str | None = Field(default=None, pattern=r"^T\d{4}(\.\d{3})?$")


class FindingOut(ORM):
    id: int
    title: str
    description: str
    severity: str
    confidence: str
    mitre_technique: str | None
    created_at: datetime


class CaseOut(ORM):
    id: int
    title: str
    description: str
    status: str
    severity: str
    incident_id: int | None
    created_at: datetime
    updated_at: datetime
    owner: UserOut | None = None
    alerts: list[AlertOut] = []
    evidence: list[EvidenceOut] = []
    findings: list[FindingOut] = []


class CaseListItem(ORM):
    id: int
    title: str
    status: str
    severity: str
    created_at: datetime
    updated_at: datetime

"""Relational data: users, alerts, incidents, cases, evidence, findings, IOC cache, watchlist, audit.

Raw log events do NOT live here -- they live in Elasticsearch. Postgres holds everything
that needs relations, transactions and an audit trail."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Table, Column, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.types import UTCDateTime, utcnow

ROLES = ("viewer", "analyst", "admin")
SEVERITIES = ("low", "medium", "high", "critical")
ALERT_STATUSES = ("open", "investigating", "closed", "false_positive")
CASE_STATUSES = ("open", "in_progress", "closed")

case_alerts = Table(
    "case_alerts",
    Base.metadata,
    Column("case_id", ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
    Column("alert_id", ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="analyst")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Incident(Base):
    """A group of correlated alerts that probably belong to one attack."""

    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="open")
    tactics: Mapped[list] = mapped_column(JSON, default=list)  # ordered kill-chain
    entities: Mapped[list] = mapped_column(JSON, default=list)
    first_seen: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    alerts: Mapped[list["Alert"]] = relationship(back_populates="incident")


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    mitre_tactic: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mitre_technique: Mapped[str | None] = mapped_column(String(32), nullable=True)
    group_values: Mapped[dict] = mapped_column(JSON, default=dict)
    entities: Mapped[list] = mapped_column(JSON, default=list)  # ["ip:1.2.3.4", "host:web01"]
    event_count: Mapped[int] = mapped_column(Integer, default=0)
    sample_events: Mapped[list] = mapped_column(JSON, default=list)
    dedupe_key: Mapped[str] = mapped_column(String(512), index=True)
    first_seen: Mapped[datetime] = mapped_column(UTCDateTime)
    last_seen: Mapped[datetime] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"), nullable=True, index=True)

    incident: Mapped[Incident | None] = relationship(back_populates="alerts")


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="open")
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    owner: Mapped[User | None] = relationship()
    alerts: Mapped[list[Alert]] = relationship(secondary=case_alerts)
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    findings: Mapped[list["Finding"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class Evidence(Base):
    """Append-only: evidence is never edited, only added. SHA-256 proves it was not altered."""

    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # note | log_event | ioc | file
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    added_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    case: Mapped[Case] = relationship(back_populates="evidence")


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    confidence: Mapped[str] = mapped_column(String(16), default="medium")
    mitre_technique: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    case: Mapped[Case] = relationship(back_populates="findings")


class IocCache(Base):
    __tablename__ = "ioc_cache"
    __table_args__ = (UniqueConstraint("ioc_type", "value", name="uq_ioc"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    ioc_type: Mapped[str] = mapped_column(String(16))
    value: Mapped[str] = mapped_column(String(1024), index=True)
    result: Mapped[dict] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class WatchlistEntry(Base):
    """Analyst-curated bad indicators. The detection engine hunts for these in the event stream."""

    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("ioc_type", "value", name="uq_watch"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    ioc_type: Mapped[str] = mapped_column(String(16))  # ip | domain | sha256 ...
    value: Mapped[str] = mapped_column(String(1024))
    source: Mapped[str] = mapped_column(String(128), default="manual")
    note: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class AuditLog(Base):
    """Who did what, when. Doubles as the chain-of-custody trail for a case."""

    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
    username: Mapped[str] = mapped_column(String(64), default="system")
    action: Mapped[str] = mapped_column(String(64))
    object_type: Mapped[str] = mapped_column(String(32))
    object_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)

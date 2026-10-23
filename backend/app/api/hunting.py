"""Hunting endpoints: event search, indicator pivot, IOC lookup, watchlist, dashboard stats."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.db.models import Alert, Incident, User, WatchlistEntry
from app.schemas import SearchIn, WatchlistIn, WatchlistOut
from app.services import enrichment, es as es_service
from app.services.audit import audit

router = APIRouter(tags=["hunting"])


def _es():
    return es_service.get_es()


@router.post("/search/events")
def search_events(body: SearchIn, user: User = Depends(require_role("viewer")), db: Session = Depends(get_db)):
    try:
        result = es_service.search_events(_es(), query=body.query, time_from=body.time_from, time_to=body.time_to,
                                          size=body.size, offset=body.offset)
    except Exception as exc:
        raise HTTPException(502, f"Search backend error: {type(exc).__name__}")
    audit(db, user.username, "search", "events", None, {"query": body.query[:200]})
    db.commit()
    return result


@router.get("/search/pivot")
def pivot(value: str, time_from: str = "now-7d", user: User = Depends(require_role("viewer"))):
    try:
        ioc_type, norm = enrichment.detect_ioc_type(value)
        return {"type": ioc_type, "value": norm, **es_service.pivot_indicator(_es(), ioc_type=ioc_type, value=norm, time_from=time_from)}
    except enrichment.InvalidIndicator as exc:
        raise HTTPException(422, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        raise HTTPException(502, f"Search backend error: {type(exc).__name__}")


@router.get("/ioc/lookup")
def ioc_lookup(value: str, refresh: bool = False, user: User = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    try:
        result = enrichment.lookup(db, value, use_cache=not refresh)
    except enrichment.InvalidIndicator as exc:
        raise HTTPException(422, str(exc))
    audit(db, user.username, "ioc_lookup", "ioc", None, {"value": result["value"], "verdict": result["verdict"]})
    db.commit()
    return result


@router.get("/watchlist", response_model=list[WatchlistOut])
def list_watchlist(db: Session = Depends(get_db), _: User = Depends(require_role("viewer"))):
    return db.scalars(select(WatchlistEntry).order_by(WatchlistEntry.id.desc())).all()


@router.post("/watchlist", response_model=WatchlistOut, status_code=201)
def add_watchlist(body: WatchlistIn, db: Session = Depends(get_db), user: User = Depends(require_role("analyst"))):
    try:
        ioc_type, value = enrichment.detect_ioc_type(body.value)
    except enrichment.InvalidIndicator as exc:
        raise HTTPException(422, str(exc))
    if db.scalars(select(WatchlistEntry).where(WatchlistEntry.ioc_type == ioc_type, WatchlistEntry.value == value)).first():
        raise HTTPException(409, "Already on the watchlist")
    row = WatchlistEntry(ioc_type=ioc_type, value=value, source=body.source, note=body.note)
    db.add(row)
    db.flush()
    audit(db, user.username, "watchlist_add", "watchlist", row.id, {"value": value})
    db.commit()
    return row


@router.delete("/watchlist/{entry_id}", status_code=204)
def remove_watchlist(entry_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("analyst"))):
    row = db.get(WatchlistEntry, entry_id)
    if not row:
        raise HTTPException(404, "Not found")
    row.active = False  # soft-delete keeps history
    audit(db, user.username, "watchlist_remove", "watchlist", row.id, {"value": row.value})
    db.commit()


@router.get("/stats/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(require_role("viewer"))):
    by_sev = dict(db.execute(select(Alert.severity, func.count()).where(Alert.status.in_(("open", "investigating"))).group_by(Alert.severity)).all())
    open_incidents = db.scalar(select(func.count()).select_from(Incident).where(Incident.status == "open")) or 0
    try:
        events = es_service.overview(_es())
    except Exception:
        events = {"events_24h": None, "failed_logins_24h": None, "per_hour": [], "top_sources": [], "top_hosts": [], "error": "Elasticsearch unavailable"}
    return {"alerts_by_severity": {k: by_sev.get(k, 0) for k in ("critical", "high", "medium", "low")},
            "open_incidents": open_incidents, **events}

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.core.config import get_settings
from app.db.models import Alert, AuditLog, Incident, User
from app.schemas import AlertOut, AlertPatch, IncidentOut
from app.services import correlation
from app.services.audit import audit

router = APIRouter(tags=["detections"])


@router.get("/rules")
def list_rules(request: Request, _: User = Depends(require_role("viewer"))):
    return [r.model_dump(by_alias=True, exclude_none=True) for r in request.app.state.rules]


@router.post("/detections/run")
def run_now(request: Request, lookback_minutes: int | None = Query(default=None, ge=1, le=10080),
            db: Session = Depends(get_db), user: User = Depends(require_role("analyst"))):
    """Run every rule now. Pass lookback_minutes to retro-hunt over older data (up to 7 days)."""
    from app.services import detection, es as es_service

    summary = detection.run_all(es_service.get_es(), db, request.app.state.rules, lookback_minutes)
    incidents = correlation.correlate(db, get_settings().correlation_window_minutes)
    audit(db, user.username, "detections_run", "detections", None, summary)
    db.commit()
    return {**summary, "incidents": len(incidents)}


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(status: str | None = None, severity: str | None = None, limit: int = 200,
                db: Session = Depends(get_db), _: User = Depends(require_role("viewer"))):
    q = select(Alert).order_by(Alert.first_seen.desc()).limit(min(limit, 500))
    if status:
        q = q.where(Alert.status == status)
    if severity:
        q = q.where(Alert.severity == severity)
    return db.scalars(q).all()


@router.get("/alerts/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: int, db: Session = Depends(get_db), _: User = Depends(require_role("viewer"))):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    return alert


@router.patch("/alerts/{alert_id}", response_model=AlertOut)
def patch_alert(alert_id: int, body: AlertPatch, db: Session = Depends(get_db), user: User = Depends(require_role("analyst"))):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    audit(db, user.username, "alert_status", "alert", alert.id, {"from": alert.status, "to": body.status})
    alert.status = body.status
    db.commit()
    return alert


@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(db: Session = Depends(get_db), _: User = Depends(require_role("viewer"))):
    return db.scalars(select(Incident).order_by(Incident.risk_score.desc(), Incident.last_seen.desc())).all()


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db), _: User = Depends(require_role("viewer"))):
    inc = db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")
    return {**IncidentOut.model_validate(inc).model_dump(mode="json"),
            "timeline": correlation.incident_timeline(inc),
            "alerts": [AlertOut.model_validate(a).model_dump(mode="json") for a in inc.alerts]}


@router.get("/audit")
def audit_log(limit: int = 200, db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 1000))).all()
    return [{"id": r.id, "ts": r.ts.isoformat(), "user": r.username, "action": r.action,
             "object": r.object_type, "object_id": r.object_id, "detail": r.detail} for r in rows]

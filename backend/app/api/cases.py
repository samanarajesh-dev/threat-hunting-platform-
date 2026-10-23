"""Case management: cases, linked alerts, append-only evidence, findings, reports."""
import hashlib
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.core.config import get_settings
from app.db.models import Alert, AuditLog, Case, Evidence, Finding, Incident, User
from app.schemas import CaseCreate, CaseListItem, CaseOut, CasePatch, EvidenceIn, EvidenceOut, FindingIn, FindingOut
from app.services import enrichment, reports
from app.services.audit import audit

router = APIRouter(prefix="/cases", tags=["cases"])


def _case_or_404(db: Session, case_id: int) -> Case:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


@router.get("", response_model=list[CaseListItem])
def list_cases(status: str | None = None, db: Session = Depends(get_db), _: User = Depends(require_role("viewer"))):
    q = select(Case).order_by(Case.updated_at.desc())
    if status:
        q = q.where(Case.status == status)
    return db.scalars(q).all()


@router.post("", response_model=CaseOut, status_code=201)
def create_case(body: CaseCreate, db: Session = Depends(get_db), user: User = Depends(require_role("analyst"))):
    case = Case(title=body.title, description=body.description, severity=body.severity, owner_id=user.id)
    if body.incident_id:
        inc = db.get(Incident, body.incident_id)
        if not inc:
            raise HTTPException(404, "Incident not found")
        case.incident_id = inc.id
        case.alerts = list(inc.alerts)  # an incident's alerts come with it
    for aid in body.alert_ids:
        alert = db.get(Alert, aid)
        if not alert:
            raise HTTPException(404, f"Alert {aid} not found")
        if alert not in case.alerts:
            case.alerts.append(alert)
    db.add(case)
    db.flush()
    audit(db, user.username, "case_created", "case", case.id, {"title": case.title})
    db.commit()
    return case


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: int, db: Session = Depends(get_db), _: User = Depends(require_role("viewer"))):
    return _case_or_404(db, case_id)


@router.patch("/{case_id}", response_model=CaseOut)
def patch_case(case_id: int, body: CasePatch, db: Session = Depends(get_db), user: User = Depends(require_role("analyst"))):
    case = _case_or_404(db, case_id)
    changes = body.model_dump(exclude_none=True)
    for k, v in changes.items():
        setattr(case, k, v)
    audit(db, user.username, "case_updated", "case", case.id, changes)
    db.commit()
    return case


@router.post("/{case_id}/alerts/{alert_id}", response_model=CaseOut)
def link_alert(case_id: int, alert_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("analyst"))):
    case, alert = _case_or_404(db, case_id), db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    if alert not in case.alerts:
        case.alerts.append(alert)
        audit(db, user.username, "alert_linked", "case", case.id, {"alert_id": alert_id})
    db.commit()
    return case


@router.post("/{case_id}/evidence", response_model=EvidenceOut, status_code=201)
def add_evidence(case_id: int, body: EvidenceIn, db: Session = Depends(get_db), user: User = Depends(require_role("analyst"))):
    case = _case_or_404(db, case_id)
    payload = body.content if body.content is not None else {"text": body.text or ""}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ev = Evidence(case_id=case.id, kind=body.kind, title=body.title, content=payload, sha256=hashlib.sha256(canonical).hexdigest(),
                  size_bytes=len(canonical), added_by=user.id)
    db.add(ev)
    db.flush()
    audit(db, user.username, "evidence_added", "case", case.id, {"evidence_id": ev.id, "kind": body.kind})
    db.commit()
    return ev


@router.post("/{case_id}/evidence/file", response_model=EvidenceOut, status_code=201)
async def add_evidence_file(case_id: int, title: str = Form(..., max_length=255), file: UploadFile = File(...),
                            db: Session = Depends(get_db), user: User = Depends(require_role("analyst"))):
    s = get_settings()
    case = _case_or_404(db, case_id)
    data = await file.read(s.max_evidence_bytes + 1)
    if len(data) > s.max_evidence_bytes:
        raise HTTPException(413, f"File larger than {s.max_evidence_bytes // (1024 * 1024)} MB")
    directory = Path(s.evidence_dir) / str(case.id)
    directory.mkdir(parents=True, exist_ok=True)
    stored = directory / uuid.uuid4().hex  # never trust the client filename for the path
    stored.write_bytes(data)
    ev = Evidence(case_id=case.id, kind="file", title=title, filename=(file.filename or "upload")[:255], storage_path=str(stored),
                  sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data), added_by=user.id)
    db.add(ev)
    db.flush()
    audit(db, user.username, "evidence_added", "case", case.id, {"evidence_id": ev.id, "kind": "file", "sha256": ev.sha256})
    db.commit()
    return ev


@router.get("/{case_id}/evidence/{evidence_id}/download")
def download_evidence(case_id: int, evidence_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    ev = db.get(Evidence, evidence_id)
    if not ev or ev.case_id != case_id or not ev.storage_path:
        raise HTTPException(404, "Evidence file not found")
    audit(db, user.username, "evidence_downloaded", "case", case_id, {"evidence_id": evidence_id})
    db.commit()
    return FileResponse(ev.storage_path, filename=ev.filename or "evidence.bin", media_type="application/octet-stream")


@router.post("/{case_id}/findings", response_model=FindingOut, status_code=201)
def add_finding(case_id: int, body: FindingIn, db: Session = Depends(get_db), user: User = Depends(require_role("analyst"))):
    case = _case_or_404(db, case_id)
    f = Finding(case_id=case.id, created_by=user.id, **body.model_dump())
    db.add(f)
    db.flush()
    audit(db, user.username, "finding_added", "case", case.id, {"finding_id": f.id})
    db.commit()
    return f


@router.get("/{case_id}/timeline")
def case_timeline(case_id: int, db: Session = Depends(get_db), _: User = Depends(require_role("viewer"))):
    _case_or_404(db, case_id)
    rows = db.scalars(select(AuditLog).where(AuditLog.object_type == "case", AuditLog.object_id == case_id).order_by(AuditLog.ts)).all()
    return [{"ts": r.ts.isoformat(), "user": r.username, "action": r.action, "detail": r.detail} for r in rows]


@router.get("/{case_id}/report")
def case_report(case_id: int, format: str = "pdf", db: Session = Depends(get_db), user: User = Depends(require_role("viewer"))):
    case = _case_or_404(db, case_id)
    iocs = []
    for ev in case.evidence:  # re-use cached verdicts for IOC evidence; no new API calls while generating a report
        if ev.kind == "ioc" and ev.content and ev.content.get("value"):
            try:
                iocs.append(enrichment.lookup(db, ev.content["value"], use_cache=True))
            except enrichment.InvalidIndicator:
                continue
    audit(db, user.username, "report_generated", "case", case.id, {"format": format})
    db.commit()
    if format == "md":
        return Response(reports.build_case_report_markdown(case, user.username), media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="case-{case.id}-report.md"'})
    if format != "pdf":
        raise HTTPException(422, "format must be pdf or md")
    return Response(reports.build_case_report_pdf(case, user.username, iocs), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="case-{case.id}-report.pdf"'})

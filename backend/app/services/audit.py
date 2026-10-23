from sqlalchemy.orm import Session

from app.db.models import AuditLog


def audit(db: Session, username: str, action: str, object_type: str, object_id: int | None = None, detail: dict | None = None) -> None:
    db.add(AuditLog(username=username, action=action, object_type=object_type, object_id=object_id, detail=detail))

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import auth, cases, detections, hunting
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal, init_db
from app.services import correlation, detection, es as es_service
from app.services.rules import load_rules

log = logging.getLogger("thp")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def _bootstrap_admin() -> None:
    s = get_settings()
    if not s.admin_password:
        return
    with SessionLocal() as db:
        if db.scalars(select(User)).first() is None:
            db.add(User(username=s.admin_username, password_hash=hash_password(s.admin_password), role="admin"))
            db.commit()
            log.info("created initial admin user '%s'", s.admin_username)


def _detection_loop(app: FastAPI, stop: threading.Event) -> None:
    s = get_settings()
    while not stop.wait(s.detection_interval_seconds):
        try:
            with SessionLocal() as db:
                detection.run_all(es_service.get_es(), db, app.state.rules)
                correlation.correlate(db, s.correlation_window_minutes)
        except Exception:
            log.exception("detection cycle failed (will retry)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    s.validate_for_runtime()
    init_db()
    _bootstrap_admin()
    app.state.rules = load_rules(s.rules_dir)
    log.info("loaded %d detection rules", len(app.state.rules))
    try:
        es_service.ensure_index_template(es_service.get_es())
    except Exception as exc:
        log.warning("Elasticsearch not reachable at startup (%s); continuing", type(exc).__name__)
    stop = threading.Event()
    if s.detection_enabled:
        threading.Thread(target=_detection_loop, args=(app, stop), daemon=True, name="detection-loop").start()
    yield
    stop.set()


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title=s.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_methods=["*"], allow_headers=["*"])
    for r in (auth.router, hunting.router, detections.router, cases.router):
        app.include_router(r, prefix="/api/v1")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()

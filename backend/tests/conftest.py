import os
import tempfile

# Configure BEFORE the app is imported: temp sqlite DB, no background loop, unreachable ES.
_tmp = tempfile.mkdtemp(prefix="thp-test-")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db",
    "DETECTION_ENABLED": "false",
    "ADMIN_PASSWORD": "Adm1n-test-password",
    "JWT_SECRET": "test-secret-test-secret-test-secret-123",
    "ES_URL": "http://127.0.0.1:1",
    "EVIDENCE_DIR": f"{_tmp}/evidence",
    "VT_API_KEY": "",
    "ABUSEIPDB_API_KEY": "",
    "OTX_API_KEY": "",
})

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db.session import Base  # noqa: E402


@pytest.fixture()
def db():
    """Fresh in-memory database per test (pure-logic tests)."""
    from app.db import models  # noqa: F401

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()

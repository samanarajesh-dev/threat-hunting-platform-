from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.models import User
from app.db.session import SessionLocal

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
ROLE_RANK = {"viewer": 1, "analyst": 2, "admin": 3}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_token(token)
    except PyJWTError:
        raise err
    user = db.scalars(select(User).where(User.username == payload.get("sub"))).first()
    if not user or not user.is_active:
        raise err
    return user


def require_role(minimum: str):
    def checker(user: User = Depends(current_user)) -> User:
        if ROLE_RANK[user.role] < ROLE_RANK[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role '{minimum}' or higher")
        return user

    return checker

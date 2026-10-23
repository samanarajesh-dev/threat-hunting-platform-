from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db, require_role
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.schemas import TokenOut, UserCreate, UserOut
from app.services.audit import audit

router = APIRouter(prefix="/auth", tags=["auth"])

# A pre-computed hash so login takes the same time whether or not the user exists.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalars(select(User).where(User.username == form.username)).first()
    ok = verify_password(form.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or not user.is_active:
        audit(db, form.username[:64], "login_failed", "user")
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")
    audit(db, user.username, "login", "user", user.id)
    db.commit()
    return TokenOut(access_token=create_access_token(user.username, user.role), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    if db.scalars(select(User).where(User.username == body.username)).first():
        raise HTTPException(409, "Username already exists")
    user = User(username=body.username, password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    db.flush()
    audit(db, admin.username, "user_created", "user", user.id, {"role": body.role})
    db.commit()
    return user

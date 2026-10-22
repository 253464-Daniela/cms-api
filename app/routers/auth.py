from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import ConflictError, UnauthorizedError
from app.models import User
from app.schemas import Token, UserCreate, UserRead
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario administrador",
    responses={
        409: {"description": "Email ya registrado"},
    },
)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    exists = db.scalar(select(User).where(User.email == payload.email))
    if exists:
        raise ConflictError(f"El email '{payload.email}' ya está registrado")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Obtener token JWT",
    responses={401: {"description": "Credenciales inválidas"}},
)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.hashed_password):
        raise UnauthorizedError("Email o contraseña incorrectos")
    if not user.is_active:
        raise UnauthorizedError("Usuario desactivado")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead, summary="Datos del usuario autenticado")
def me(current_user: User = Depends(get_current_user)):
    return current_user
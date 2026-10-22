from fastapi import Depends, Header, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.exceptions import UnauthorizedError
from app.models import User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise UnauthorizedError("Falta el token de autenticación")
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise UnauthorizedError("Token inválido o expirado")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise UnauthorizedError("Usuario inactivo o no existe")
    return user


class Pagination:
    """Dependencia reutilizable para paginación."""

    def __init__(
        self,
        page: int = 1,
        page_size: int | None = None,
        x_page_size: int | None = Header(None, alias="X-Page-Size"),
    ):
        if page < 1:
            page = 1
        size = page_size or x_page_size or settings.DEFAULT_PAGE_SIZE
        if size < 1:
            size = settings.DEFAULT_PAGE_SIZE
        if size > settings.MAX_PAGE_SIZE:
            size = settings.MAX_PAGE_SIZE
        self.page = page
        self.page_size = size
        self.offset = (page - 1) * size
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import ConflictError, NotFoundError
from app.models import Category, Post, Tag, User
from app.schemas import CategoryCreate, CategoryRead, CategoryWithCount, TagRead
from app.utils import slugify

router = APIRouter(tags=["Categorías y Etiquetas"])


@router.get(
    "/categories",
    response_model=list[CategoryWithCount],
    summary="Listar categorías con conteo de posts",
)
def list_categories(db: Session = Depends(get_db)):
    stmt = (
        select(Category, func.count(Post.id))
        .outerjoin(Post, (Post.category_id == Category.id) & (Post.is_published.is_(True)))
        .group_by(Category.id)
        .order_by(Category.name)
    )
    result = db.execute(stmt).all()
    return [
        CategoryWithCount(**CategoryRead.model_validate(cat).model_dump(), post_count=count)
        for cat, count in result
    ]


@router.get("/tags", response_model=list[TagRead], summary="Listar etiquetas")
def list_tags(db: Session = Depends(get_db)):
    return db.scalars(select(Tag).order_by(Tag.name)).all()


# ---------- Admin ----------
@router.post(
    "/categories",
    response_model=CategoryRead,
    status_code=201,
    summary="Crear categoría (requiere auth)",
    responses={409: {"description": "Ya existe"}},
)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    slug = slugify(payload.name)
    if db.scalar(select(Category).where((Category.name == payload.name) | (Category.slug == slug))):
        raise ConflictError(f"La categoría '{payload.name}' ya existe")
    cat = Category(name=payload.name, slug=slug, description=payload.description)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete(
    "/categories/{category_id}",
    status_code=204,
    summary="Eliminar categoría (requiere auth)",
    responses={404: {"description": "No existe"}},
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cat = db.get(Category, category_id)
    if not cat:
        raise NotFoundError("Categoría", category_id)
    db.delete(cat)
    db.commit()
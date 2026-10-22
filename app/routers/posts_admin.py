from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import ConflictError, NotFoundError
from app.models import Category, Post, Tag, User
from app.schemas import PostCreate, PostDetail, PostListItem, PostUpdate
from app.utils import slugify

router = APIRouter(
    prefix="/admin/posts",
    tags=["Posts (admin)"],
    dependencies=[Depends(get_current_user)],
)


def _get_or_404(db: Session, post_id: int) -> Post:
    post = db.scalar(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.category), selectinload(Post.tags))
    )
    if not post:
        raise NotFoundError("Post", post_id)
    return post


def _resolve_tags(db: Session, names: list[str] | None) -> list[Tag]:
    if not names:
        return []
    tags = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        slug = slugify(name)
        tag = db.scalar(select(Tag).where(Tag.slug == slug))
        if not tag:
            tag = Tag(name=name, slug=slug)
            db.add(tag)
        tags.append(tag)
    return tags


@router.post(
    "",
    response_model=PostDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Crear post",
    responses={409: {"description": "Slug duplicado"}, 404: {"description": "Categoría no existe"}},
)
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    slug = slugify(payload.title)
    if db.scalar(select(Post).where(Post.slug == slug)):
        raise ConflictError(f"Ya existe un post con slug '{slug}'")

    if payload.category_id:
        if not db.get(Category, payload.category_id):
            raise NotFoundError("Categoría", payload.category_id)

    post = Post(
        title=payload.title,
        slug=slug,
        excerpt=payload.excerpt,
        content=payload.content,
        cover_image=payload.cover_image,
        seo_title=payload.seo_title,
        seo_description=payload.seo_description,
        category_id=payload.category_id,
        author_id=current_user.id,
        is_published=payload.is_published,
        published_at=datetime.now(timezone.utc) if payload.is_published else None,
        tags=_resolve_tags(db, payload.tags),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.patch(
    "/{post_id}",
    response_model=PostDetail,
    summary="Actualizar parcialmente un post",
    responses={404: {"description": "No existe"}},
)
def update_post(
    post_id: int,
    payload: PostUpdate,
    db: Session = Depends(get_db),
):
    post = _get_or_404(db, post_id)
    data = payload.model_dump(exclude_unset=True)

    if "tags" in data:
        post.tags = _resolve_tags(db, data.pop("tags"))

    if "category_id" in data and data["category_id"] is not None:
        if not db.get(Category, data["category_id"]):
            raise NotFoundError("Categoría", data["category_id"])

    for field, value in data.items():
        setattr(post, field, value)

    db.commit()
    db.refresh(post)
    return post


@router.post(
    "/{post_id}/publish",
    response_model=PostDetail,
    summary="Publicar un post",
)
def publish_post(post_id: int, db: Session = Depends(get_db)):
    post = _get_or_404(db, post_id)
    if not post.is_published:
        post.is_published = True
        post.published_at = post.published_at or datetime.now(timezone.utc)
        db.commit()
        db.refresh(post)
    return post


@router.post(
    "/{post_id}/unpublish",
    response_model=PostDetail,
    summary="Despublicar un post",
)
def unpublish_post(post_id: int, db: Session = Depends(get_db)):
    post = _get_or_404(db, post_id)
    post.is_published = False
    db.commit()
    db.refresh(post)
    return post


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un post",
    responses={404: {"description": "No existe"}},
)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = _get_or_404(db, post_id)
    db.delete(post)
    db.commit()


@router.get(
    "",
    response_model=list[PostListItem],
    summary="Listar TODOS los posts (incluye borradores)",
)
def list_all_posts(db: Session = Depends(get_db)):
    return db.scalars(
        select(Post)
        .options(selectinload(Post.category), selectinload(Post.tags))
        .order_by(Post.created_at.desc())
    ).all()
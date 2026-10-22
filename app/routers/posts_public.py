from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import Pagination
from app.exceptions import NotFoundError
from app.models import Post, Tag, post_tags
from app.schemas import PaginatedMeta, PaginatedPosts, PostDetail, PostListItem

router = APIRouter(prefix="/posts", tags=["Posts (público)"])


def _base_query():
    return (
        select(Post)
        .where(Post.is_published.is_(True))
        .options(selectinload(Post.category), selectinload(Post.tags))
    )


@router.get(
    "",
    response_model=PaginatedPosts,
    summary="Listar posts publicados",
    responses={422: {"description": "Parámetros inválidos"}},
)
def list_posts(
    response: Response,
    pag: Pagination = Depends(),
    category: str | None = Query(None, description="Filtrar por slug de categoría"),
    tag: str | None = Query(None, description="Filtrar por slug de etiqueta"),
    q: str | None = Query(None, min_length=1, max_length=100, description="Búsqueda por título"),
    sort: str = Query("newest", pattern="^(newest|oldest|title)$"),
    db: Session = Depends(get_db),
):
    stmt = _base_query()

    if category:
        stmt = stmt.join(Post.category).where(Post.category.has(slug=category))
    if tag:
        stmt = stmt.join(Post.tags).where(Tag.slug == tag)
    if q:
        stmt = stmt.where(or_(Post.title.ilike(f"%{q}%"), Post.excerpt.ilike(f"%{q}%")))

    order = {
        "newest": Post.published_at.desc(),
        "oldest": Post.published_at.asc(),
        "title": Post.title.asc(),
    }[sort]
    stmt = stmt.order_by(order)

    # total antes de paginar
    total = db.scalar(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ) or 0

    posts = db.scalars(stmt.offset(pag.offset).limit(pag.page_size)).all()

    total_pages = (total + pag.page_size - 1) // pag.page_size or 1

    # Headers de paginación (convención habitual)
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(pag.page)
    response.headers["X-Page-Size"] = str(pag.page_size)
    response.headers["X-Total-Pages"] = str(total_pages)
    response.headers["Cache-Control"] = "public, max-age=60"

    return PaginatedPosts(
        meta=PaginatedMeta(
            page=pag.page,
            page_size=pag.page_size,
            total_items=total,
            total_pages=total_pages,
        ),
        items=posts,
    )


@router.get(
    "/{slug}",
    response_model=PostDetail,
    summary="Detalle de un post por slug",
    responses={404: {"description": "Post no encontrado"}},
)
def get_post(slug: str, db: Session = Depends(get_db)):
    post = db.scalar(_base_query().where(Post.slug == slug))
    if not post:
        raise NotFoundError("Post", slug)
    return post


@router.get(
    "/{slug}/related",
    response_model=list[PostListItem],
    summary="Posts relacionados (misma categoría o etiquetas)",
)
def related_posts(
    slug: str,
    limit: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
):
    post = db.scalar(select(Post).where(Post.slug == slug, Post.is_published.is_(True)))
    if not post:
        raise NotFoundError("Post", slug)

    stmt = _base_query().where(Post.id != post.id)

    conditions = []
    if post.category_id:
        conditions.append(Post.category_id == post.category_id)
    if post.tags:
        tag_ids = [t.id for t in post.tags]
        conditions.append(
            Post.id.in_(
                select(post_tags.c.post_id).where(post_tags.c.tag_id.in_(tag_ids))
            )
        )

    if conditions:
        from sqlalchemy import or_
        stmt = stmt.where(or_(*conditions))

    return db.scalars(stmt.order_by(Post.published_at.desc()).limit(limit)).all()
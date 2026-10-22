from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
    exp: int | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime


# ---------- Category ----------
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    created_at: datetime


class CategoryWithCount(CategoryRead):
    post_count: int = 0


# ---------- Tag ----------
class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


# ---------- Post ----------
class PostBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    excerpt: str | None = Field(None, max_length=500)
    content: str = Field(..., min_length=1)
    cover_image: str | None = Field(None, max_length=500)
    seo_title: str | None = Field(None, max_length=200)
    seo_description: str | None = Field(None, max_length=300)
    category_id: int | None = None
    tags: list[str] | None = None


class PostCreate(PostBase):
    is_published: bool = False


class PostUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=200)
    excerpt: str | None = Field(None, max_length=500)
    content: str | None = Field(None, min_length=1)
    cover_image: str | None = Field(None, max_length=500)
    seo_title: str | None = Field(None, max_length=200)
    seo_description: str | None = Field(None, max_length=300)
    category_id: int | None = None
    tags: list[str] | None = None


class PostListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    excerpt: str | None
    cover_image: str | None
    is_published: bool
    published_at: datetime | None
    created_at: datetime
    category: CategoryRead | None = None
    tags: list[TagRead] = []


class PostDetail(PostListItem):
    content: str
    seo_title: str | None
    seo_description: str | None
    updated_at: datetime


class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PaginatedPosts(BaseModel):
    meta: PaginatedMeta
    items: list[PostListItem]
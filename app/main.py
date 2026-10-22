from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.exceptions import (
    APIError,
    api_error_handler,
    http_exception_handler,
    validation_error_handler,
)
from app.models import User
from app.routers import auth, categories, posts_admin, posts_public
from app.security import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Usuario demo (solo desarrollo)
    db = SessionLocal()
    try:
        from sqlalchemy import select
        if not db.scalar(select(User).where(User.email == "admin@demo.com")):
            db.add(
                User(
                    email="admin@demo.com",
                    hashed_password=hash_password("admin12345"),
                    is_active=True,
                )
            )
            db.commit()
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API de Blog CMS con FastAPI",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ---------- Middlewares ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page", "X-Page-Size", "X-Total-Pages"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ---------- Exception handlers ----------
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "Error interno del servidor",
                "details": [],
                "path": request.url.path,
            }
        },
    )


# ---------- Routers ----------
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(posts_public.router, prefix=settings.API_V1_PREFIX)
app.include_router(categories.router, prefix=settings.API_V1_PREFIX)
app.include_router(posts_admin.router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"], summary="Healthcheck")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}
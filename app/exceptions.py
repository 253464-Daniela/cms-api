from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(HTTPException):
    """Error de negocio con código y detalle estructurado."""

    def __init__(self, status_code: int, code: str, message: str, details: list | None = None):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details or []


class NotFoundError(APIError):
    def __init__(self, resource: str, identifier):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="not_found",
            message=f"{resource} con identificador '{identifier}' no encontrado",
        )


class ConflictError(APIError):
    def __init__(self, message: str):
        super().__init__(status.HTTP_409_CONFLICT, "conflict", message)


class UnauthorizedError(APIError):
    def __init__(self, message: str = "Credenciales inválidas"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message=message,
        )


class ForbiddenError(APIError):
    def __init__(self, message: str = "No tienes permisos"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="forbidden",
            message=message,
        )


# ---------- Handlers ----------
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "path": request.url.path,
            }
        },
        headers=getattr(exc, "headers", None),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [
        {
            "field": ".".join(str(p) for p in err["loc"] if p != "body"),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Los datos enviados no son válidos",
                "details": details,
                "path": request.url.path,
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "http_error",
                "message": str(exc.detail),
                "details": [],
                "path": request.url.path,
            }
        },
        headers=exc.headers,
    )
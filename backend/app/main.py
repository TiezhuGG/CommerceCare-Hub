import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import DomainError
from app.schemas import ErrorResponse


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="CommerceCare Hub API", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def trace_request(
        request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]
    ) -> JSONResponse:
        request.state.trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Trace-ID"] = request.state.trace_id
        return response

    @application.exception_handler(DomainError)
    async def domain_error_handler(request: Request, error: DomainError) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
        payload = ErrorResponse(code=error.code, message=error.message, trace_id=trace_id)
        return JSONResponse(status_code=400, content=payload.model_dump())

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, error: StarletteHTTPException) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
        payload = ErrorResponse(
            code="HTTP_ERROR",
            message="Request could not be completed",
            trace_id=trace_id,
            details={"detail": error.detail},
        )
        return JSONResponse(status_code=error.status_code, content=payload.model_dump())

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
        payload = ErrorResponse(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            trace_id=trace_id,
            details={"errors": error.errors()},
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @application.get("/healthz", tags=["health"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(router)
    return application


app = create_app()

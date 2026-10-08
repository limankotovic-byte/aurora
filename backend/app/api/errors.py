import logging
from collections.abc import Mapping
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.exceptions import AppError, ErrorCode, RateLimited
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger("aurora.errors")


def error_response(
    request: Request,
    status: int,
    code: ErrorCode,
    message: str,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    request_id: str = request.state.request_id
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message, request_id=request_id))
    response_headers = dict(headers or {})
    response_headers["X-Request-ID"] = request_id
    return JSONResponse(
        status_code=status,
        content=payload.model_dump(mode="json"),
        headers=response_headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        headers: dict[str, str] = {}
        if isinstance(exc, RateLimited) and exc.retry_after is not None:
            headers["Retry-After"] = str(exc.retry_after)
        logger.warning(
            "application_error",
            extra={"request_id": request.state.request_id, "error_code": exc.code.value},
        )
        return error_response(request, exc.status_code, exc.code, exc.public_message, headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            request, 422, ErrorCode.VALIDATION_ERROR, "Некорректные параметры запроса"
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = {
            404: ErrorCode.NOT_FOUND,
            405: ErrorCode.METHOD_NOT_ALLOWED,
        }.get(exc.status_code, ErrorCode.HTTP_ERROR)
        try:
            message = HTTPStatus(exc.status_code).phrase
        except ValueError:
            message = "Ошибка HTTP"
        return error_response(request, exc.status_code, code, message, exc.headers)

    @app.exception_handler(Exception)
    async def handle_unknown_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_error",
            extra={
                "request_id": request.state.request_id,
                "error_code": ErrorCode.UNKNOWN_ERROR.value,
                "exception_type": type(exc).__name__,
            },
        )
        return error_response(request, 500, ErrorCode.UNKNOWN_ERROR, "Внутренняя ошибка сервера")

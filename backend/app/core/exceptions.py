from enum import StrEnum


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    HTTP_ERROR = "HTTP_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PARSING_ERROR = "PARSING_ERROR"
    PLAYER_UNAVAILABLE = "PLAYER_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class AppError(Exception):
    """Internal exception details are never used as a public error message."""

    code: ErrorCode = ErrorCode.UNKNOWN_ERROR
    status_code: int = 500
    public_message: str = "Внутренняя ошибка сервера"


class NetworkError(AppError):
    code = ErrorCode.NETWORK_ERROR
    status_code = 502
    public_message = "Не удалось связаться с источником"


class InvalidAnimeId(AppError):
    code = ErrorCode.VALIDATION_ERROR
    status_code = 422
    public_message = "Некорректный идентификатор тайтла"


class InvalidSearchQuery(AppError):
    code = ErrorCode.VALIDATION_ERROR
    status_code = 422
    public_message = "Поиск AMD принимает от 3 до 25 символов"


class InvalidEpisodeId(AppError):
    code = ErrorCode.VALIDATION_ERROR
    status_code = 422
    public_message = "Некорректный идентификатор серии"


class ProviderUnavailable(AppError):
    code = ErrorCode.PROVIDER_UNAVAILABLE
    status_code = 503
    public_message = "Источник временно недоступен"


class ParsingError(AppError):
    code = ErrorCode.PARSING_ERROR
    status_code = 502
    public_message = "Не удалось обработать данные источника"


class NotFound(AppError):
    code = ErrorCode.NOT_FOUND
    status_code = 404
    public_message = "Запрашиваемый ресурс не найден"


class PlayerUnavailable(AppError):
    code = ErrorCode.PLAYER_UNAVAILABLE
    status_code = 503
    public_message = "Плеер временно недоступен"


class RateLimited(AppError):
    code = ErrorCode.RATE_LIMITED
    status_code = 429
    public_message = "Слишком много запросов, попробуйте позже"

    def __init__(self, detail: str = "", *, retry_after: int | None = None) -> None:
        super().__init__(detail)
        if retry_after is not None and retry_after < 0:
            raise ValueError("retry_after cannot be negative")
        self.retry_after = retry_after


class UnsupportedOperation(AppError):
    code = ErrorCode.UNSUPPORTED_OPERATION
    status_code = 422
    public_message = "Источник не поддерживает эту операцию или фильтр"

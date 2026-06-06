import logging
import traceback
from dataclasses import dataclass
from typing import Callable, Mapping, Union

from marshmallow.exceptions import ValidationError
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from werkzeug.exceptions import HTTPException

from pamfilico_flask_core.responses import standard_response

logger = logging.getLogger(__name__)

DEBUG = True  # global variable setting the debug config

ErrorHandlerCallable = Callable[[Exception], tuple]
ErrorHandlerSpec = Union[int, "ErrorHandlerConfig", ErrorHandlerCallable]


@dataclass(frozen=True)
class ErrorHandlerConfig:
    """Declarative handler for a custom exception type."""

    status_code: int
    log_level: int = logging.ERROR
    ui_message: str | None = None


def _make_standard_handler(
    status_code: int,
    log_level: int = logging.ERROR,
    ui_message: str | None = None,
) -> ErrorHandlerCallable:
    def handler(error: Exception):
        msg = ui_message if ui_message is not None else str(error)
        logger.log(log_level, "%s: %s", type(error).__name__, error)
        return standard_response(error=True, ui_message=msg, status_code=status_code)

    return handler


def register_error_handlers(app, handlers: Mapping[type, ErrorHandlerSpec]) -> None:
    """Register Flask error handlers for app-specific exception types.

    Each value in ``handlers`` may be:
    - an ``int`` HTTP status code (uses the default ``standard_response`` handler)
    - an ``ErrorHandlerConfig`` for status, log level, and optional fixed UI message
    - a callable ``(error) -> standard_response`` tuple for full control
    """
    for exc_type, spec in handlers.items():
        if callable(spec) and not isinstance(spec, type):
            app.errorhandler(exc_type)(spec)
        elif isinstance(spec, int):
            app.errorhandler(exc_type)(_make_standard_handler(spec))
        elif isinstance(spec, ErrorHandlerConfig):
            app.errorhandler(exc_type)(
                _make_standard_handler(
                    spec.status_code,
                    log_level=spec.log_level,
                    ui_message=spec.ui_message,
                )
            )
        else:
            raise TypeError(
                f"Handler for {exc_type!r} must be int, ErrorHandlerConfig, or callable"
            )


class BaseError(Exception):
    """Base exception for all custom Flask API errors."""

    def __init__(self, message, session=None):
        self.session = session
        super().__init__(message)
        if self.session:
            try:
                logger.error("RollingBack session")
                self.session.rollback()
                self.session.close()
            except Exception as e:
                logger.error("Error rolling back session: %s", e)
                traceback_info = traceback.format_exc()
                logger.error("Traceback: %s", traceback_info)


class BizlogicError(BaseError):
    """Business logic rule violation (e.g. invalid state transition)."""
    pass


class DataNotFoundError(BaseError):
    """Entity not found when querying by ID or other lookup."""
    pass


class VehicleError(BaseError):
    """Vehicle domain or operation constraint violation."""
    pass


class AlreadyExistsError(BaseError):
    """Duplicate resource (unique constraint or logical duplicate)."""
    pass


class NotFoundError(BaseError):
    """Resource not found (generic 404)."""
    pass


class ServerError(BaseError):
    """Internal server or dependency failure."""
    pass


class DatabaseError(BaseError):
    """Database constraint or integrity violation (wrapped)."""
    pass


class AuthenticationError(BaseError):
    """Invalid or missing authentication (token, user not found)."""
    pass


class EnvironmentVariableError(BaseError):
    """Required environment variable missing or invalid."""
    pass


class StripeError(BaseError):
    """Stripe API or payment processing failure."""
    pass


class ForbidenError(BaseError):
    """Forbidden access (user authenticated but not authorized)."""
    pass


def init_errors(app, *, extra_handlers: Mapping[type, ErrorHandlerSpec] | None = None, debug: bool | None = None):
    """Register Flask error handlers for all custom and common exceptions.

    Call once during app initialization (e.g. in create_app). Handlers
    return standard_response() with appropriate status codes.

    Pass ``extra_handlers`` to register app-specific exception types without
    forking the package. Each value is an HTTP status ``int``, an
    ``ErrorHandlerConfig``, or a custom handler callable.
    """
    global DEBUG
    if debug is not None:
        DEBUG = debug
    @app.errorhandler(409)
    def conflict_error(error):
        logger.error("HTTP 409: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(
            error=True,
            ui_message="Conflict",
            status_code=409,
        )

    @app.errorhandler(PermissionError)
    def permission_error(error):
        logger.error("PermissionError: %s", error)
        return standard_response(
            error=True,
            ui_message="Insufficient Permissions",
            status_code=403,
        )

    @app.errorhandler(NotFoundError)
    def resource_not_found_error(error):
        logger.info("NotFoundError: %s", error)
        msg = str(error)
        return standard_response(error=True, ui_message=msg, status_code=404)

    @app.errorhandler(DataNotFoundError)
    def data_not_found_error(error):
        logger.info("DataNotFoundError: %s", error)
        msg = str(error)
        return standard_response(error=True, ui_message=msg, status_code=404)

    @app.errorhandler(ForbidenError)
    def forbiden_error(error):
        logger.error("ForbidenError: %s", error)
        return standard_response(
            error=True,
            ui_message=str(error),
            status_code=403,
        )

    @app.errorhandler(VehicleError)
    def vehicle_error(error):
        logger.error("VehicleError: %s", error)
        return standard_response(error=True, ui_message=str(error), status_code=400)

    @app.errorhandler(AuthenticationError)
    def authentication_error(error):
        logger.error("AuthenticationError: %s", error)
        msg = str(error)
        return standard_response(error=True, ui_message=msg, status_code=401)

    @app.errorhandler(BizlogicError)
    def bizlogic_error(error):
        logger.error("BizlogicError: %s", error)
        return standard_response(error=True, ui_message=str(error), status_code=400)

    @app.errorhandler(EnvironmentVariableError)
    def environment_variable_error(error):
        logger.error("EnvironmentVariableError: %s", error)
        return standard_response(error=True, ui_message=str(error), status_code=500)

    @app.errorhandler(ValidationError)
    def validation_error(error):
        errors = []
        for field, messages in error.messages.items():
            if isinstance(messages, list):
                errors.extend([f"{field}: {msg}" for msg in messages])
            else:
                errors.append(f"{field}: {messages}")
        error_message = "; ".join(errors) if errors else "Validation error"
        logger.error("ValidationError: %s", error_message)
        return standard_response(
            error=True,
            ui_message=error_message,
            status_code=400,
        )

    @app.errorhandler(ValueError)
    def value_error(error):
        logger.error("ValueError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(error=True, ui_message=str(error), status_code=400)

    @app.errorhandler(AlreadyExistsError)
    def resource_exist_error(error):
        logger.error("AlreadyExistsError: %s", error)
        msg = str(error)
        return standard_response(
            error=True,
            ui_message=msg,
            status_code=409,
        )

    @app.errorhandler(DataError)
    def data_error(error):
        logger.error("DataError: %s", error)
        return standard_response(
            error=True,
            ui_message="Invalid data provided.",
            status_code=400,
        )

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        logger.error("IntegrityError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        msg = str(error)
        if "unique" in str(error).lower():
            msg = "Object already exists."
        return standard_response(
            error=True,
            ui_message=msg,
            status_code=409,
        )

    @app.errorhandler(OperationalError)
    def operational_error(error):
        msg = str(error)
        logger.error("OperationalError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(
            error=True,
            dev_message=f"Database Error: {msg}",
            ui_message="Database Error",
            status_code=500,
        )

    @app.errorhandler(DatabaseError)
    def database_error_handler(error):
        logger.error("DatabaseError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        msg = str(error)
        if "unique" in str(error).lower():
            msg = "Object already exists."
        return standard_response(
            error=True,
            ui_message=msg,
            status_code=409,
        )

    if extra_handlers:
        register_error_handlers(app, extra_handlers)

    @app.errorhandler(500)
    def server_error(error):
        logger.error("HTTP 500: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(
            error=True,
            ui_message="Internal Server Error",
            status_code=500,
        )

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error("Unhandled exception: %s", e)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        if isinstance(e, HTTPException):
            return e
        dev_msg = ""
        if DEBUG:
            dev_msg = traceback_info if traceback_info else str(e)
        return standard_response(
            error=True,
            ui_message="Internal Server Error",
            dev_message=dev_msg,
            status_code=500,
        )

    @app.errorhandler(StripeError)
    def stripe_error(error):
        msg = str(error)
        logger.error("StripeError: %s", error)
        traceback_info = traceback.format_exc()
        logger.error("Traceback: %s", traceback_info)
        return standard_response(
            error=True,
            ui_message=msg,
            status_code=404,
        )

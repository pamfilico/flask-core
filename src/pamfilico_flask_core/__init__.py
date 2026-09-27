"""Pamfilico Flask Core - standard response and error classes for Flask APIs."""

from importlib.metadata import PackageNotFoundError, version as _dist_version

try:
    #: Read from the INSTALLED distribution, never hardcoded — a literal here is
    #: one more thing that can drift from pyproject.toml and from the git tag,
    #: which is the exact failure this is meant to make visible. Consumers pin by
    #: tag and can assert on this to prove which build they actually got.
    __version__ = _dist_version("pamfilico-flask-core")
except PackageNotFoundError:  # running from a source tree, not installed
    __version__ = "0.0.0.dev0"

from pamfilico_flask_core.responses import standard_response
from pamfilico_flask_core.errors import (
    AlreadyExistsError,
    AuthenticationError,
    BaseError,
    BizlogicError,
    DatabaseError,
    DataNotFoundError,
    EnvironmentVariableError,
    ErrorHandlerConfig,
    ForbidenError,
    NotFoundError,
    ServerError,
    StripeError,
    VehicleError,
    init_errors,
    register_error_handlers,
)

__all__ = [
    "__version__",
    "standard_response",
    "AlreadyExistsError",
    "AuthenticationError",
    "BaseError",
    "BizlogicError",
    "DatabaseError",
    "DataNotFoundError",
    "EnvironmentVariableError",
    "ErrorHandlerConfig",
    "ForbidenError",
    "NotFoundError",
    "ServerError",
    "StripeError",
    "VehicleError",
    "init_errors",
    "register_error_handlers",
]

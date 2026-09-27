"""Pamfilico Flask Core - standard response and error classes for Flask APIs."""

#: Keep in step with ``version`` in pyproject.toml, and TAG the commit that bumps
#: it (``git tag v<version> && git push --tags``). Consumers pin by tag, so an
#: untagged bump is unreachable: poetry can only be asked for a branch, and the
#: branch moves. Exposing it here is what lets a consumer assert which build it
#: actually got — without it, the only way to tell is diffing ``dir()`` against
#: GitHub, which is how a README documenting an API the installed code did not
#: have went unnoticed.
__version__ = "1.2.0"

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

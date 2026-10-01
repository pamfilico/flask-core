# pamfilico-flask-core

Standard response envelope and error classes for Flask APIs.

## Installation

```bash
pip install git+https://github.com/pamfilico/flask-core.git
```

## Usage

### Standard Response

```python
from pamfilico_flask_core import standard_response

@app.route("/api/users")
def get_users():
    return standard_response(data={"users": []})
```

### Error Classes & Handlers

```python
from pamfilico_flask_core import init_errors, NotFoundError

app = Flask(__name__)
init_errors(app)

@app.route("/api/user/<user_id>")
def get_user(user_id):
    user = find_user(user_id)
    if not user:
        raise NotFoundError("User not found", session=session)
    return standard_response(data=user)
```

### App-specific custom errors

Subclass `BaseError` (or an existing core type) in your app, then pass handlers to
`init_errors` or call `register_error_handlers` after it:

```python
from pamfilico_flask_core import BaseError, ErrorHandlerConfig, init_errors

class IntegrationError(BaseError):
    pass

init_errors(
    app,
    extra_handlers={
        IntegrationError: 502,
        # or: IntegrationError: ErrorHandlerConfig(status_code=502, log_level=logging.WARNING),
    },
    debug=app.config.get("DEBUG", False),
)
```

## Exports

- `standard_response()` — response envelope
- `init_errors(app, *, extra_handlers=None, debug=None)` — register all error handlers
- `register_error_handlers(app, handlers)` — register additional handlers later
- `ErrorHandlerConfig` — declarative status/log/message for a custom exception
- Error classes: `BaseError`, `NotFoundError`, `AuthenticationError`, `ServerError`, `DatabaseError`, `AlreadyExistsError`, `BizlogicError`, `DataNotFoundError`, `ForbidenError`, `VehicleError`, `StripeError`, `EnvironmentVariableError`


## Tests

Integration tests against a **real Flask app and a real Postgres** — no mocks:

```bash
./run-tests.sh        # docker compose up → pytest inside the api container → down
```

`tests/test_server.py` is the app; `tests/test_integration.py` calls it over HTTP
and checks, for every error class: the status and envelope, that the session's
uncommitted row was rolled back, and that the connection went back to the pool —
including when the connection was killed in Postgres first (rollback fails, close
must still happen).

## Changelog

- **1.3.0** — `init_errors(debug=...)` is per app and **off by default**: an
  unexpected error's 500 no longer carries the traceback in `dev_message` unless
  the app asked for it. (It used to default on, for every app in the process.)
- **1.2.2** — `BaseError(session=...)` closes the session even when its rollback
  fails (the pooled connection used to leak).

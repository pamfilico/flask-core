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

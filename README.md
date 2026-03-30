# @pamfilico/flask-core

Standard response envelope, error classes, pagination, and filtering for Flask APIs.

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
        raise NotFoundError("User not found")
    return standard_response(data=user)
```

### Pagination

```python
from pamfilico_flask_core import collection

@app.route("/api/vehicles")
@collection(VehicleSchema, searchable_fields=["name"], sortable_fields=["created_at"])
def list_vehicles(auth):
    return session.query(Vehicle).filter_by(user_id=auth["id"])
```

### Filtering

```python
from pamfilico_flask_core import apply_filters

query = session.query(Vehicle)
query, active_filters = apply_filters(query, Vehicle, request.args)
```

## Exports

- `standard_response()` — response envelope
- `init_errors(app)` — register all error handlers
- `collection()` — pagination/search/sort decorator
- `apply_filters()` / `parse_filters()` — query param filtering
- Error classes: `BaseError`, `NotFoundError`, `AuthenticationError`, `ServerError`, `DatabaseError`, `AlreadyExistsError`, `BizlogicError`, `DataNotFoundError`, `ForbidenError`, `VehicleError`, `StripeError`, `EnvironmentVariableError`

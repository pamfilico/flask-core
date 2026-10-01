"""A real Flask app for pamfilico-flask-core's integration tests — no mocks.

Postgres is real (docker-compose.test.yml). Routes write a row, then raise one
of the package's errors carrying the session, so the tests can see from the
OUTSIDE what the handlers did: the response envelope, whether the row was
rolled back, and whether the connection went back to the pool.
"""

import os

from flask import Flask
from marshmallow.exceptions import ValidationError
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from pamfilico_flask_core import standard_response
from pamfilico_flask_core.errors import (
    AlreadyExistsError,
    AuthenticationError,
    BaseError,
    BizlogicError,
    DataNotFoundError,
    EnvironmentVariableError,
    ErrorHandlerConfig,
    ForbidenError,
    NotFoundError,
    VehicleError,
    init_errors,
)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://test:test@localhost:5498/testdb")

#: A real pool (QueuePool): ``checkedout()`` is how a test sees a leaked connection.
engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=0, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)


Base.metadata.create_all(engine)


# --- an app's own errors, registered through extra_handlers ---------------------

class TeapotError(BaseError):
    """Registered with a plain status code."""


class ConfiguredError(BaseError):
    """Registered with an ErrorHandlerConfig (fixed message)."""


class CustomShapeError(BaseError):
    """Registered with a callable."""


app = Flask(__name__)
init_errors(
    app,
    extra_handlers={
        TeapotError: 418,
        ConfiguredError: ErrorHandlerConfig(status_code=422, ui_message="Configured message"),
        CustomShapeError: lambda e: standard_response(error=True, ui_message=f"custom: {e}", status_code=451),
    },
)

ERRORS = {
    "bizlogic": BizlogicError,
    "not_found": NotFoundError,
    "data_not_found": DataNotFoundError,
    "forbidden": ForbidenError,
    "authentication": AuthenticationError,
    "already_exists": AlreadyExistsError,
    "vehicle": VehicleError,
    "environment": EnvironmentVariableError,
    "teapot": TeapotError,
    "configured": ConfiguredError,
    "custom": CustomShapeError,
}


@app.route("/health")
def health():
    return standard_response(data={"ok": True})


@app.route("/state")
def state():
    """How many rows exist and how many pooled connections are checked out."""
    session = Session()
    count = session.query(Item).count()
    session.close()
    return standard_response(data={"items": count, "checked_out": engine.pool.checkedout()})


@app.route("/reset", methods=["POST"])
def reset():
    session = Session()
    session.execute(text("TRUNCATE items RESTART IDENTITY"))
    session.commit()
    session.close()
    return standard_response(data=None)


@app.route("/ok")
def ok():
    return standard_response(data={"hello": "world"}, ui_message="All good")


@app.route("/envelope/full")
def envelope_full():
    return standard_response(
        data=[1, 2],
        dev_message="for developers",
        pagination={"currentPage": 1, "totalPages": 1, "pageSize": 2, "totalCount": 2,
                    "nextPage": None, "previousPage": None},
        ordering={"sortBy": "id", "sortOrder": "asc"},
        filtering={"name": {"eq": "a"}},
    )


@app.route("/raise/<kind>", methods=["POST"])
def raise_with_session(kind):
    """Write a row (uncommitted), then raise ``kind`` carrying the session."""
    session = Session()
    session.add(Item(name=f"pending-{kind}"))
    session.flush()
    raise ERRORS[kind](f"{kind} happened", session=session)


@app.route("/raise-after-connection-dies", methods=["POST"])
def raise_after_connection_dies():
    """The connection is killed in Postgres before the error: rollback MUST fail,
    and the session must still be closed (connection returned to the pool)."""
    session = Session()
    session.add(Item(name="pending-dead"))
    session.flush()
    pid = session.execute(text("SELECT pg_backend_pid()")).scalar()
    killer = engine.connect()
    killer.execute(text("SELECT pg_terminate_backend(:pid)"), {"pid": pid})
    killer.close()
    raise BizlogicError("connection died", session=session)


@app.route("/unexpected")
def unexpected():
    raise RuntimeError('relation "user" has no column "secret_token"')


@app.route("/validation", methods=["POST"])
def validation():
    raise ValidationError({"name": ["Missing data for required field."], "age": ["Not a valid integer."]})


@app.route("/value")
def value():
    raise ValueError("bad value")


@app.route("/duplicate", methods=["POST"])
def duplicate():
    session = Session()
    session.add(Item(name="dup"))
    session.commit()
    session.add(Item(name="dup"))
    session.commit()   # real unique violation → IntegrityError
    return standard_response(data=None)


@app.route("/bad-cast")
def bad_cast():
    session = Session()
    session.execute(text("SELECT 'abc'::integer"))   # real DataError
    return standard_response(data=None)



# --- a second app in the same process, with debug=True ----------------------------
# Served under /debug (see the CMD in Dockerfile.test). The flag is per app: this
# one shows tracebacks, the main app above does not.

debug_app = Flask("debug_app")
init_errors(debug_app, debug=True)


@debug_app.route("/unexpected")
def debug_unexpected():
    raise RuntimeError("debug detail visible")

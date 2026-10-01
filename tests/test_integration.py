"""pamfilico-flask-core against a real Flask app and a real Postgres — no mocks.

Run with ./run-tests.sh (docker compose up, pytest, down).
"""

import os

import pytest
import requests

API_URL = os.environ.get("FLASK_CORE_TEST_API_URL", "http://localhost:5098")


def _api_available():
    try:
        return requests.get(f"{API_URL}/health", timeout=2).status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _api_available(), reason="API required — run ./run-tests.sh")


@pytest.fixture(autouse=True)
def clean_table():
    requests.post(f"{API_URL}/reset", timeout=10)


def _state():
    return requests.get(f"{API_URL}/state", timeout=10).json()["data"]


# --- the envelope ---------------------------------------------------------------

def test_the_success_envelope():
    body = requests.get(f"{API_URL}/ok").json()
    assert body == {"error": False, "ui_message": "All good", "status_code": 200,
                    "redirect_to_login": False, "data": {"hello": "world"}}


def test_optional_fields_appear_only_when_given():
    body = requests.get(f"{API_URL}/envelope/full").json()
    assert body["dev_message"] == "for developers"
    assert body["pagination"]["totalCount"] == 2
    assert body["ordering"] == {"sortBy": "id", "sortOrder": "asc"}
    assert body["filtering"] == {"name": {"eq": "a"}}
    plain = requests.get(f"{API_URL}/ok").json()
    assert not {"dev_message", "pagination", "ordering", "filtering"} & plain.keys()


# --- every error class: status, envelope, rollback, connection returned --------

ERROR_CASES = [
    ("bizlogic", 400),
    ("not_found", 404),
    ("data_not_found", 404),
    ("forbidden", 403),
    ("authentication", 401),
    ("already_exists", 409),
    ("vehicle", 400),
    ("environment", 500),
    ("teapot", 418),        # extra_handlers: int
    ("configured", 422),    # extra_handlers: ErrorHandlerConfig
    ("custom", 451),        # extra_handlers: callable
]


@pytest.mark.parametrize("kind,status", ERROR_CASES)
def test_an_error_with_a_session_answers_rolls_back_and_returns_the_connection(kind, status):
    resp = requests.post(f"{API_URL}/raise/{kind}")
    body = resp.json()
    assert resp.status_code == status, body
    assert body["error"] is True and body["status_code"] == status and body["data"] is None
    assert body["ui_message"]
    state = _state()
    assert state["items"] == 0, "the uncommitted row must be rolled back"
    assert state["checked_out"] == 0, "the connection must be back in the pool"


def test_extra_handler_messages():
    assert requests.post(f"{API_URL}/raise/configured").json()["ui_message"] == "Configured message"
    assert requests.post(f"{API_URL}/raise/custom").json()["ui_message"] == "custom: custom happened"
    assert requests.post(f"{API_URL}/raise/bizlogic").json()["ui_message"] == "bizlogic happened"


def test_a_failing_rollback_still_closes_the_session():
    """The connection is killed in Postgres, so rollback raises. Close must still
    happen — before 1.2.2 it was skipped and the pooled connection leaked."""
    resp = requests.post(f"{API_URL}/raise-after-connection-dies")
    assert resp.status_code == 400 and resp.json()["error"] is True
    assert _state()["checked_out"] == 0
    # …and the pool still serves requests afterwards
    assert requests.get(f"{API_URL}/ok").status_code == 200


def test_repeated_errors_do_not_drain_the_pool():
    """pool_size=5, no overflow: twenty errors that each leaked one connection
    would hang the app. They must not."""
    for _ in range(20):
        assert requests.post(f"{API_URL}/raise/bizlogic", timeout=10).status_code == 400
    assert _state()["checked_out"] == 0


# --- errors that are not the package's classes ----------------------------------

def test_an_unexpected_error_is_a_500_envelope_without_the_exception_text():
    resp = requests.get(f"{API_URL}/unexpected")
    body = resp.json()
    assert resp.status_code == 500
    assert body["error"] is True and body["ui_message"] == "Internal Server Error"
    assert "secret_token" not in resp.text      # no traceback by default
    assert "dev_message" not in body


def test_debug_is_per_app_and_shows_the_traceback_only_there():
    body = requests.get(f"{API_URL}/debug/unexpected").json()
    assert body["ui_message"] == "Internal Server Error"
    assert "debug detail visible" in body["dev_message"] and "Traceback" in body["dev_message"]
    # the other app in the same process is unaffected
    assert "dev_message" not in requests.get(f"{API_URL}/unexpected").json()


def test_marshmallow_validation_errors_are_one_400_message():
    resp = requests.post(f"{API_URL}/validation")
    assert resp.status_code == 400
    msg = resp.json()["ui_message"]
    assert "name: Missing data for required field." in msg and "age: Not a valid integer." in msg


def test_a_value_error_is_a_400():
    resp = requests.get(f"{API_URL}/value")
    assert resp.status_code == 400 and resp.json()["ui_message"] == "bad value"


def test_a_real_unique_violation_is_a_409():
    resp = requests.post(f"{API_URL}/duplicate")
    assert resp.status_code == 409 and resp.json()["ui_message"] == "Object already exists."


def test_a_real_bad_cast_is_a_400():
    resp = requests.get(f"{API_URL}/bad-cast")
    assert resp.status_code == 400 and resp.json()["ui_message"] == "Invalid data provided."


def test_routing_errors_keep_their_status():
    assert requests.get(f"{API_URL}/does-not-exist").status_code == 404
    assert requests.post(f"{API_URL}/ok").status_code == 405

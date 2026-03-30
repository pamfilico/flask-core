"""
Standard API response envelope.

Matches docs/api/spec.md canonical version. All Flask API responses should use
``standard_response()`` for a consistent JSON shape (error, ui_message,
status_code, redirect_to_login, data, plus opt-in dev_message, pagination,
ordering, filtering).
"""


def standard_response(
    data=None,
    ui_message="",
    dev_message="",
    status_code=200,
    error=False,
    redirect_to_login=False,
    pagination=None,
    ordering=None,
    filtering=None,
):
    """Wrap an API response in the standard envelope.

    Parameters
    ----------
    data : optional
        The response payload. Defaults to None.
    ui_message : str, optional
        User-facing message displayed in the UI (toast, alert). Defaults to "".
    dev_message : str, optional
        Developer-facing message for debugging (only included when non-empty).
        Defaults to "".
    status_code : int, optional
        HTTP status code. Defaults to 200.
    error : bool, optional
        True if the request failed, False if it succeeded. Defaults to False.
    redirect_to_login : bool, optional
        Hint for the frontend to redirect to login. Defaults to False.
    pagination : dict, optional
        Pagination metadata (only included when provided).
        Keys: currentPage, totalPages, pageSize, totalCount, nextPage, previousPage.
    ordering : dict, optional
        Ordering metadata (only included when provided).
        Keys: sortBy, sortOrder.
    filtering : dict, optional
        Active filter metadata (only included when provided).

    Returns
    -------
    tuple[dict, int]
        (response_dict, status_code) for Flask to jsonify and return.
    """
    response = {
        "error": error,
        "ui_message": ui_message,
        "status_code": status_code,
        "redirect_to_login": redirect_to_login,
        "data": data,
    }

    if dev_message:
        response["dev_message"] = dev_message

    if pagination is not None:
        response["pagination"] = pagination

    if ordering is not None:
        response["ordering"] = ordering

    if filtering is not None:
        response["filtering"] = filtering

    return response, status_code

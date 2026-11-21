"""Running queries against the flight database."""
from validator import FIELD_NAMES, parse_datetime

STRING_KEYS={"flight_id", "origin", "destination"}
DATETIME_KEYS={"departure_datetime", "arrival_datetime"}
NUMBER_KEYS = {"price", "min_price"}
ALLOWED_KEYS = STRING_KEYS | DATETIME_KEYS | NUMBER_KEYS | {"sort_by", "order", "limit"}


def _is_number(value) -> bool:
    # bool is a subclass of int, but booleans are not numbers here.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_valid(query) -> bool:
    if not isinstance(query, dict):
        return False
    for key, value in query.items():
        if key not in ALLOWED_KEYS:
            return False
        if key in STRING_KEYS and not isinstance(value, str):
            return False
        if key in DATETIME_KEYS and parse_datetime(value) is None:
            return False
        if key in NUMBER_KEYS and not _is_number(value):
            return False
        if key == "sort_by" and not (isinstance(value, str) and value in FIELD_NAMES):
            return False
        if key == "order" and value not in ("asc", "desc"):
            return False
        if key == "limit" and not (isinstance(value, int) and not isinstance(value, bool) and value >= 0):
            return False
    if "order" in query and "sort_by" not in query:
        return False
    return True


def _matches(flight: dict, query: dict) -> bool:
    for key in STRING_KEYS:
        if key in query and flight[key] != query[key]:
            return False
    # The fixed YYYY-MM-DD HH:MM format sorts correctly as a string.
    if "departure_datetime" in query and flight["departure_datetime"] < query["departure_datetime"]:
        return False
    if "arrival_datetime" in query and flight["arrival_datetime"] > query["arrival_datetime"]:
        return False
    if "price" in query and not flight["price"] <= query["price"]:
        return False
    if "min_price" in query and not flight["price"] >= query["min_price"]:
        return False
    return True


def run_query(db: list[dict], query: dict) -> dict:
    """Return one response entry for one query object.

    Valid query:   {"query": query, "matches": [...]}
    Invalid query: {"query": query, "error": "INVALID_QUERY", "matches": []}
    """
    if not _is_valid(query):
        return {"query": query, "error": "INVALID_QUERY", "matches": []}

    matches = [flight for flight in db if _matches(flight, query)]
    if "sort_by" in query:
        key = query["sort_by"]
        # sorted() is stable in both directions, so ties keep database order.
        matches = sorted(matches, key=lambda f: f[key], reverse=query.get("order") == "desc")
    if "limit" in query:
        matches = matches[: query["limit"]]
    return {"query": query, "matches": matches}


def run_queries(db: list[dict], queries: dict | list) -> list[dict]:
    """Accept one query object or a list of them; always return a list."""
    if isinstance(queries, dict):
        queries = [queries]
    return [run_query(db, q) for q in queries]
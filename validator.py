"""Row validation: airport list loading, single-row checks, record building."""
import math
import re
from datetime import datetime

FIELD_NAMES=[
    "flight_id",
    "origin",
    "destination",
    "departure_datetime",
    "arrival_datetime",
    "price",
]

FLIGHT_ID_RE=re.compile(r"[A-Za-z0-9]{2,8}")
AIRPORT_RE=re.compile(r"[A-Z]{3}")
DATETIME_RE=re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}")
DATETIME_FORMAT="%Y-%m-%d %H:%M"

def load_airports(path: str)->set[str]:
    """Read an airport list file and return the set of codes.
    One code per line. Strip whitespace; skip blank lines and lines
    starting with '#'.
    """
    codes=set()
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            code=line.strip()
            if not code or code.startswith("#"):
                continue
            codes.add(code)
    return codes

def parse_datetime(value: str)->datetime | None:
    """Return the datetime for an exact 'YYYY-MM-DD HH:MM' string, else None."""
    if not isinstance(value, str) or not DATETIME_RE.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, DATETIME_FORMAT)
    except ValueError:
        return None

def _valid_airport(code: str, airports: set[str])->bool:
    return bool(AIRPORT_RE.fullmatch(code)) and code in airports

def validate_row(fields: list[str], airports: set[str])->str | None:
    """Check one CSV row (fields as returned by csv.reader, not yet stripped).
    Return None if the row is valid, otherwise the error code of the
    FIRST failing check (checks 1-11 in the specification, in order).
    Does not check for duplicates.
    """
    if len(fields)!=len(FIELD_NAMES):
        return "WRONG_FIELD_COUNT"
    flight_id, origin, destination, dep, arr, price=(f.strip() for f in fields)
    if any(f=="" for f in (flight_id, origin, destination, dep, arr, price)):
        return "MISSING_FIELD"
    if not FLIGHT_ID_RE.fullmatch(flight_id):
        return "INVALID_FLIGHT_ID"
    if not _valid_airport(origin, airports):
        return "INVALID_ORIGIN"
    if not _valid_airport(destination, airports):
        return "INVALID_DESTINATION"
    if origin==destination:
        return "SAME_ORIGIN_DESTINATION"
    dep_dt=parse_datetime(dep)
    if dep_dt is None:
        return "INVALID_DEPARTURE"
    arr_dt=parse_datetime(arr)
    if arr_dt is None:
        return "INVALID_ARRIVAL"
    if arr_dt<=dep_dt:
        return "ARRIVAL_NOT_AFTER_DEPARTURE"
    try:
        value=float(price)
    except ValueError:
        return "INVALID_PRICE"
    if not math.isfinite(value):
        return "INVALID_PRICE"
    if value<=0:
        return "NON_POSITIVE_PRICE"
    return None

def to_record(fields: list[str]) -> dict:
    """Turn a valid row into a flight record dictionary.
    Keys: flight_id, origin, destination, departure_datetime,
    arrival_datetime (stripped strings) and price (float).
    """
    stripped=[f.strip() for f in fields]
    record=dict(zip(FIELD_NAMES[:5], stripped[:5]))
    record["price"]=float(stripped[5])
    return record
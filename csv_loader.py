"""Reading CSV files into flight records and error messages."""
import csv
import os

from validator import to_record, validate_row

def _physical_lines(path: str):
    """Yield (line_number, text) for every physical line, without line endings.
    newline="" keeps the file's own line endings, so both \\n and \\r\\n
    end a line and line numbers match the file exactly.
    """
    with open(path, encoding="utf-8-sig", newline="") as f:
        for number, line in enumerate(f, start=1):
            yield number, line.rstrip("\r\n")

def parse_files(paths: list[str], airports: set[str]) -> tuple[list[dict], list[str]]:
    """Process the CSV files in the order given.
    Return (records, errors):
      records - valid flight records, in input order
      errors  - one message per invalid row, in input order, formatted as
                "<file name>:<line number>: <ERROR_CODE> | <free text>"
                (base file name only, no timestamp or level, no newline)
    Also performs the DUPLICATE_FLIGHT check across all the files.
    Does not write any files and does not log anything itself.
    """
    records: list[dict]=[]
    errors: list[str]=[]
    seen: set[tuple[str, str]]=set()
    for path in paths:
        name=os.path.basename(path)
        for number, text in _physical_lines(path):
            if number==1:  
                continue
            stripped=text.strip()
            if not stripped or stripped.startswith("#"):
                continue
            fields=next(csv.reader([text]), [])
            code=validate_row(fields, airports)
            if code is None:
                record=to_record(fields)
                key=(record["flight_id"], record["departure_datetime"])
                if key in seen:
                    code="DUPLICATE_FLIGHT"
                else:
                    seen.add(key)
                    records.append(record)
            if code is not None:
                errors.append(f"{name}:{number}: {code} | {text}")
    return records, errors
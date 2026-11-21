import argparse
import json
import logging
import os
import sys
from datetime import datetime

from csv_loader import parse_files
from query import run_queries
from validator import load_airports

STUDENT_ID="251ADB240"
FIRST_NAME="Sarah"
LAST_NAME="Fatima"

LOGGER_NAME="flight_parser"

class RuntimeProblem(Exception):
    """An expected problem that ends the run with exit code 1."""

def build_parser()->argparse.ArgumentParser:
    parser=argparse.ArgumentParser(
        prog="flight_parser.py",
        description="Validate flight schedule CSV files, build a JSON database and run queries.",
    )
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument("-i", metavar="FILE", help="parse a single CSV file")
    source.add_argument("-d", metavar="FOLDER", help="parse every .csv file in a folder")
    source.add_argument("-j", metavar="FILE", help="load an existing JSON database")
    parser.add_argument("-a", metavar="FILE", help="airport list file (required with -i and -d)")
    parser.add_argument("-o", metavar="FILE", help="output path for the JSON database (default: db.json)")
    parser.add_argument("-q", metavar="FILE", help="JSON file with queries to run")
    parser.add_argument("-r", metavar="FOLDER", help="folder for the response file (default: current directory)")
    return parser

def parse_args(argv: list[str] | None)->argparse.Namespace:
    parser=build_parser()
    args=parser.parse_args(argv)
    if(args.i is not None or args.d is not None) and args.a is None:
        parser.error("-a is required with -i and -d")
    if args.j is not None and args.o is not None:
        parser.error("-o cannot be used with -j")
    return args

def read_json(path: str, what: str):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeProblem(f"{what} not found: {path}")
    except json.JSONDecodeError as e:
        raise RuntimeProblem(f"{what} is not valid JSON: {path} ({e})")
    except (OSError, UnicodeDecodeError) as e:
        raise RuntimeProblem(f"cannot read {what}{path}:e}")

def write_json(path: str, data, what: str)->None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
    except OSError as e:
        raise RuntimeProblem(f"cannot write {what}{path}:{e}")

def csv_paths(args: argparse.Namespace)->list[str]:
    if args.i is not None:
        if not os.path.isfile(args.i):
            raise RuntimeProblem(f"CSV file not found: {args.i}")
        return [args.i]
    folder=args.d
    if not os.path.isdir(folder):
        raise RuntimeProblem(f"folder not found: {folder}")
    try:
        names=os.listdir(folder)
    except OSError as e:
        raise RuntimeProblem(f"cannot read folder {folder}: {e}")
    paths=[
        os.path.join(folder, name)
        for name in sorted(names)
        if name.endswith(".csv") and os.path.isfile(os.path.join(folder, name))
    ]
    if not paths:
        raise RuntimeProblem(f"no .csv files found in folder: {folder}")
    return paths

def load_database(path: str) -> list[dict]:
    db=read_json(path, "JSON database")
    if not isinstance(db, list) or not all(isinstance(r, dict) for r in db):
        raise RuntimeProblem(f"JSON database must be an array of objects: {path}")
    return db

def load_queries(path: str):
    queries=read_json(path, "query file")
    if isinstance(queries, dict):
        return queries
    if isinstance(queries, list) and all(isinstance(q, dict) for q in queries):
        return queries
    raise RuntimeProblem(f"query file must contain a query object or an array of query objects: {path}")

def response_file_name()->str:
    stamp=datetime.now().strftime("%Y%m%d_%H%M")
    return f"response_{STUDENT_ID}_{FIRST_NAME}_{LAST_NAME}_{stamp}.json"

def run(args: argparse.Namespace, logger: logging.Logger, handlers: list)->int:
    if args.j is not None:
        db=load_database(args.j)
        print(f"Loaded {len(db)} flights from {args.j}")
    else:
        try:
            airports=load_airports(args.a)
        except FileNotFoundError:
            raise RuntimeProblem(f"airport list not found: {args.a}")
        except (OSError, UnicodeDecodeError) as e:
            raise RuntimeProblem(f"cannot read airport list {args.a}: {e}")
        paths=csv_paths(args)
        try:
            db, errors=parse_files(paths, airports)
        except (OSError, UnicodeDecodeError) as e:
            raise RuntimeProblem(f"cannot read CSV file: {e}")
        db_path=args.o if args.o is not None else "db.json"
        write_json(db_path, db, "database")
        log_path=os.path.join(os.path.dirname(os.path.abspath(db_path)), "errors.log")
        try:
            handler=logging.FileHandler(log_path, mode="w", encoding="utf-8")
        except OSError as e:
            raise RuntimeProblem(f"cannot write log file {log_path}: {e}")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
        handlers.append(handler)
        logger.info("Parsed %d file(s): %d valid, %d invalid", len(paths), len(db), len(errors))
        for message in errors:
            logger.warning(message)
        print(f"Parsed {len(paths)} file(s): {len(db)} valid rows, {len(errors)} invalid rows")
        print(f"Database written to {db_path}, errors to {log_path}")
    if args.q is not None:
        queries=load_queries(args.q)
        responses=run_queries(db, queries)
        out_dir=args.r if args.r is not None else "."
        out_path=os.path.join(out_dir, response_file_name())
        write_json(out_path, responses, "response file")
        print(f"Ran {len(responses)} quer{'y' if len(responses)==1 else 'ies'}, response written to {out_path}")
    return 0

def main(argv: list[str] | None=None)->int:
    """Run the whole program and return the exit code (0, 1 or 2).
    argv is the argument list without the program name.
    None means use sys.argv[1:] (argparse does this for you).
    Do not call sys.exit() inside main(); return the code instead.
    """
    try:
        args=parse_args(argv)
    except SystemExit as e:  
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 2)
    logger=logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    handlers: list[logging.Handler] = []
    try:
        return run(args, logger, handlers)
    except RuntimeProblem as e:
        if handlers:
            logger.error("%s", e)
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        for handler in handlers:
            logger.removeHandler(handler)
            handler.close()

if __name__ == "__main__":
    sys.exit(main())
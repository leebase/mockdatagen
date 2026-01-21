from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mockdatagen.assertions import run_assertions
from mockdatagen.exceptions import SpecValidationError
from mockdatagen.generate import generate_sqlite, write_er_diagram
from mockdatagen.reporting import write_json_report
from mockdatagen.spec import load_spec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mockdatagen")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run generator commands")
    run_subparsers = run_parser.add_subparsers(dest="run_command", required=True)

    validate_parser = run_subparsers.add_parser("validate", help="Validate a spec")
    validate_parser.add_argument("--spec", required=True)

    generate_parser = run_subparsers.add_parser("generate", help="Generate SQLite")
    generate_parser.add_argument("--spec", required=True)
    generate_parser.add_argument("--scenario", default="baseline")
    generate_parser.add_argument("--out", required=True)
    generate_parser.add_argument("--er-diagram", default="reports/er_diagram.mmd")

    assert_parser = run_subparsers.add_parser("assert", help="Run assertions")
    assert_parser.add_argument("--spec", required=True)
    assert_parser.add_argument("--scenario", required=True)
    assert_parser.add_argument("--db", required=True)

    args = parser.parse_args(argv)

    try:
        if args.command == "run":
            if args.run_command == "validate":
                return _handle_validate(args.spec)
            if args.run_command == "generate":
                return _handle_generate(args.spec, args.out, args.er_diagram)
            if args.run_command == "assert":
                return _handle_assert(args.spec, args.db, args.scenario)
    except SpecValidationError as exc:
        print(f"Validation error: {exc}")
        return 1

    print("Unknown command")
    return 1


def _handle_validate(spec_path: str) -> int:
    spec = load_spec(spec_path)
    report = {
        "status": "ok",
        "project": spec.project.name,
        "tables": [table.name for table in spec.tables],
    }
    write_json_report("reports/validate.json", report)
    print("Spec validation passed")
    return 0


def _handle_generate(spec_path: str, output_path: str, er_diagram_path: str) -> int:
    spec = load_spec(spec_path)
    result = generate_sqlite(spec, output_path)
    diagram_path = write_er_diagram(spec, er_diagram_path)
    report = {
        "status": "ok",
        "db": str(Path(result.db_path)) if result else None,
        "tables": result.table_counts,
        "er_diagram": str(diagram_path),
    }
    write_json_report("reports/generate.json", report)
    print(f"Generated SQLite db at {output_path}")
    return 0


def _handle_assert(spec_path: str, db_path: str, scenario: str) -> int:
    spec = load_spec(spec_path)
    result = run_assertions(spec, db_path, scenario)
    report = {
        "status": "ok" if result.passed else "failed",
        "scenario": scenario,
        "failures": result.failures,
        "metrics": result.metrics,
    }
    write_json_report("reports/assertions.json", report)
    if not result.passed:
        print("Assertions failed")
        return 1
    print("Assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

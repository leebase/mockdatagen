from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sqlite3

from mockdatagen.spec import AssertionSpec, ScenarioSpec, Spec


@dataclass(frozen=True)
class AssertionResult:
    passed: bool
    failures: list[str]
    metrics: dict[str, Any]


def run_assertions(spec: Spec, db_path: str | Path, scenario: str) -> AssertionResult:
    path = Path(db_path)
    if not path.exists():
        return AssertionResult(
            passed=False,
            failures=[f"Missing database at {path}"],
            metrics={},
        )

    scenario_spec = _find_scenario(spec, scenario)
    if scenario_spec is None:
        return AssertionResult(
            passed=False,
            failures=[f"Scenario '{scenario}' not found in spec"],
            metrics={},
        )

    if not scenario_spec.assertions:
        return AssertionResult(passed=True, failures=[], metrics={"assertions": []})

    failures: list[str] = []
    metrics: dict[str, Any] = {"assertions": []}
    with sqlite3.connect(path) as connection:
        cursor = connection.cursor()
        for assertion in scenario_spec.assertions:
            result = _evaluate_assertion(cursor, assertion)
            metrics["assertions"].append(result)
            if not result["passed"]:
                failures.append(result["message"])

    return AssertionResult(
        passed=not failures,
        failures=failures,
        metrics=metrics,
    )


def _find_scenario(spec: Spec, scenario: str) -> ScenarioSpec | None:
    for candidate in spec.scenarios:
        if candidate.name == scenario:
            return candidate
    return None


def _evaluate_assertion(
    cursor: sqlite3.Cursor,
    assertion: AssertionSpec,
) -> dict[str, Any]:
    cursor.execute(assertion.sql)
    row = cursor.fetchone()
    if row is None:
        return {
            "name": assertion.name,
            "passed": False,
            "expected": assertion.expect,
            "actual": None,
            "message": f"Assertion '{assertion.name}' returned no rows",
        }
    actual = row[0]
    passed = actual == assertion.expect
    message = (
        f"Assertion '{assertion.name}' expected {assertion.expect} but got {actual}"
        if not passed
        else f"Assertion '{assertion.name}' passed"
    )
    return {
        "name": assertion.name,
        "passed": passed,
        "expected": assertion.expect,
        "actual": actual,
        "message": message,
    }

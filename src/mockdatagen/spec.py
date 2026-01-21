from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

from mockdatagen.exceptions import SpecValidationError


@dataclass(frozen=True)
class ProjectSpec:
    name: str
    version: str
    seed: int
    locale: str


@dataclass(frozen=True)
class RunSpec:
    batch_size: int
    validate: bool
    assert_enabled: bool


@dataclass(frozen=True)
class FieldSpec:
    name: str
    field_type: str
    nullable: bool
    generator: dict[str, Any]


@dataclass(frozen=True)
class ForeignKeySpec:
    fields: list[str]
    ref_table: str
    ref_fields: list[str]


@dataclass(frozen=True)
class AssetDictionarySpec:
    name: str
    path: Path
    columns: list[str]
    weight_column: str | None


@dataclass(frozen=True)
class AssertionSpec:
    name: str
    sql: str
    expect: Any


@dataclass(frozen=True)
class TableSpec:
    name: str
    row_count: int
    fields: list[FieldSpec]
    primary_key: list[str]
    foreign_keys: list[ForeignKeySpec]


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    assertions: list[AssertionSpec]


@dataclass(frozen=True)
class Spec:
    project: ProjectSpec
    run: RunSpec
    tables: list[TableSpec]
    assets: list[AssetDictionarySpec]
    scenarios: list[ScenarioSpec]


def load_spec(path: str | Path) -> Spec:
    spec_path = Path(path)
    if not spec_path.exists():
        raise SpecValidationError(f"Spec not found: {spec_path}")
    with spec_path.open("rb") as handle:
        data = tomllib.load(handle)
    return validate_spec(data, base_path=spec_path.parent)


def validate_spec(data: dict[str, Any], base_path: Path | None = None) -> Spec:
    project = data.get("project")
    if not isinstance(project, dict):
        raise SpecValidationError("Missing [project] section")

    project_spec = ProjectSpec(
        name=_require_str(project, "name"),
        version=_require_str(project, "version"),
        seed=_require_int(project, "seed"),
        locale=_require_str(project, "locale"),
    )

    run = data.get("run")
    if not isinstance(run, dict):
        raise SpecValidationError("Missing [run] section")

    run_spec = RunSpec(
        batch_size=_require_int(run, "batch_size"),
        validate=_require_bool(run, "validate"),
        assert_enabled=_require_bool(run, "assert"),
    )

    schema = data.get("schema")
    if not isinstance(schema, dict):
        raise SpecValidationError("Missing [schema] section")

    tables_raw = schema.get("tables")
    if not isinstance(tables_raw, list) or not tables_raw:
        raise SpecValidationError("Missing [[schema.tables]] entries")

    tables = []
    for table in tables_raw:
        tables.append(_parse_table(table))

    assets = _parse_assets(data, base_path)
    scenarios = _parse_scenarios(data)

    return Spec(
        project=project_spec,
        run=run_spec,
        tables=tables,
        assets=assets,
        scenarios=scenarios,
    )


def _parse_table(table: dict[str, Any]) -> TableSpec:
    name = _require_str(table, "name")
    row_count = _require_int(table, "row_count")

    fields_raw = table.get("fields")
    if not isinstance(fields_raw, list) or not fields_raw:
        raise SpecValidationError(f"Table '{name}' is missing fields")

    fields = []
    for field in fields_raw:
        fields.append(_parse_field(name, field))

    primary_key_block = table.get("primary_key", {})
    if not isinstance(primary_key_block, dict):
        raise SpecValidationError(f"Table '{name}' has invalid primary_key")

    pk_fields = primary_key_block.get("fields", [])
    if not isinstance(pk_fields, list):
        raise SpecValidationError(f"Table '{name}' has invalid primary_key.fields")

    foreign_keys = _parse_foreign_keys(table, name)

    return TableSpec(
        name=name,
        row_count=row_count,
        fields=fields,
        primary_key=[str(field) for field in pk_fields],
        foreign_keys=foreign_keys,
    )


def _parse_foreign_keys(table: dict[str, Any], table_name: str) -> list[ForeignKeySpec]:
    foreign_keys_raw = table.get("foreign_keys", [])
    if not isinstance(foreign_keys_raw, list):
        raise SpecValidationError(f"Table '{table_name}' has invalid foreign_keys")

    parsed: list[ForeignKeySpec] = []
    for foreign_key in foreign_keys_raw:
        if not isinstance(foreign_key, dict):
            raise SpecValidationError(
                f"Table '{table_name}' has invalid foreign_keys entry"
            )
        fields = _require_str_list(foreign_key, "fields")
        ref_table = _require_str(foreign_key, "ref_table")
        ref_fields = _require_str_list(foreign_key, "ref_fields")
        parsed.append(
            ForeignKeySpec(fields=fields, ref_table=ref_table, ref_fields=ref_fields)
        )
    return parsed


def _parse_field(table_name: str, field: dict[str, Any]) -> FieldSpec:
    name = _require_str(field, "name")
    field_type = _require_str(field, "type")
    nullable = _require_bool(field, "nullable")

    generator = field.get("generator")
    if not isinstance(generator, dict):
        raise SpecValidationError(f"Field '{table_name}.{name}' missing generator")

    kind = generator.get("kind")
    if kind not in {"sequence", "constant"}:
        raise SpecValidationError(
            f"Field '{table_name}.{name}' has unsupported generator '{kind}'"
        )

    return FieldSpec(
        name=name,
        field_type=field_type,
        nullable=nullable,
        generator=generator,
    )


def _parse_assets(data: dict[str, Any], base_path: Path | None) -> list[AssetDictionarySpec]:
    assets = data.get("assets")
    if assets is None:
        return []
    if not isinstance(assets, dict):
        raise SpecValidationError("Invalid [assets] section")

    dictionaries = assets.get("dictionary", [])
    if not isinstance(dictionaries, list):
        raise SpecValidationError("Invalid [[assets.dictionary]] entries")

    parsed: list[AssetDictionarySpec] = []
    for entry in dictionaries:
        if not isinstance(entry, dict):
            raise SpecValidationError("Invalid [[assets.dictionary]] entry")
        name = _require_str(entry, "name")
        path_value = _require_str(entry, "path")
        path = Path(path_value)
        if not path.is_absolute() and base_path is not None:
            path = base_path / path
        if not path.exists():
            raise SpecValidationError(
                f"Missing asset file '{path_value}' for dictionary '{name}'"
            )
        columns = entry.get("columns", [])
        if not isinstance(columns, list):
            raise SpecValidationError(
                f"Dictionary '{name}' has invalid columns list"
            )
        parsed_columns = [str(column) for column in columns]
        weight_column = entry.get("weight_column")
        if weight_column is None and "weights" in entry:
            weight_column = entry.get("weights")
        if weight_column is not None and not isinstance(weight_column, str):
            raise SpecValidationError(
                f"Dictionary '{name}' has invalid weight column"
            )
        parsed.append(
            AssetDictionarySpec(
                name=name,
                path=path,
                columns=parsed_columns,
                weight_column=weight_column,
            )
        )
    return parsed


def _parse_scenarios(data: dict[str, Any]) -> list[ScenarioSpec]:
    scenarios = data.get("scenarios")
    if scenarios is None:
        return []
    if not isinstance(scenarios, list):
        raise SpecValidationError("Invalid [[scenarios]] entries")

    parsed: list[ScenarioSpec] = []
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise SpecValidationError("Invalid [[scenarios]] entry")
        name = _require_str(scenario, "name")
        assertions_raw = scenario.get("assertions", [])
        if not isinstance(assertions_raw, list):
            raise SpecValidationError(f"Scenario '{name}' has invalid assertions")
        assertions = []
        for assertion in assertions_raw:
            if not isinstance(assertion, dict):
                raise SpecValidationError(
                    f"Scenario '{name}' has invalid assertion entry"
                )
            assertion_name = _require_str(assertion, "name")
            sql = _require_str(assertion, "sql")
            if "expect" not in assertion:
                raise SpecValidationError(
                    f"Scenario '{name}' assertion '{assertion_name}' missing expect"
                )
            expect = assertion["expect"]
            if not isinstance(expect, (str, int, float, bool)):
                raise SpecValidationError(
                    f"Scenario '{name}' assertion '{assertion_name}' has invalid expect"
                )
            assertions.append(
                AssertionSpec(name=assertion_name, sql=sql, expect=expect)
            )
        parsed.append(ScenarioSpec(name=name, assertions=assertions))
    return parsed


def _require_str(values: dict[str, Any], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise SpecValidationError(f"Missing or invalid '{key}'")
    return value


def _require_int(values: dict[str, Any], key: str) -> int:
    value = values.get(key)
    if not isinstance(value, int):
        raise SpecValidationError(f"Missing or invalid '{key}'")
    return value


def _require_bool(values: dict[str, Any], key: str) -> bool:
    value = values.get(key)
    if not isinstance(value, bool):
        raise SpecValidationError(f"Missing or invalid '{key}'")
    return value


def _require_str_list(values: dict[str, Any], key: str) -> list[str]:
    value = values.get(key)
    if not isinstance(value, list) or not value:
        raise SpecValidationError(f"Missing or invalid '{key}'")
    parsed = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise SpecValidationError(f"Missing or invalid '{key}'")
        parsed.append(item)
    return parsed

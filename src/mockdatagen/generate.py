from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from mockdatagen.exceptions import SpecValidationError
from mockdatagen.spec import FieldSpec, ForeignKeySpec, Spec, TableSpec


SQLITE_TYPE_MAP = {
    "int": "INTEGER",
    "text": "TEXT",
}


@dataclass(frozen=True)
class GenerateResult:
    db_path: Path
    table_counts: dict[str, int]


def generate_sqlite(spec: Spec, output_path: str | Path) -> GenerateResult:
    db_path = Path(output_path)
    if db_path.exists():
        db_path.unlink()

    connection = sqlite3.connect(db_path)
    try:
        _create_schema(connection, spec.tables)
        table_counts = _insert_data(connection, spec)
    finally:
        connection.close()

    return GenerateResult(db_path=db_path, table_counts=table_counts)


def write_er_diagram(spec: Spec, output_path: str | Path) -> Path:
    diagram_path = Path(output_path)
    diagram_path.parent.mkdir(parents=True, exist_ok=True)
    diagram_path.write_text(_render_er_diagram(spec))
    return diagram_path


def _create_schema(connection: sqlite3.Connection, tables: list[TableSpec]) -> None:
    cursor = connection.cursor()
    for table in tables:
        column_defs = []
        for field in table.fields:
            column_defs.append(_column_definition(table, field))

        if table.primary_key:
            pk_clause = ", ".join(table.primary_key)
            column_defs.append(f"PRIMARY KEY ({pk_clause})")

        ddl = f"CREATE TABLE {table.name} ({', '.join(column_defs)})"
        cursor.execute(ddl)
    connection.commit()


def _column_definition(table: TableSpec, field: FieldSpec) -> str:
    if field.field_type not in SQLITE_TYPE_MAP:
        raise SpecValidationError(
            f"Field '{table.name}.{field.name}' has unsupported type '{field.field_type}'"
        )
    column_type = SQLITE_TYPE_MAP[field.field_type]
    nullable = "" if field.nullable else " NOT NULL"
    return f"{field.name} {column_type}{nullable}"


def _render_er_diagram(spec: Spec) -> str:
    lines = ["erDiagram"]

    for table in spec.tables:
        lines.append(f"  {table.name} {{")
        pk_fields = set(table.primary_key)
        fk_fields = _collect_fk_fields(table.foreign_keys)
        for field in table.fields:
            field_type = SQLITE_TYPE_MAP.get(field.field_type, field.field_type)
            tags = []
            if field.name in pk_fields:
                tags.append("PK")
            if field.name in fk_fields:
                tags.append("FK")
            tag_suffix = f" {' '.join(tags)}" if tags else ""
            lines.append(f"    {field_type} {field.name}{tag_suffix}")
        lines.append("  }")

    for table in spec.tables:
        for foreign_key in table.foreign_keys:
            label = ",".join(foreign_key.fields)
            lines.append(
                _render_fk_relationship(table.name, foreign_key, label)
            )

    return "\n".join(lines) + "\n"


def _insert_data(connection: sqlite3.Connection, spec: Spec) -> dict[str, int]:
    cursor = connection.cursor()
    table_counts: dict[str, int] = {}
    batch_size = spec.run.batch_size

    for table in spec.tables:
        rows = _generate_rows(table)
        columns = [field.name for field in table.fields]
        placeholders = ", ".join(["?"] * len(columns))
        insert_sql = (
            f"INSERT INTO {table.name} ({', '.join(columns)}) VALUES ({placeholders})"
        )

        for batch in _batch_rows(rows, batch_size):
            cursor.executemany(insert_sql, batch)
        table_counts[table.name] = table.row_count

    connection.commit()
    return table_counts


def _generate_rows(table: TableSpec) -> Iterable[tuple[Any, ...]]:
    for index in range(table.row_count):
        values = []
        for field in table.fields:
            values.append(_generate_value(field, index))
        yield tuple(values)


def _generate_value(field: FieldSpec, index: int) -> Any:
    generator = field.generator
    kind = generator.get("kind")
    if kind == "sequence":
        start = generator.get("start", 1)
        if not isinstance(start, int):
            raise SpecValidationError(
                f"Sequence generator for '{field.name}' has invalid start"
            )
        return start + index
    if kind == "constant":
        return generator.get("value")
    raise SpecValidationError(f"Unsupported generator kind '{kind}'")


def _batch_rows(rows: Iterable[tuple[Any, ...]], batch_size: int) -> Iterable[list[Any]]:
    batch: list[Any] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _collect_fk_fields(foreign_keys: list[ForeignKeySpec]) -> set[str]:
    fields: set[str] = set()
    for foreign_key in foreign_keys:
        fields.update(foreign_key.fields)
    return fields


def _render_fk_relationship(
    child_table: str, foreign_key: ForeignKeySpec, label: str
) -> str:
    return (
        f"  {foreign_key.ref_table} ||--o{{ {child_table} : \"{label}\""
    )

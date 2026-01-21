from __future__ import annotations

import sqlite3

from mockdatagen.generate import generate_sqlite
from mockdatagen.spec import load_spec


def test_spec_toml_generates_hello_table(tmp_path):
    spec = load_spec("spec.toml")
    output_path = tmp_path / "out.db"
    generate_sqlite(spec, output_path)

    with sqlite3.connect(output_path) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT id, message FROM hello ORDER BY id")
        rows = cursor.fetchall()

    assert rows == [(1, "Hello, World"), (2, "Hello, World"), (3, "Hello, World")]

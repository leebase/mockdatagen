from __future__ import annotations

from mockdatagen.cli import main
from mockdatagen.generate import generate_sqlite
from mockdatagen.spec import load_spec


def test_validate_exits_nonzero_on_bad_spec(tmp_path):
    missing_path = tmp_path / "missing.toml"
    result = main(["run", "validate", "--spec", str(missing_path)])
    assert result == 1


def test_validate_fails_on_missing_asset(tmp_path):
    spec_path = tmp_path / "spec.toml"
    spec_path.write_text(
        """
[project]
name = "assets"
version = "0.1.0"
seed = 1
locale = "en_US"

[run]
batch_size = 10
validate = true
assert = false

[[assets.dictionary]]
name = "cities"
path = "missing.csv"

[[schema.tables]]
name = "hello"
row_count = 1

[[schema.tables.fields]]
name = "id"
type = "int"
nullable = false
generator = { kind = "sequence", start = 1 }

[[schema.tables.fields]]
name = "message"
type = "text"
nullable = false
generator = { kind = "constant", value = "Hello" }

[schema.tables.primary_key]
fields = ["id"]
""".lstrip()
    )

    result = main(["run", "validate", "--spec", str(spec_path)])
    assert result == 1


def test_assert_fails_on_bad_scenario(tmp_path):
    spec_path = tmp_path / "spec.toml"
    spec_path.write_text(
        """
[project]
name = "assertions"
version = "0.1.0"
seed = 1
locale = "en_US"

[run]
batch_size = 10
validate = true
assert = true

[[schema.tables]]
name = "hello"
row_count = 1

[[schema.tables.fields]]
name = "id"
type = "int"
nullable = false
generator = { kind = "sequence", start = 1 }

[[schema.tables.fields]]
name = "message"
type = "text"
nullable = false
generator = { kind = "constant", value = "Hello" }

[schema.tables.primary_key]
fields = ["id"]

[[scenarios]]
name = "baseline"

[[scenarios.assertions]]
name = "wrong_count"
sql = "SELECT COUNT(*) FROM hello"
expect = 2
""".lstrip()
    )

    spec = load_spec(spec_path)
    db_path = tmp_path / "out.db"
    generate_sqlite(spec, db_path)

    result = main(
        [
            "run",
            "assert",
            "--spec",
            str(spec_path),
            "--scenario",
            "baseline",
            "--db",
            str(db_path),
        ]
    )
    assert result == 1

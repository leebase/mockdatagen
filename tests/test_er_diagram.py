from __future__ import annotations

from mockdatagen.cli import main


def test_generate_writes_er_diagram(tmp_path):
    output_path = tmp_path / "out.db"
    diagram_path = tmp_path / "schema.mmd"

    result = main(
        [
            "run",
            "generate",
            "--spec",
            "spec.toml",
            "--scenario",
            "baseline",
            "--out",
            str(output_path),
            "--er-diagram",
            str(diagram_path),
        ]
    )

    assert result == 0
    diagram = diagram_path.read_text()
    assert "erDiagram" in diagram
    assert "hello" in diagram

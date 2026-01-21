# Mockdatagen

Minimal, deterministic mock data generator driven by TOML specs. SQLite is the
first output target.

## CLI

Install editable:

```
python -m pip install -e .
```

Generate SQLite:

```
mockdatagen run generate --spec spec.toml --scenario baseline --out out.db
```

Generate SQLite with ER diagram output:

```
mockdatagen run generate --spec spec.toml --scenario baseline --out out.db --er-diagram reports/er_diagram.mmd
```

Validate a spec:

```
mockdatagen run validate --spec spec.toml
```

Run assertions:

```
mockdatagen run assert --spec spec.toml --scenario baseline --db out.db
```

## LLM-to-TOML workflow

See `docs/HowToCreateSpecsWithLLM.md` for a prompt template and end-to-end flow.

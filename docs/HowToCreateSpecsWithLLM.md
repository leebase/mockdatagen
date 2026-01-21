# How to Create TOML Specs with an LLM

This guide shows a simple workflow for turning a story into a valid TOML spec and
running `mockdatagen`.

## 1) Prompt the LLM

Use a prompt like this and paste your story where indicated:

```
You are writing a TOML spec for the mockdatagen generator.

Requirements:
- Output valid TOML only, no prose.
- Use the exact schema sections shown below.
- Include primary keys and generators for every field.
- Keep it minimal: only what is required for the story.

Schema skeleton:
[project]
name = "<string>"
version = "0.1.0"
seed = 42
locale = "en_US"

[run]
batch_size = 100
validate = true
assert = false

[[schema.tables]]
name = "<table_name>"
row_count = <int>

[[schema.tables.fields]]
name = "<field_name>"
type = "int" | "text"
nullable = false
generator = { kind = "sequence" | "constant", ... }

[schema.tables.primary_key]
fields = ["<field_name>"]

Story:
<PASTE STORY HERE>
```

## 2) Save the TOML

Save the output as `spec.toml` in the repo root.

## 3) Validate and generate

```
mockdatagen run validate --spec spec.toml
mockdatagen run generate --spec spec.toml --scenario baseline --out out.db
```

## 4) Assert (optional)

If your spec includes scenario assertions:

```
mockdatagen run assert --spec spec.toml --scenario baseline --db out.db
```

## Example: Hello World

```
[project]
name = "hello_world"
version = "0.1.0"
seed = 42
locale = "en_US"

[run]
batch_size = 100
validate = true
assert = false

[[schema.tables]]
name = "hello"
row_count = 3

[[schema.tables.fields]]
name = "id"
type = "int"
nullable = false
generator = { kind = "sequence", start = 1 }

[[schema.tables.fields]]
name = "message"
type = "text"
nullable = false
generator = { kind = "constant", value = "Hello, World" }

[schema.tables.primary_key]
fields = ["id"]
```

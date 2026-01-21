# technicalDesign.md — TOML Mock Data Generator (SQLite MVP)

## 1. Architecture Overview
### Inputs
- `spec.toml` (schema + rules + scenarios + assertions)
- `assets/` (CSV/JSON dictionaries and mappings)
- CLI args: scenario, output path, scale/row overrides

### Outputs
- SQLite database file (`.db`)
- Reports:
  - `reports/plan.json`
  - `reports/validate.json`
  - `reports/assertions.json`
  - `reports/summary.md`

### Modules
- `spec/` — TOML parsing + schema validation + canonicalization
- `compiler/` — compile spec to an execution plan (DAG + schedules + mutations)
- `assets/` — dictionary registry loader + weighted sampling support
- `engine/` — deterministic generator runtime (streaming)
- `sqlite/` — schema DDL + insert batching + PRAGMA tuning
- `scenarios/` — inject/mutate/time-series shaping
- `verify/` — assertions + constraints + summary stats
- `cli.py` — command entry point

## 2. Determinism Strategy
Hard requirement: identical build inputs -> identical outputs.

### 2.1 RNG Partitioning
Use a deterministic RNG seed derivation:
- project seed
- scenario seed override
- per-table seed = hash(project_seed, scenario, table_name)
- per-row/per-field = hash(per-table seed, row_index, field_name)
This ensures parallelism does not change results.

### 2.2 Stable Sampling for Injection
For selecting 0.5% fraud rows:
- compute a stable score per row (hash-based uniform [0,1))
- choose rows where score < 0.005 (or pick exact count via stable sort)
This avoids “random drift” across runs.

## 3. Spec (TOML) Formalization
### 3.1 Spec sections (MVP)
- `[project]` name, version, seed, locale
- `[run]` batch_size, output flags, validate/assert on/off
- `[[schema.tables]]` name, row_count
- `[[schema.tables.fields]]` name, type, nullable, generator
- `[schema.tables.primary_key]` fields, generator
- `[[schema.tables.foreign_keys]]` fields, ref_table, ref_fields
- `[[assets.dictionary]]` name, mode, path, columns, weights
- `[[facts]]` (optional MVP) name/table + schedule (needed for time-series)
- `[[scenarios]]` name, seed, date_range
  - `inject` (rate + label field + selection)
  - `mutations` (where + set generators)
  - `calendar_overrides` (month + volume_multiplier)
  - `assertions` (expr and/or SQL)
- `[[rules.assertions]]` global validations (non-scenario)

### 3.2 Validation
Implement `pydantic` (or equivalent) models to validate:
- required fields present
- types correct
- references resolve: tables, fields, assets, FK targets
- generator config valid

### 3.3 Canonicalization
Provide `format_spec`:
- stable ordering of sections
- stable ordering of tables/fields
- expands shorthand into explicit blocks
This makes LLM authoring more reliable (feed canonical TOML back to LLM as exemplars).

## 4. Generation Plan (Compiler)
The compiler produces:
- Table dependency DAG from FK graph
- Generation order (toposort)
- Insert strategy (parents first)
- Row counts (global scale * table row_count)
- Fact schedules (for time-series)
- Scenario plan:
  - injections (table, count/rate, selection)
  - mutations (predicates + generator overrides)
  - calendar overrides (time window multipliers)

## 5. SQLite Implementation Details
### 5.1 Schema creation
- Create tables with types mapped to SQLite affinities
- PK constraints where possible
- Optional FK enforcement:
  - `PRAGMA foreign_keys=ON` during verification
  - may be OFF during bulk load for speed, then ON + validate in verifier

### 5.2 Bulk insert
- use `executemany` batches
- wrap in explicit transactions
- tune pragmas (MVP defaults):
  - `journal_mode=WAL`
  - `synchronous=NORMAL`
  - `temp_store=MEMORY`
  - `cache_size` tuned

## 6. Scenario Engine (MVP primitives)
### 6.1 Injection
Goal: mark X% rows, mutate signals.
Algorithm:
1. Build base dataset
2. Determine injected row indices deterministically
3. Apply label changes and mutations to selected rows
4. Optional: burst subpattern (adds extra rows keyed by entity)

### 6.2 Time-series shaping
Approach: generate month-by-month:
- expected volume = base_monthly * (1+r)^m
- apply calendar overrides (e.g., June multiplier 0.8)
- allocate to cohorts via weights (optional MVP+)

## 7. Verifier / Tests
### 7.1 Verifier rule: generators cannot self-green
- Keep verifiers under `verify/` with strict ownership and stable interfaces.

### 7.2 Tests
- Unit:
  - spec validation
  - deterministic hashing RNG
  - weighted dictionary sampling
  - injection selection stability
  - calendar volume calculation
- Integration:
  - generate small DB -> verify row counts, PK uniqueness
  - scenario: fraud rate within tolerance
  - scenario: June dip vs trend expected
- Performance sanity:
  - generate 1M rows within reasonable time envelope (not strict, but tracked)

### 7.3 Reports
- JSON for machines, Markdown/text for humans.

## 8. OpenCode + Ralph Wiggum Loop Mechanics
### 8.1 Repo structure
- `docs/` for productRequirements.md and technicalDesign.md
- `specs/` sample TOMLs
- `assets/` example dictionaries
- `src/` generator engine
- `verify/` verifiers + test harness
- `progress/` loop logs

### 8.2 Loop contract
Each loop must:
- implement a bounded story set
- add/extend tests
- update progress log
- never modify verifier logic except via explicit “verifier change” story

### 8.3 NEEDS_CAPABILITY mechanism
If spec uses unsupported generator/scenario feature:
- engine emits `NEEDS_CAPABILITY:<capability>` and exits non-zero
- PRD adds a story for that capability next loop

# productRequirements.md — TOML-Driven Mock Data Generator (SQLite MVP)

## 1. Purpose
Build a deterministic, TOML-driven mock/synthetic data generator that:
- Generates realistic datasets **at any configured scale** without using an LLM at runtime.
- Supports **dimension dictionaries** (provided lists) and **realistic-sounding synthetic dictionaries** (generated once, then cached as assets).
- Supports **scenario-driven facts** (e.g., fraud at 0.5%, MoM growth with June dip).
- Outputs to **SQLite** first (portable MVP), with a path to additional targets later.

## 2. Problem Statement
Existing generators often excel at:
- Quick UI-based fake data (good for small demos)
- FK-aware table population
But they struggle with:
- Spec-as-code workflows (CI/repro/versioning)
- Scenario “story” generation with measurable targets
- Domain dictionaries as governed dependencies
- Deterministic, offline scaling without token costs

## 3. Users / Personas
### P1: Data Engineer / Architect (Primary)
Needs reproducible datasets for dev/test/CI and environment hydration.

### P2: Analytics / ML Engineer
Needs datasets with controlled patterns (fraud rate, anomalies, seasonality) for modeling and detection.

### P3: QA / Automation Engineer
Needs test data builds that can run reliably and validate “the story” with assertions.

## 4. Goals (MVP)
### G1: Spec-as-code
- TOML spec defines: tables, fields, types, keys, FKs, generators, volumes, scenarios, assertions.

### G2: Deterministic Offline Generation
- Given identical inputs (spec + assets + seed + engine version) -> identical outputs.
- Scale to millions of rows (bounded by local hardware) with streaming inserts.
- Obviously items that are randomnly generated need not be deterministic, We want to be able to run this to generate a data set at any time without costing llm tokens

### G3: SQLite Output
- Generate schema + data into a single `.db` file.
- Optionally emit CSV/Parquet later, but SQLite is MVP.
- Also generate mermaid.js er diagram file

### G4: Scenarios that Tell Stories
Must support at least:
- Fraud injection at `0.5%` with mutated signals (amount, channel, velocity).
- Sales with MoM growth trend and a June dip (20% below expected), optionally cohort-specific.
- the generator doesn't need to respond to stories, but llms given a story need to be able to create toml's that inform the generation of data to tell stories.  In other words, data that isn't just random.

### G5: Validations / Assertions
- Constraint validation: PK uniqueness, FK integrity (as applicable), nullability.
- Scenario assertions: fraud rate within tolerance; June dip measured vs trend expectation.
- Column level assertions: data type, range, distribution, etc.

## 5. Non-Goals (MVP)
- Production masking/de-identification platform
- GUI (CLI only)
- Multi-database targets (beyond SQLite)
- Full ML-based synthesizers (SDV-style) — can be future

## 6. Core Concepts
### 6.1 Spec (TOML)
- Human + LLM writable
- Validated via strict schema validation
- Canonical formatting command to normalize structure

### 6.2 Assets (Domain Dictionaries)
- Files under `assets/` (CSV/JSON)
- Referenced in TOML by name + version tag
- Can be:
  - Provided (real domain list)
  - Synthetic (realistic-sounding list generated once, then frozen)

### 6.3 Scenarios
Scenario = deterministic transformation layer applied during generation:
- Injection: mark X% rows as fraud and mutate correlated fields
- Time-series shaping: monthly volumes follow trend, with an outlier month multiplier
- Cohorts: apply effects only to subset (e.g., region/product line)

### 6.4 Assertions
- Simple expression checks and/or SQL checks executed against generated SQLite DB.

## 7. Success Criteria (MVP Definition of Done)
- `opencode run generate --spec spec.toml --scenario baseline --out out.db` produces correct DB
- `... --scenario fraud_0_5pct` yields:
  - `is_fraud` rate 0.5% ± tolerance
  - fraud rows show mutated distributions
- `... --scenario june_dip` yields:
  - monthly totals trending upward
  - June at ~20% below expected trend
- Validations produce a machine-readable report (JSON) + human summary (markdown/text)

## 8. UX (CLI)
Required commands:
- `validate` (spec + assets)
- `plan` (show generation order, volumes, required assets)
- `generate` (build SQLite)
- `assert` (run scenario checks; also invoked by generate if enabled)
- `summarize` (row counts, null rates, top values, monthly totals, fraud rate)

## 9. Ralph Wiggum Loop Requirements (OpenCode)
- Each loop must end with:
  - passing verifier (tests + assertions)
  - updated progress log
  - PRD story status updated to DONE
- Strict trust boundary:
  - generators cannot edit verifier scripts
  - verifiers are stable and reviewed
- Capability request mechanism:
  - If engine encounters unsupported spec feature, it emits `NEEDS_CAPABILITY: <cap>` with guidance.

## 10. Risks / Mitigations
- **LLM-generated TOML errors** -> strict validation + canonicalizer + error feedback loop.
- **Performance** -> chunked inserts, PRAGMA tuning, streaming generation.
- **Determinism with parallelism** -> stable RNG partitioning per table/field or per-row hashing.
- **Scenario complexity creep** -> keep scenario primitives minimal (inject, mutate, time-series volume, cohort filter).

## 11. Future Roadmap (Post-MVP)
- Targets: Postgres/Snowflake/Parquet
- UI: minimal web UI for spec editing + preview
- Advanced scenario primitives (bursts, cascades)
- Asset derivation from DB / reference datasets
- ML synth add-on module

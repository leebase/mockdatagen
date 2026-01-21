# Agent Guidelines for mockdatagen

## Repository Snapshot (Current)
- This repo currently contains product/docs files and a helper script under `scripts/`.
- Source code directories like `src/`, `tests/`, `verify/`, and `docs/` are described in the PRD/technical design but are not present yet.
- There is no `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md` in this repo at the time of writing.

## High-Level Intent (From PRD/Tech Design)
- Build a TOML-driven mock data generator for SQLite.
- Determinism here means the generator runs as pure Python code (no LLM at runtime).
- Focus on strict spec validation and scenario-driven facts.

## Build / Lint / Test Commands
### Current reality
- No Makefile, package manager, or test harness is present yet.
- The only runnable script today is `scripts/ralph/ralph.sh`.

### Expected commands once code exists (Python-first)
- Install dev deps: `python -m pip install -e .[dev]` or `uv sync`
- Format (if adopted): `ruff format` or `black .`
- Lint (required): `ruff check .`
- Compile sanity (if needed): `python -m py_compile path/to/file.py`
- Run tests: `pytest -q`
- Run a single test file: `pytest tests/path/to/test_file.py -q`
- Run a single test case: `pytest tests/path/to/test_file.py -k test_case_name -q`
- Run verifier tests (planned): `pytest verify -q`

### CLI/run commands (planned)
- Validate spec: `opencode run validate --spec spec.toml`
- Plan generation: `opencode run plan --spec spec.toml`
- Generate SQLite: `opencode run generate --spec spec.toml --scenario baseline --out out.db`
- Assertions: `opencode run assert --spec spec.toml --scenario fraud_0_5pct`
- Summarize: `opencode run summarize --db out.db`

## Local Helper Script
- Ralph loop runner: `bash scripts/ralph/ralph.sh [--tool amp|claude] [max_iterations]`
- The script archives previous runs when the branch name changes.
- It expects `scripts/ralph/prd.json` and `scripts/ralph/progress.txt` (created as needed).

## Code Style and Conventions (Target State)
### Imports
- Prefer absolute imports from project root package (no relative imports across modules).
- Group imports: standard library, third-party, local.
- One import per line for clarity; no wildcard imports.
- Keep module boundaries clean (no cross-layer imports).

### Formatting
- Python: 4 spaces, no tabs.
- Keep line length reasonable (88-100 chars if using Black/Ruff).
- Use trailing commas in multi-line literals for clean diffs.
- Use double quotes for strings unless a single quote avoids escaping.

### Naming
- Python: `snake_case` for variables/functions, `PascalCase` for types/classes.
- Constants: `UPPER_SNAKE_CASE`.
- Filenames: `snake_case.py` or `kebab-case` for scripts.
- CLI flags: use `kebab-case`.

### Types and Data Models
- Use type hints throughout; no untyped public functions.
- Prefer `pydantic` models for spec validation (per technical design).
- Keep model validation errors actionable and specific.
- Avoid `Any` except at boundaries (IO, parsing, external data).

### Errors and Logging
- Fail fast for invalid specs; surface clear, user-facing errors.
- Raise domain-specific errors (e.g., `SpecValidationError`).
- Do not swallow exceptions; log context and rethrow or exit non-zero.
- Failures should be reproducible for a given input spec and code version.

### Determinism (Runtime Constraint)
- Deterministic means generation is pure Python code (no LLM calls at runtime).
- Using randomness is allowed; do not imply or promise stable outputs across runs.
- Keep generator behavior transparent and debuggable via logs/reports.

### Testing
- Tests mirror source paths: `src/foo/bar.py` -> `tests/foo/test_bar.py`.
- Cover generator behavior and edge cases (nulls, FK constraints, missing assets).
- Favor small, focused unit tests for generators and validators.
- Integration tests should generate tiny DBs and verify row counts and invariants.
- Each story should include: compile/lint checks, a minimal runtime smoke run, and at least one unit test when logic changes.

### SQLite + IO
- Use explicit transactions for bulk inserts.
- Separate schema creation, data generation, and verification phases.
- Keep PRAGMA settings centralized and test-configurable.

### Spec and Assets
- TOML spec is the source of truth; never invent fields not in spec.
- Canonicalize spec output with a stable ordering.
- Assets are immutable inputs; treat missing assets as errors.

### LLM-to-Spec Contract
- LLMs only author TOML; runtime generation must be pure Python.
- Validation errors must be specific enough for automatic repair.
- Provide canonical examples as references for prompt context.
- Keep spec versioning explicit to avoid silent behavior shifts.
- Scenarios should include assertions to confirm the story.

### CLI Behavior
- All commands should return non-zero on failure.
- Commands should emit machine-readable JSON reports when relevant.
- Provide human-readable summaries with short, structured output.

### Scenario and Assertions
- Scenario behavior must be implemented in pure Python (no LLM calls).
- Assertions should be separate from generator code and produce explicit metrics.
- Never modify verifiers unless a verifier-change story explicitly allows it.

## Documentation Expectations
- Update `docs/` and `specs/` when new features or capabilities are added.
- Keep examples minimal and canonical; avoid ambiguous or partial specs.
- Document new CLI flags and defaults in README or dedicated docs.

## Repo Hygiene
- Do not commit secrets; use `.env` and `.env.example` when needed.
- Keep changes scoped; avoid unrelated refactors.
- If files are missing for a change, ask before creating broad scaffolding.

## If You Need to Add Tooling
- Prefer adding a Makefile with `setup`, `lint`, `test`, `run` targets.
- Use `pyproject.toml` for dependency management when possible.
- Align formatter and linter choices (Black/Ruff or Ruff-only).

## Notes for Agentic Changes
- This repository is early-stage; confirm assumptions before adding new structure.
- When uncertain about tooling, propose a brief plan and ask for confirmation.

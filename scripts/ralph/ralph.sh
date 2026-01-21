#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop
# Usage: ./ralph.sh [--tool opencode|amp|claude] [--max-iterations N]

set -e

export PYTHONPATH="${PYTHONPATH:-}:src"

# Parse arguments
TOOL="opencode"  # Default to OpenCode
MAX_ITERATIONS=5

while [[ $# -gt 0 ]]; do
  case $1 in
    --tool)
      TOOL="$2"
      shift 2
      ;;
    --tool=*)
      TOOL="${1#*=}"
      shift
      ;;
    --max-iterations)
      MAX_ITERATIONS="$2"
      shift 2
      ;;
    --max-iterations=*)
      MAX_ITERATIONS="${1#*=}"
      shift
      ;;
    *)
      # Ignore unknown arguments for now
      shift
      ;;
  esac
 done


# Validate tool choice
if [[ "$TOOL" != "opencode" && "$TOOL" != "amp" && "$TOOL" != "claude" ]]; then
  echo "Error: Invalid tool '$TOOL'. Must be 'opencode', 'amp', or 'claude'."
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$(dirname "$SCRIPT_DIR")/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

venv_python() {
  if [[ -x ".venv/bin/python" ]]; then
    echo ".venv/bin/python"
    return 0
  fi
  echo "python3"
}

venv_exec() {
  local tool="$1"
  if [[ -x ".venv/bin/$tool" ]]; then
    echo ".venv/bin/$tool"
    return 0
  fi
  echo "$tool"
}

bootstrap_tools() {
  if ! command_exists python3; then
    echo "Error: python3 is required for bootstrap"
    return 1
  fi

  local python_bin
  python_bin=$(venv_python)

  if [[ "$python_bin" == "python3" && ! -d ".venv" ]]; then
    echo "Creating local venv for tooling..."
    python3 -m venv .venv
    python_bin=$(venv_python)
  fi

  echo "Bootstrapping lint/test tooling..."
  "$python_bin" -m pip install --upgrade pip >/dev/null 2>&1 || true
  "$python_bin" -m pip install ruff pytest >/dev/null 2>&1
}

run_lint_check() {
  local ruff_bin
  ruff_bin=$(venv_exec "ruff")
  echo "Running lint check (ruff)..."
  "$ruff_bin" check .
}

run_compile_check() {
  local python_bin
  python_bin=$(venv_python)
  local py_files
  py_files=$(git ls-files "*.py")
  if [[ -z "$py_files" ]]; then
    echo "No Python files to compile"
    return 0
  fi
  echo "Running Python compile sanity..."
  "$python_bin" -m py_compile $py_files
}

run_runtime_smoke() {
  local python_bin
  python_bin=$(venv_python)
  if [[ ! -f "spec.toml" ]]; then
    echo "Missing spec.toml for runtime smoke run"
    return 1
  fi
  echo "Running runtime smoke check..."
  PYTHONPATH=src "$python_bin" -m mockdatagen.cli run validate --spec spec.toml
}

run_unit_tests() {
  local pytest_bin
  pytest_bin=$(venv_exec "pytest")
  if [[ ! -d "tests" && ! -d "verify" ]]; then
    echo "Missing tests/ or verify/ for unit tests"
    return 1
  fi
  echo "Running unit tests..."
  "$pytest_bin" -q
}

get_current_story_id() {
  if [[ ! -f "$PRD_FILE" ]]; then
    return 0
  fi
  jq -r '[.loops[].stories[] | select(.status!="DONE")][0].id // empty' "$PRD_FILE" 2>/dev/null || true
}

run_story_checks() {
  if ! bootstrap_tools; then
    return 1
  fi
  run_lint_check && run_compile_check && run_runtime_smoke && run_unit_tests
}

log_progress_entry() {
  local status="$1"
  local story_id="$2"
  local message="$3"
  {
    echo "$(date +%Y-%m-%dT%H:%M:%S%z) | ${status} | ${story_id} | ${message}"
  } >> "$PROGRESS_FILE"
}

enforce_story_gates() {
  local story_id="$1"
  if [[ -z "$story_id" ]]; then
    return 0
  fi
  echo "Running story gates for ${story_id}..."
  if run_story_checks; then
    log_progress_entry "PASS" "$story_id" "lint/compile/smoke/tests"
    return 0
  fi
  log_progress_entry "FAIL" "$story_id" "lint/compile/smoke/tests"
  echo "Story gates failed for ${story_id}. Exiting."
  exit 1
}

commit_if_clean() {
  local iteration="$1"
  if ! command_exists git; then
    echo "Git not available; skipping commit"
    return 0
  fi

  if git status --porcelain | grep -q .; then
    git add -A
    git commit -m "chore: ralph iteration ${iteration}"
  else
    echo "No changes to commit"
  fi
}

# Archive previous run if branch changed
if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")
  
  if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
    # Archive the previous run
    DATE=$(date +%Y-%m-%d)
    # Strip "ralph/" prefix from branch name for folder
    FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^ralph/||')
    ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"
    
    echo "Archiving previous run: $LAST_BRANCH"
    mkdir -p "$ARCHIVE_FOLDER"
    [ -f "$PRD_FILE" ] && cp "$PRD_FILE" "$ARCHIVE_FOLDER/"
    [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/"
    echo "   Archived to: $ARCHIVE_FOLDER"
    
    # Reset progress file for new run
    echo "# Ralph Progress Log" > "$PROGRESS_FILE"
    echo "Started: $(date)" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
  fi
fi

# Track current branch
if [ -f "$PRD_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  if [ -n "$CURRENT_BRANCH" ]; then
    echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
  fi
fi

# Initialize progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
  echo "# Ralph Progress Log" > "$PROGRESS_FILE"
  echo "Started: $(date)" >> "$PROGRESS_FILE"
  echo "---" >> "$PROGRESS_FILE"
fi

echo "Starting Ralph - Tool: $TOOL - Max iterations: $MAX_ITERATIONS"

CURRENT_STORY_ID=$(get_current_story_id)
LAST_STORY_ID="$CURRENT_STORY_ID"
ITERATION=1

while true; do
  CURRENT_STORY_ID=$(get_current_story_id)
  if [[ -n "$CURRENT_STORY_ID" && "$CURRENT_STORY_ID" != "$LAST_STORY_ID" ]]; then
    enforce_story_gates "$LAST_STORY_ID"
    ITERATION=1
    LAST_STORY_ID="$CURRENT_STORY_ID"
  fi

  if [[ $ITERATION -gt $MAX_ITERATIONS ]]; then
    break
  fi
  echo ""
  echo "==============================================================="
  echo "  Ralph Iteration $ITERATION of $MAX_ITERATIONS ($TOOL)"
  echo "==============================================================="

  # Run the selected tool with the ralph prompt
  if [[ "$TOOL" == "opencode" ]]; then
    if [[ ! -f "$PRD_FILE" ]]; then
      echo "Error: PRD file not found at $PRD_FILE"
      exit 1
    fi
    PROMPT_BODY=$(cat "$PRD_FILE")
    FULL_PROMPT="You are Ralph. Implement the next TODO story from the attached PRD JSON.

Required steps:
1) Read the PRD JSON and select the first story whose status is not DONE.
2) Implement that single story only. Do not touch verifiers unless the story explicitly allows it.
3) Run the story's verification plan and ensure all three gates pass:
   - lint/compile checks
   - runtime smoke run
   - unit tests (at least one when logic changes)
4) Only if all gates pass, update the story status to DONE in prd.json.
5) Append a short progress note to scripts/ralph/progress.txt.
6) If all stories are DONE, output exactly: <promise>COMPLETE</promise>

Keep changes scoped. Use existing repo conventions. The PRD JSON is provided below.

<prd>\n${PROMPT_BODY}\n</prd>"
    OUTPUT=$(opencode run "$FULL_PROMPT" 2>&1 | tee /dev/stderr) || true
  elif [[ "$TOOL" == "amp" ]]; then
    OUTPUT=$(cat "$SCRIPT_DIR/prompt.md" | amp --dangerously-allow-all 2>&1 | tee /dev/stderr) || true
  else
    # Claude Code: use --dangerously-skip-permissions for autonomous operation, --print for output
    OUTPUT=$(claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | tee /dev/stderr) || true
  fi
  
  # Check for completion signal
  if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
    echo ""
    echo "Ralph completed all tasks!"
    echo "Completed at iteration $ITERATION of $MAX_ITERATIONS"

    enforce_story_gates "$LAST_STORY_ID"
    echo "Story checks passed; committing changes"
    commit_if_clean "$ITERATION"

    exit 0
  fi
  
  echo "Iteration $ITERATION complete. Continuing..."
  sleep 2
  ITERATION=$((ITERATION + 1))
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Check $PROGRESS_FILE for status."
exit 1

# QueueForge: Engineering Guidelines

Rules for any AI assistant (and human) changing this repository. Adapted from the fresher-radar
guidelines, with QueueForge-specific changes. QueueForge is a PostgreSQL-backed job queue
(FastAPI + SQLAlchemy + Alembic), built as a learning project: the owner must be able to explain
every line in an SDE interview.

---

## 1. Zero Unsolicited Changes (Surgical Precision)

- **Strict scope:** modify only the files, functions and lines the request needs.
- **Preserve existing code and comments:** never delete, rewrite or "clean up" unrelated comments,
  docstrings, formatting or working code.
- **No drive-by refactoring:** don't modernize, re-architect or optimize outside the task unless asked.
- **No unrequested additions:** no extra endpoints, models, migrations, Docker changes or libraries.
- **Match existing style:** naming, indentation, structure, comment tone.
- **Orphan cleanup:** remove only imports, variables or functions that *your own* change made unused.

---

## 2. Mandatory Real Test Cases (No Placeholders)

- Every new function, feature or bugfix comes with real tests in `backend/tests/`.
- No trivial assertions (`assert True`, `assert x is not None` without checking properties).
- Each change covers:
  1. **Happy path:** valid input, precise expected output.
  2. **Edge cases:** empty queue, boundary values, missing optional fields.
  3. **Failure modes:** invalid config, database unreachable, `pytest.raises(...)`.
- **Deterministic and isolated:** tests never depend on the developer's real database contents or on
  `.env` secrets. Use a throwaway database or a fake, and override settings explicitly.
- Run after every change, from `backend/` with the venv active: `pytest tests/`. All tests must pass.

---

## 3. Coding Standards

### Architecture
- **Separation of concerns:** config in `app/core/`, the HTTP layer in `app/main.py` and later routers.
  Models, sessions and queue logic get their own modules when they arrive. Don't grow `main.py`.
- **Config-driven:** no URLs, ports, credentials or thresholds hard-coded in logic.
  - `.env` at the repo root holds this machine's settings and secrets. It is never committed.
    `.env.example` documents the required keys.
  - Settings are read through `app.core.config.settings` (pydantic-settings), never `os.environ` directly.
- **Schema changes go through Alembic migrations**, never `create_all()`.
- **Queue correctness:** claim jobs inside a transaction with `SELECT ... FOR UPDATE SKIP LOCKED`.
  A job must never be lost or handed to two workers.

### Python
- **Type hints** on every function signature and return type (`X | None` style).
- **Error handling:** never use bare `except:`, and never swallow an error. Catch specific exceptions.
  A broad `except Exception` is allowed only at a worker boundary, where it must record and log the
  failure, then continue.
- **Logging over printing:** use `logging`. No `print` in application code.
- **Fail fast:** required config has no default, so a missing value stops startup with a clear error.

---

## 4. Project Rules

### Secrets
- **Never read, print, copy or paste `.env`**, in code, commands, logs or answers. If a value is needed,
  ask the user, or refer to `.env.example`.
- Confirm with `git status` that `.env` is not staged before any commit is suggested.

### Interview-prep process
- Before creating each file: 2-3 sentences on its purpose.
- After creating each file: explain the key lines in plain language.
- Record every decision in `docs/DECISIONS.md`: append a new entry, never silently rewrite an old one.
  If a decision is reversed, mark the old one `Superseded by Dx`.
- Finish a step with a short checklist for the user to verify, plus 1-2 understanding-check questions.

### Data and git
- Work on the current branch. The repo uses a branch per chore (e.g. `chore/dev-environment`).
  Don't create branches unless asked.
- **The user runs `git add`, `git commit` and `git push` themselves.** Never commit or push. When asked
  for a commit message, give the text only.
- `.env`, `.venv/`, `__pycache__/` and database volumes are never committed.

### Environment
- The repo lives in WSL (Ubuntu) at `~/queueforge`. Run project commands inside WSL bash
  (`wsl.exe -d Ubuntu -- bash ...`), not in PowerShell. The Windows side sees it as
  `\\wsl.localhost\Ubuntu\home\aditi\queueforge`.
- For anything longer than one line, write a script file and run it. Don't pass nested quotes
  through PowerShell.
- Postgres runs through Docker Compose on **host port 5433** (container 5432). The port in
  `DATABASE_URL` must match.
- Python 3.14 venv at `backend/.venv`. Dependencies are pinned in `backend/requirements.txt`.
  Don't add a library without asking.

### Commands
Run from `backend/` with the venv active (`source .venv/bin/activate`):
```
uvicorn app.main:app --reload     # dev server on :8000
curl localhost:8000/health        # expect {"status":"ok","database":"connected"}
pytest tests/                     # full test suite
```
From the repo root: `docker compose up -d` starts Postgres.
Always run uvicorn from `backend/`, not the repo root, or `app` won't import.

---

## 5. Execution Workflow

1. **Analyze:** read the relevant files, tests and `docs/DECISIONS.md` before touching code.
2. **Implement:** minimal, focused edits.
3. **Test:** add or update concrete tests for the change.
4. **Verify:** run `pytest tests/` and, for API changes, the dev server plus `/health`.
5. **Log:** add a `docs/DECISIONS.md` entry for any decision made.

## Response Rules

- Be concise, with no preamble. Explanations of *why* are welcome here (interview prep), but keep
  them plain and short.
- Show only changed lines or sections; don't echo whole files.
- If something fails, show the full error, explain it, and propose the fix before applying it.


# QueueForge: Development Tracker

Last updated: 2026-11-09. Tick items as they are finished. Read this at the start of every session.

**Current position: Phase 1, last task: commit the schema review through a PR. Phase 2 has not started.**

---

## Phase 1: Planning and environment setup (est. 2-3 days)
**Objectives:** fix the architecture, set up tools, GitHub and the first running skeleton, agree the schema.
**Technologies:** WSL2 Ubuntu, Python 3.14, Docker Compose, PostgreSQL 16, Git/GitHub, FastAPI, pydantic-settings.
**Expected output:** a working `/health` endpoint backed by PostgreSQL, a pushed branch merged to `main`, a reviewed schema.

- [x] Architecture and task lifecycle decided
- [x] WSL2, Python 3.14.4, Docker/Compose, Git, VS Code (WSL) set up
- [x] GitHub repo `queueforge`, SSH auth working, first commit on `main`
- [x] venv at `backend/.venv`, dependencies installed, `requirements.txt` generated
- [x] `.env` / `.env.example` at repo root (port 5433, `postgresql+psycopg`)
- [x] `docker-compose.yml`: PostgreSQL 16, container `queueforge-db`, healthcheck
- [x] Step 7: `app/core/config.py` and `app/main.py` with `GET /health` (verified 2026-11-09: HTTP 200, `{"status":"ok","database":"connected"}`, docs title "QueueForge")
- [x] `docs/DECISIONS.md` created (D1-D13)
- [x] `CLAUDE.md` created
- [x] Step 7 committed and pushed on `chore/dev-environment` (commit `0a80f1b`)
- [x] Open a pull request `chore/dev-environment` -> `main` (PR #1)
- [x] Merge the PR (squash, commit `7cdece0`), update local `main`
- [x] Review the schema column by column (`jobs`, `job_attempts`, `workers`, `job_dependencies`) and log decisions (D14-D28 in `docs/DECISIONS.md`)
- [ ] Commit the schema decisions and tracker on a `docs/schema-review` branch, PR, merge
- [ ] Node.js: not needed until Phase 5

Not yet done or untested: no automated tests exist (`backend/tests/` is empty); `/health` returns a 500, not a 503, when the DB is down.

---

## Phase 2: Backend foundation (est. 4 days)
**Objectives:** models, migrations, submit/retrieve APIs, API tests.
**Technologies:** SQLAlchemy, Alembic, FastAPI, pydantic, pytest, httpx.
**Expected output:** `POST /jobs` and `GET /jobs`, `GET /jobs/{id}` working against migrated tables, with tests.

- [ ] `db/` module: engine and session dependency
- [ ] SQLAlchemy models for the four tables
- [ ] Alembic initialised, first migration applied
- [ ] Pydantic schemas (API shape, separate from models)
- [ ] `POST /jobs` with idempotency key handling
- [ ] `GET /jobs/{id}` and list endpoint with filters
- [ ] Services layer (thin routes)
- [ ] pytest setup with isolated test database; API tests

## Phase 3: Core queue (est. 5 days)
**Technologies:** Python worker process, PostgreSQL `FOR UPDATE SKIP LOCKED`.
- [ ] Worker process skeleton and handler registry
- [ ] Atomic claim query
- [ ] Execute handler, record attempt, update status
- [ ] Run multiple workers; verify no double claim

## Phase 4: Reliability and advanced features (est. 8-10 days)
- [ ] Retries with exponential backoff and jitter
- [ ] Idempotency (keys and idempotent handlers)
- [ ] Priority scheduling
- [ ] Worker heartbeat and lease extension
- [ ] Crash recovery (expired leases)
- [ ] Dead-letter state
- [ ] Delayed/scheduled jobs
- [ ] Job dependencies (`blocked` -> `queued`)

## Phase 5: Frontend dashboard (est. 5-6 days)
**Technologies:** React (JavaScript), Node.js (install first).
- [ ] Install Node.js; scaffold `frontend/`
- [ ] Submit task form, task list, job status
- [ ] Completed/failed jobs, worker activity, execution history, stats (polling)

## Phase 6: Testing and performance (est. 4 days)
- [ ] Unit and integration tests
- [ ] Concurrent execution and worker-crash simulation
- [ ] Duplicate-execution tests
- [ ] Throughput and latency benchmarks; fix bottlenecks

## Phase 7: Deployment and documentation (est. 3 days)
**Technologies:** Docker, GitHub Actions, Prometheus, Grafana.
- [ ] Dockerfile and full Compose stack
- [ ] CI with GitHub Actions
- [ ] Prometheus `/metrics` and Grafana dashboard
- [ ] Deploy
- [ ] Architecture diagrams, README, demo video, resume bullets

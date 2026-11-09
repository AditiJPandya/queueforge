# QueueForge: Decision Log

A running record of every engineering decision, written so I can explain it in an interview.
Each entry: **Decision / Context / Alternatives / Why / Trade-offs / Interview question.**
Add a new entry (never silently rewrite an old one) whenever a decision is made. If a decision is reversed, mark it `Superseded by Dx`.

| ID  | Decision                                      | Step | Status   |
|-----|-----------------------------------------------|------|----------|
| D1  | FastAPI as the web framework                  | Setup | Accepted |
| D2  | PostgreSQL as the database and the queue store | Setup | Accepted |
| D3  | SQLAlchemy (ORM/Core) + Alembic migrations    | Setup | Accepted |
| D4  | psycopg v3 driver                             | Setup | Accepted |
| D5  | Docker Compose for Postgres, host port 5433   | Setup | Accepted |
| D6  | Secrets in a gitignored `.env`                | Setup | Accepted |
| D7  | `.env` at repo root, located via `pathlib`    | 7    | Accepted |
| D8  | `extra="ignore"` in Settings                  | 7    | Accepted |
| D9  | `database_url` is required, no default        | 7    | Accepted |
| D10 | One shared module-level `settings` object     | 7    | Accepted |
| D11 | Synchronous SQLAlchemy engine for now         | 7    | Accepted (revisit) |
| D12 | `/health` runs `SELECT 1`                     | 7    | Accepted |
| D13 | Branch-per-chore git workflow, manual commits | Setup | Accepted |

---

## D1: FastAPI as the web framework
- **Context:** Need an HTTP API to submit jobs and inspect queue state.
- **Alternatives:** Flask, Django (+DRF).
- **Why:** Type hints drive request validation (pydantic), automatic OpenAPI docs at `/docs`, and it supports both sync and async handlers. It is lighter than Django, which brings an ORM and admin I don't need because I'm choosing SQLAlchemy.
- **Trade-offs:** Younger ecosystem than Django. No built-in admin or auth.
- **Interview question:** *Why FastAPI over Flask?* (Validation and docs from type hints, async support, performance via Starlette/uvicorn.)

## D2: PostgreSQL as the database and the queue store
- **Context:** A job queue must never lose jobs and never hand one job to two workers.
- **Alternatives:** Redis (fast, but weaker durability by default), RabbitMQ/Kafka (extra infrastructure), MySQL, MongoDB.
- **Why:** ACID transactions give durability and consistency. `SELECT ... FOR UPDATE SKIP LOCKED` lets many workers claim jobs concurrently without blocking or double-claiming. One system holds both the job data and the queue state.
- **Trade-offs:** Lower raw throughput than Redis or Kafka. Polling or LISTEN/NOTIFY is needed instead of push.
- **Interview question:** *How do you stop two workers picking the same job?* (Row locks with `SKIP LOCKED` inside a transaction.)

## D3: SQLAlchemy + Alembic
- **Context:** Need database access from Python and a way to evolve the schema safely.
- **Alternatives:** Raw SQL with a driver, Django ORM, Tortoise/SQLModel.
- **Why:** SQLAlchemy is the standard Python toolkit and supports both ORM and raw SQL. Alembic gives versioned, reviewable, reversible migrations.
- **Trade-offs:** More concepts to learn (engine, session, metadata) than raw SQL.
- **Interview question:** *Why migrations instead of `create_all()`?* (Versioned history, repeatable across environments, safe changes to existing data.)

## D4: psycopg v3 driver
- **Context:** SQLAlchemy needs a PostgreSQL driver. The URL scheme is `postgresql+psycopg://`.
- **Alternatives:** psycopg2, asyncpg.
- **Why:** psycopg 3 is the actively developed successor to psycopg2, and supports both sync and async. The `[binary]` extra avoids needing a C compiler and libpq headers.
- **Trade-offs:** Some older tutorials still show psycopg2 URLs (`postgresql://`).
- **Interview question:** *What does `postgresql+psycopg://` mean?* (dialect + driver.)

## D5: Docker Compose for Postgres, host port 5433
- **Context:** Need a reproducible database for development.
- **Alternatives:** Installing Postgres natively, a cloud-hosted database.
- **Why:** One command to start the same Postgres 16 for everyone. Host port 5433 (container 5432) avoids clashing with any local Postgres on 5432. A healthcheck shows when the DB is actually ready.
- **Trade-offs:** Needs Docker running. The port mapping must match `DATABASE_URL`.
- **Interview question:** *Why does the URL say 5433 but Postgres listens on 5432?* (host:container port mapping.)

## D6: Secrets in a gitignored `.env`
- **Context:** The database password must not live in git.
- **Alternatives:** Hard-coding it, committing `.env`, a secrets manager (overkill for now).
- **Why:** Follows the 12-factor rule of config in the environment. The same code runs in dev and production with different values.
- **Trade-offs:** A new clone needs its own `.env`. A committed `.env.example` with placeholders documents the required keys.
- **Interview question:** *How do you manage secrets in your project?*

## D7: `.env` at repo root, located with `pathlib` (`parents[3]`)
- **Context:** Docker Compose and the backend both need the same variables. The app can be launched from any directory.
- **Alternatives:** A relative path like `".env"` (breaks depending on the working directory), a separate `backend/.env`, setting env vars by hand.
- **Why:** Building the path from `__file__` makes it independent of the current directory. A single root `.env` means one source of truth shared with Compose.
- **Trade-offs:** `parents[3]` breaks if the file moves. The comment in `config.py` documents the layout.
- **Interview question:** *What does `Path(__file__).resolve().parents[3]` give you?*

## D8: `extra="ignore"`
- **Context:** The root `.env` also holds variables meant for Docker (e.g. Postgres user and password), not for the app.
- **Alternatives:** `extra="forbid"` (the default for dotenv files, which raises an error on unknown keys), declaring every variable as a field.
- **Why:** The app only models what it uses. Unknown keys shouldn't crash startup.
- **Trade-offs:** A typo in a variable name is silently ignored. Required fields (D9) still catch missing critical values.
- **Interview question:** *What happens without `extra="ignore"`?* (ValidationError for extra inputs.)

## D9: `database_url` is required, no default
- **Context:** The app cannot work without a database.
- **Alternatives:** A default like `sqlite:///dev.db` or localhost credentials.
- **Why:** Fail fast. A missing config stops the app at startup with a clear error, instead of silently connecting to the wrong database.
- **Trade-offs:** Tests and CI must provide the variable.
- **Interview question:** *Fail fast vs sensible defaults, which for secrets and connection strings?*

## D10: One shared module-level `settings`
- **Context:** Many modules need configuration.
- **Alternatives:** Build `Settings()` in each module, or use FastAPI dependency injection with `lru_cache`.
- **Why:** Python imports each module once, so `settings = Settings()` is a simple singleton. It is easy to read and import.
- **Trade-offs:** Settings load at import time, which makes it harder to override in tests. Dependency injection can be adopted later.
- **Interview question:** *Why is a module-level object a singleton in Python?*

## D11: Synchronous SQLAlchemy engine for now (revisit)
- **Context:** Step 7 only proves connectivity. No concurrency requirements yet.
- **Alternatives:** `create_async_engine` with `async def` handlers.
- **Why:** The simplest model to learn first. FastAPI runs plain `def` handlers in a thread pool, so they don't block the event loop.
- **Trade-offs:** A thread per concurrent request, so less scalable than async under heavy I/O. Moving to async later touches the engine, sessions and handlers.
- **Interview question:** *Does a sync `def` endpoint block FastAPI?* (No, it runs in a thread pool. `async def` with blocking code would.)

## D12: `/health` runs `SELECT 1`
- **Context:** Load balancers and orchestrators need a liveness/readiness signal.
- **Alternatives:** Return a static `{"status": "ok"}` that only proves the process is up.
- **Why:** The query proves the database is reachable, not just that the app is running.
- **Trade-offs:** If the DB is down, the endpoint currently returns a 500 instead of a clean 503. A readiness check can also hurt availability if the DB blips. Liveness and readiness can be split later.
- **Interview question:** *Liveness vs readiness probe: which is this?* (Closer to readiness.)

## D13: Branch-per-chore git workflow, manual commits
- **Context:** Learning project with a GitHub history that should be readable.
- **Alternatives:** Committing directly to `main`.
- **Why:** Small branches (`chore/dev-environment`) keep history reviewable. I run `git commit` and `git push` myself so I understand each change.
- **Trade-offs:** A bit more ceremony for a solo project.
- **Interview question:** *Walk me through your git workflow.*

---

## Open questions / revisit later
- Sync vs async engine once workers and load matter (D11).
- Return 503 from `/health` when the DB is unreachable (D12).
- Move the engine and sessions into a `db/` module once models arrive.

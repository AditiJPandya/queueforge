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
| D14 | `jobs.id` is BIGINT identity                  | Schema | Accepted |
| D15 | `task_name` string + worker handler registry  | Schema | Accepted |
| D16 | `payload` JSONB, NOT NULL, default `{}`, must be an object | Schema | Accepted |
| D17 | `status` as TEXT + CHECK constraint           | Schema | Accepted |
| D18 | Higher `priority` runs first, default 0       | Schema | Accepted (starvation noted) |
| D19 | `run_at` timestamptz; backoff via `run_at`; database clock | Schema | Accepted |
| D20 | Lease columns, short claim transaction, heartbeat about lease/3 | Schema | Accepted |
| D21 | `locked_by` FK to `workers`, SET NULL; workers soft-deleted | Schema | Accepted |
| D22 | `attempts` incremented at claim; guarded updates (fencing) | Schema | Accepted |
| D23 | Idempotency key unique per `(queue, key)`; mismatch gives 409 | Schema | Accepted |
| D24 | Retention policy and `finished_at`            | Schema | Accepted (numbers to confirm) |
| D25 | Partial indexes for claim and recovery        | Schema | Accepted (verify with EXPLAIN) |
| D26 | State-consistency CHECK (running means leased) | Schema | Accepted |
| D27 | `job_attempts`: UNIQUE `(job_id, attempt_no)`, ON DELETE CASCADE | Schema | Accepted |
| D28 | `job_dependencies`: PK pair, self-check, cycle check in code | Schema | Accepted |
| D29 | Engine and sessions live in `app/db/session.py`; `get_db` dependency | 8 | Accepted |

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

## D14: `jobs.id` is BIGINT identity
- **Context:** Every job needs a unique id, and the table is write-heavy.
- **Alternatives:** UUID (random or time-ordered UUIDv7), 32-bit INTEGER.
- **Why:** 8 bytes and sequential, so new rows land at the end of the index and inserts and the claim index stay compact. 64-bit avoids the ~2.1 billion limit of INTEGER. Idempotency has its own key, so UUIDs are not needed for deduplication.
- **Trade-offs:** Ids are guessable and reveal job counts. Revisit (UUIDv7) if ids are exposed to untrusted users.
- **Interview question:** *Integer or UUID for a primary key?*

## D15: `task_name` string with a handler registry
- **Context:** A job must say what to run, but a database cannot store a running function.
- **Alternatives:** Serialising code (pickle).
- **Why:** Pickle is fragile and unsafe (a poisoned row could run arbitrary code). Workers own the code and look the name up in a registry, so implementations can change without touching queued jobs. An unknown name is a clear error, and the table is queryable per task.
- **Trade-offs:** Workers need the registry kept in sync with the names the API accepts.
- **Interview question:** *Why not store the function in the database?*

## D16: `payload` JSONB, NOT NULL, default `{}`, must be an object
- **Context:** Each task type takes different arguments.
- **Alternatives:** Nullable payload, one column per argument, text JSON.
- **Why:** JSONB needs no column per task and stays queryable. NOT NULL removes the "NULL or `{}`" ambiguity. `CHECK (jsonb_typeof(payload) = 'object')` also rejects arrays and scalars, so handlers can always assume an object.
- **Trade-offs:** No schema enforcement inside the JSON, so validation happens in the API schemas.
- **Interview question:** *Why JSONB and not a column per argument?*

## D17: `status` as TEXT + CHECK
- **Context:** Six fixed states: queued, running, succeeded, dead, blocked, cancelled.
- **Alternatives:** Native ENUM, lookup table.
- **Why:** The CHECK rejects invalid values and is easy to change. An ENUM cannot cleanly remove or rename values. A lookup table adds a join for no benefit, since the states are a fixed state machine the code already knows.
- **Trade-offs:** The allowed list lives in both the CHECK and the Python enum. To add a status: a migration swaps the CHECK, deployed before the code that writes it.
- **Interview question:** *Enum vs CHECK vs lookup table?*

## D18: Higher `priority` runs first, default 0
- **Context:** Due jobs need an order.
- **Alternatives:** Lower number first.
- **Why:** Matches intuition (10 beats 1) and negatives can demote. Claim order is `priority DESC, run_at ASC, id ASC`, so equal priorities are FIFO.
- **Trade-offs:** Strict priority can starve low-priority jobs under a steady high-priority stream. The tie-breakers only protect jobs within one priority. A later fix is aging.
- **Interview question:** *How could priority scheduling starve jobs?*

## D19: `run_at` timestamptz, retries via `run_at`, database clock
- **Context:** Delayed jobs and retries with backoff both mean "not before time T".
- **Alternatives:** A separate delay column, per-worker clocks.
- **Why:** One column drives the claim filter (`run_at <= now()`). timestamptz stores one unambiguous UTC moment. Using the database's `now()` stops workers with skewed clocks disagreeing. Backoff is `min(cap, base * 2^attempts)` plus jitter, so jobs that fail together do not retry together.
- **Trade-offs:** All timing depends on the database clock.
- **Interview question:** *Why exponential backoff with jitter?*

## D20: Lease columns, short claim transaction, heartbeat about lease/3
- **Context:** A running job needs an owner, but holding a row lock for the whole job would hold a connection and block vacuum.
- **Alternatives:** One long transaction per job.
- **Why:** The claim is short: set `running`, `locked_by`, `lease_expires_at = now() + lease`, then commit. A heartbeat extends the lease. Crash means the heartbeat stops, the lease expires, and recovery requeues the job. The heartbeat is about lease/3 so two missed beats still keep the lease. This gives at-least-once delivery.
- **Trade-offs:** A job can run twice, so handlers must be idempotent.
- **Interview question:** *What happens when a worker dies mid-job?*

## D21: `locked_by` is a FK to `workers`, ON DELETE SET NULL; workers are soft-deleted
- **Context:** Jobs need to point at their worker, and the dashboard needs the join.
- **Alternatives:** Free-text hostname/pid.
- **Why:** Integrity plus an easy join. Worker rows are marked `stopped`, never deleted, so history stays and SET NULL never fires on a running job (it would violate D26).
- **Trade-offs:** Workers must register on startup.
- **Interview question:** *Foreign key or free text for the owner column?*

## D22: `attempts` incremented at claim; guarded updates (fencing)
- **Context:** A slow worker can lose its lease while a second worker takes the job.
- **Alternatives:** Blind updates on finish.
- **Why:** Incrementing at claim gives every claim a distinct number. Finishing and heartbeats use `UPDATE ... WHERE id=:id AND locked_by=:me AND status='running' AND attempts=:mine`. Zero rows updated means the lease was lost, so the worker discards its result.
- **Trade-offs:** Protects database state only. Side effects already done (an email sent) need idempotent handlers.
- **Interview question:** *What is a fencing token?*

## D23: Idempotency key unique per `(queue, key)`, mismatch gives 409
- **Context:** Clients retry submits and double-click.
- **Alternatives:** Globally unique key, silently returning the old job on a payload mismatch.
- **Why:** Keys come from natural ids and different queues may legitimately share them. UNIQUE allows many NULLs, so the key stays optional. A repeat with the same task and payload returns the existing job. A different payload is a client bug, so it returns 409 and never loses data silently. Insert with `INSERT ... ON CONFLICT (queue, idempotency_key) DO NOTHING RETURNING ...`, then fetch and compare, so there is no check-then-insert race.
- **Trade-offs:** Large payloads may need a stored hash to compare.
- **Interview question:** *How do you make a POST safe to retry?*

## D24: Retention policy and `finished_at`
- **Context:** The table grows without limit, and the idempotency window is bounded by how long rows live.
- **Alternatives:** Keep forever, partition by time.
- **Why:** Add `finished_at` (set on succeeded, dead, cancelled) with an index for cleanup. Delete succeeded jobs after about 7 days and dead jobs after about 30 days, in small batches to avoid long locks. Document "duplicates are detected within N days". Roll stats up before deleting.
- **Trade-offs:** The 7 and 30 day numbers are placeholders to confirm. Long-term stats need a summary table. Partitioning is deferred to benchmarking.
- **Interview question:** *How do you stop a queue table growing forever?*

## D25: Partial indexes for claim and recovery
- **Context:** The claim query reads a tiny slice of a table that is mostly finished jobs.
- **Alternatives:** Plain index on `status`.
- **Why:** `(queue, priority DESC, run_at, id) WHERE status='queued'` stays small and is already in `ORDER BY` order, so the claim reads one entry and stops. `(lease_expires_at) WHERE status='running'` serves recovery. `queue` leads because workers claim per queue.
- **Trade-offs:** The `run_at <= now()` condition is a filter, so future-dated high-priority jobs are skipped on each scan. Verify with `EXPLAIN ANALYZE` when benchmarking.
- **Interview question:** *Why a partial index?*

## D26: State-consistency CHECK
- **Context:** A forgotten lease or a ghost lock would leave jobs stuck or wrongly owned.
- **Alternatives:** Trust the code.
- **Why:** Running requires both `locked_by` and `lease_expires_at`, and every other status requires both NULL. The database refuses the bad write immediately.
- **Trade-offs:** Each state transition must change all the columns in one UPDATE. No step-by-step manual edits.
- **Interview question:** *What invariants does your schema enforce?*

## D27: `job_attempts` UNIQUE `(job_id, attempt_no)`, ON DELETE CASCADE
- **Context:** One row per run, for execution history.
- **Alternatives:** RESTRICT, no uniqueness.
- **Why:** The unique pair stops duplicate attempt records and its index serves "attempts for this job". Attempts mean nothing without their job, so cascade keeps cleanup a single DELETE.
- **Trade-offs:** Cleanup deletes attempt history with the job, so long-term stats need a rollup first. Large cascades are heavy, so cleanup runs in batches.
- **Interview question:** *Cascade or restrict, and what does it cost?*

## D28: `job_dependencies`: PK pair, self-check, cycle check in code
- **Context:** Blocked jobs wait on other jobs, and a loop would block them forever.
- **Alternatives:** Trust the client.
- **Why:** Primary key `(job_id, depends_on_job_id)` blocks duplicate edges, and `CHECK (job_id <> depends_on_job_id)` blocks self-dependency. A CHECK cannot see multi-row cycles, so the API walks the graph before inserting an edge, in one serialised transaction so two concurrent requests cannot together create a loop.
- **Trade-offs:** The cycle check costs a graph walk per insert.
- **Interview question:** *How do you prevent cycles in a dependency graph?*

## D29: Engine and sessions in `app/db/session.py`, `get_db` dependency
- **Context:** Step 7 created the engine in `main.py`. Many routes will need the database, and tests must be able to swap it.
- **Alternatives:** Keep the engine in `main.py`; build a connection inside each route.
- **Why:** One module reads `settings.database_url` and owns the engine (one connection pool per process). Each request gets its own session through `Depends(get_db)`, closed in a `finally` so connections are never leaked and uncommitted work is rolled back. Tests can replace the dependency with `app.dependency_overrides`. `autoflush=False` makes SQL timing explicit, and `expire_on_commit=False` keeps objects readable after a commit.
- **Trade-offs:** `get_db` never commits, so whoever writes data must commit or flush explicitly. Pending changes are not visible to queries until `flush()`.
- **Interview question:** *Why `yield` in a FastAPI dependency, and why one session per request?* (Setup and cleanup around the route, and sessions are not safe to share.)

---

## Open questions / revisit later
- Sync vs async engine once workers and load matter (D11).
- Return 503 from `/health` when the DB is unreachable (D12).
- ~~Move the engine and sessions into a `db/` module once models arrive.~~ Done in D29.
- Priority starvation: add aging if low-priority jobs wait too long (D18).
- Confirm the retention numbers (7 days / 30 days) and add a stats rollup table (D24).
- What happens to jobs that depend on a `dead` job: stay `blocked` forever, or cascade to `dead`/`cancelled`? (D28)
- Verify the claim index with `EXPLAIN ANALYZE` during benchmarking (D25).

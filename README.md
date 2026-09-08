# CoordSync

A web app for coordinating the work of technical teams.

## The problem

At the company where I work, coordinating shared projects meant scattered chat
messages and Word or Excel files — no single, up-to-date picture of who had to
do what. CoordSync was built to give a technical team one place to see projects,
jobs and their progress.

## What it does

- Coordinates teams and departments across projects and jobs, with status,
  priority, due dates, assignments and comments.
- Calendar with meetings and recurring events.
- Machine records with an intervention history, grouped by topic.
- Role-based permissions: decide who can only view and who can create or edit
  projects and jobs.
- Two levels of isolation: each company sees only its own data, and within a
  company, departments limit visibility by role.

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic for migrations
- **Database:** SQLite (development) → PostgreSQL (production)
- **Authentication:** bcrypt password hashing, JWT tokens, login rate limiting
- **Frontend:** React + Vite, no UI libraries — CSS written by hand
- **Tests:** pytest (246) and vitest (17) · **CI:** GitHub Actions, which on
  every push runs the tests, applies migrations up and down, and builds the
  frontend
- **Observability:** Sentry for production errors, per-request logging
- **In production:** Render (web service + static site + PostgreSQL), email via
  the Brevo HTTP API, weekly encrypted backup through a GitHub Action

## Architecture at a glance

A layered backend, one responsibility per file:

- **Models** (`app/models`): the entities and their relationships —
  organization, membership (a user in a company, with a role), department,
  project, job, subtask, comment, machine and machine entry, attachment, event
  (calendar), notification. Projects and machines can belong to more than one
  department.
- **Routers** (`app/routers`): the HTTP endpoints, one module per area (auth,
  projects, jobs, comments, assignments, subtasks, departments, machines,
  calendar, notifications, global search).
- **Schemas** (`app/schemas`): input/output validation with Pydantic.
- **Security** (`app/security`, `app/dependencies`): password hashing, tokens,
  role and membership checks on every request.
- **Observability** (`app/osservabilita`): per-request logging and Sentry alerts.
- **Configuration** (`app/config`): settings from environment variables, with a
  guard that stops production from starting with the example key.

The database schema is managed by Alembic migrations (not created on the fly),
so development and production stay in sync and tables can evolve without losing
data. Isolation works on two levels: each company sees only its own data, and
within a company, departments limit visibility of projects and jobs by role.

## Running it locally

Backend:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head            # create/update the database schema
uvicorn app.main:app --reload
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Interactive API docs: http://127.0.0.1:8000/docs

## Tests

```bash
pytest                          # backend
cd frontend && npm test         # frontend
```

## Project status

In production and used in the field. Backend and frontend are complete for
day-to-day work: projects and jobs with status, priority, due dates,
assignments and comments; departments with role-based visibility; machine
records with history grouped by topic; a calendar with meetings; notifications;
unified search. The project is still under active development.

## License

MIT — see the [LICENSE](LICENSE) file.

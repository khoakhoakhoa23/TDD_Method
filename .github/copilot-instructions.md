## Purpose
This file gives concise, repository-specific guidance for AI coding agents working on this project.

## Big picture
- Backend: Django REST API under `backend/` with a single app `api` (see [backend/manage.py](backend/manage.py)).
- Frontend: Vite + React under `frontend/` (use `npm install` then `npm run dev`).
- DB: SQLite at `backend/db.sqlite3` and migrations present under `backend/api/migrations/`.
- Auth: DRF + Simple JWT (`REST_FRAMEWORK` configured in [backend/backend/settings.py](backend/backend/settings.py)).

Data flow & responsibilities
- HTTP requests -> function-based DRF views in [backend/api/views.py](backend/api/views.py).
- Input validation & shape -> serializers in [backend/api/serializers.py](backend/api/serializers.py).
- Persistence -> models in `backend/api/models.py` (migrations capture schema).
- Tests drive design: tests in `backend/api/tests/` express expected behavior (fixtures in [backend/api/tests/conftest.py](backend/api/tests/conftest.py)).

Key conventions and patterns
- TDD-first: follow RED → GREEN → REFACTOR (project docs in `README_TDD.md`). Tests are authoritative.
- Tests use `pytest` and `pytest-django`; DB tests are marked with `@pytest.mark.django_db`.
- Shared fixtures: `api_client`, `authenticated_client`, `admin_client`, `user`, `product`, `category` (see [backend/api/tests/conftest.py](backend/api/tests/conftest.py)).
- Factories use factory_boy in [backend/api/tests/factories.py](backend/api/tests/factories.py).
- API style: function-based views using `@api_view`; no DRF ViewSets are used in most places—follow existing view patterns when adding endpoints.
- Serializer patterns: prefer `PrimaryKeyRelatedField` for relations in list/create serializers and a nested `*DetailSerializer` for read endpoints (see [backend/api/serializers.py](backend/api/serializers.py)).

Project-specific behavior worth noting
- Product creation: anonymous POST is allowed; authenticated non-staff POST is explicitly forbidden by view logic — tests depend on this nuance (see `product_list_create` in [backend/api/views.py](backend/api/views.py)).
- Payment webhook: expecting provider transaction IDs that start with `TXN`; webhook is implemented with idempotency and DB transactions (see `payment_webhook` in [backend/api/views.py](backend/api/views.py)).
- Order status transitions are implemented with string statuses and guarded flows (see `update_order_status`).

Developer workflows (commands you can run)
- Run backend tests (preferred):
  - `cd backend` then `pytest` (or use `backend/run_tests.bat` / `backend/run_tests.sh`).
- Run backend dev server: `cd backend && python manage.py runserver`.
- Run frontend dev: `cd frontend && npm install && npm run dev`.
- Create migrations (if you modify models): `cd backend && python manage.py makemigrations && python manage.py migrate`.

How an AI agent should make changes
- Edit tests first for TDD tasks: update or add tests under `backend/api/tests/` mirroring existing naming and fixture usage.
- Implement minimal code to satisfy tests in `api/serializers.py`, `api/views.py`, or `api/models.py` as appropriate.
- Preserve existing API contracts: prefer adding new endpoints rather than changing existing response shapes unless tests are updated accordingly.
- Use `pytest -k <pattern>` to run focused tests during development.

Files to inspect for context when making changes
- [backend/api/views.py](backend/api/views.py)
- [backend/api/serializers.py](backend/api/serializers.py)
- [backend/api/tests/conftest.py](backend/api/tests/conftest.py)
- [backend/api/tests/factories.py](backend/api/tests/factories.py)
- [backend/requirements.txt](backend/requirements.txt)
- [README_TDD.md](README_TDD.md)

When to ask the human
- If a change would modify public API shapes (response fields, status codes) beyond tests, ask for confirmation.
- If new external services or secrets are required (payment providers, external queues), request credentials and deployment guidance.

Feedback
Please review these instructions and tell me if you want more detail about any area (tests, CI, or frontend integration).

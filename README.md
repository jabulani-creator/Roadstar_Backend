# Roadstar backend

Local API for the Roadstar Driving School platform.

## Setup

```bash
cd backend
poetry install
copy .env.example .env
# Edit .env and set a real SECRET_KEY (already done if .env exists)
poetry run python manage.py migrate
poetry run python manage.py runserver 8000
```

Health check: http://127.0.0.1:8000/api/v1/health/

API docs (DEBUG only):

- Swagger UI: http://127.0.0.1:8000/api/docs/ (also `/api/v1/docs/`)
- ReDoc: http://127.0.0.1:8000/api/redoc/
- OpenAPI schema: http://127.0.0.1:8000/api/schema/

Login in Swagger: `POST /api/v1/auth/token/` with `email` + `password`, then **Authorize** and paste the access token.

## Environment files

| File | Purpose |
|---|---|
| `.env` | Your real local secrets. Gitignored. Never commit. |
| `.env.example` | Safe template teammates copy. No real secrets. |

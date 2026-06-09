# GDocx Backend

FastAPI API with Supabase for authentication and PostgreSQL database.

## Folder structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point, global error handler
│   ├── config.py            # pydantic-settings env config
│   ├── dependencies.py      # JWT auth middleware (get_current_user)
│   ├── routes/
│   │   ├── auth.py          # Register, login, logout, me
│   │   ├── documents.py     # Document CRUD + sharing
│   │   └── health.py        # Health check
│   ├── schemas/
│   │   ├── auth.py          # Auth request/response models
│   │   └── documents.py     # Document request/response models
│   └── services/
│       ├── supabase_client.py   # Cached Supabase client factory
│       ├── supabase_errors.py   # Error mapping (PGRST205, transient, etc.)
│       └── supabase_retry.py    # Retry logic with exponential back-off
├── database/
│   └── schema.sql           # Supabase SQL migrations (run once)
├── tests/                   # pytest suite (45 tests, no live DB needed)
├── pytest.ini
├── requirements.txt
├── .env.example
└── README.md
```

## Prerequisites

- Python 3.9+
- A [Supabase](https://supabase.com) project (free tier works)

## Installation

### 1. Create a Supabase project

1. Go to [supabase.com](https://supabase.com) and create a project.
2. Open **Project Settings → API** and copy:
   - Project URL → `SUPABASE_URL`
   - `anon` public key → `SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY`
   - JWT Secret → `SUPABASE_JWT_SECRET`

### 2. Set up the database

In the Supabase **SQL Editor**, run the contents of `database/schema.sql`.

### 3. Install Python dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 5. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/api/docs

## Running tests

```bash
pytest
```

Tests run without a live Supabase project — all external calls are mocked.

## API endpoints

Protected routes require: `Authorization: Bearer <access_token>`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health` | No | Health check |
| POST | `/api/auth/register` | No | Create account |
| POST | `/api/auth/login` | No | Sign in |
| POST | `/api/auth/logout` | No | Sign out |
| GET | `/api/auth/me` | Yes | Current user |
| GET | `/api/documents` | Yes | List own documents |
| POST | `/api/documents` | Yes | Create document |
| GET | `/api/documents/shared` | Yes | Documents shared with me |
| GET | `/api/documents/share-users` | Yes | Users available to share with |
| GET | `/api/documents/{id}` | Yes | Get document (owner or shared viewer) |
| PUT | `/api/documents/{id}` | Yes | Update title / content |
| DELETE | `/api/documents/{id}` | Yes | Delete (owner only) |
| POST | `/api/documents/{id}/share` | Yes | Share with a user |
| GET | `/api/documents/{id}/shares` | Yes | List current shares |
| DELETE | `/api/documents/{id}/share/{uid}` | Yes | Revoke a share |

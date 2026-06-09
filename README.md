# GDocx Backend

FastAPI API with Supabase for authentication and PostgreSQL database.

## Folder structure

```
backend/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Environment settings
│   ├── dependencies.py      # Auth middleware (JWT)
│   ├── routes/
│   │   ├── auth.py          # Register, login, logout, me
│   │   └── health.py        # Health check
│   ├── schemas/
│   │   └── auth.py          # Request/response models
│   ├── services/
│   │   └── supabase_client.py
│   └── models/
├── database/
│   └── schema.sql           # Supabase SQL migrations
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

## API endpoints

| Method | Endpoint         | Auth | Description        |
|--------|------------------|------|--------------------|
| GET    | `/api/health`    | No   | Health check       |
| POST   | `/api/auth/register` | No | Create account |
| POST   | `/api/auth/login`    | No | Sign in        |
| POST   | `/api/auth/logout`   | No | Sign out       |
| GET    | `/api/auth/me`       | Yes | Current user  |

Protected routes require: `Authorization: Bearer <access_token>`

"""Seed test users via Supabase Admin API.

Usage (from backend/):
    source .venv/bin/activate
    PYTHONPATH=. python database/seed_users.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.services.supabase_client import get_supabase_admin

SEED_USERS = [
    {"email": "owner@test.com", "password": "password", "email_confirm": True},
    {"email": "user@test.com", "password": "password", "email_confirm": True},
]


def main() -> None:
    admin = get_supabase_admin()

    for user in SEED_USERS:
        try:
            response = admin.auth.admin.create_user(user)
            print(f"Created {user['email']} ({response.user.id})")
        except Exception as exc:
            print(f"Skipped {user['email']}: {exc}")


if __name__ == "__main__":
    main()

#!/bin/sh
# Jalankan migrasi dulu; kalau gagal, container berhenti (set -e) dan tidak melayani request.
set -e

alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port 8000

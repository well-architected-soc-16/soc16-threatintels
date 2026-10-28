# TASK-01 — Fondasi Backend (target: jalan malam ini)

> Taruh file ini di `docs/tasks/TASK-01-fondasi-backend.md`.
> Prompt ke Claude Code: **"Baca CLAUDE.md dan docs/tasks/TASK-01-fondasi-backend.md. Kerjakan Tahap 0 saja, jalankan Cek selesai, lalu berhenti dan laporkan."**
> Ulangi untuk Tahap 1, 2, dst. Tidak harus selesai semua malam ini — Tahap 0–2 sudah cukup untuk "ada yang jalan".

Branch kerja: `feat/fondasi-backend`.
Di luar lingkup task ini: frontend, adapter AbuseIPDB/VirusTotal, scoring, CI/CD, deploy ke soc-ir.

---

## Tahap 0 — Kerangka proyek + Docker Compose (API + Postgres)

**Kerjakan:**
1. Buat struktur folder `backend/` sesuai CLAUDE.md (file boleh kosong/minimal dulu).
2. `backend/requirements.txt`: fastapi, uvicorn[standard], sqlalchemy (2.x), alembic, psycopg[binary] (v3),
   pydantic-settings, pyjwt, "pwdlib[argon2]", python-multipart.
   `backend/requirements-dev.txt`: pytest, httpx, ruff. Pin versi (`==`) setelah dicek ke PyPI.
3. `backend/Dockerfile`: base `python:3.12-slim`, user non-root, install requirements, jalankan uvicorn di port 8000.
4. `app/core/config.py` (pydantic-settings) membaca dari env:
   `APP_ENV`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD_FILE`, `JWT_SECRET_KEY`,
   `JWT_EXPIRE_MINUTES` (default 30), `MISP_MODE` (default `mock`), `LOG_LEVEL`.
   Password DB dibaca dari isi file di `DB_PASSWORD_FILE` (bukan env biasa). URL DB dirakit di config.
5. `app/main.py` + `routers/health.py`: `GET /api/v1/health` → `{"status":"ok","db":"ok|error","misp_mode":"mock","time":"<ISO8601 WIB>"}`.
   Cek DB dengan query `SELECT 1`.
6. `docker-compose.yml` (dev):
   - service `db`: `postgres:18-alpine`, env `POSTGRES_DB`, `POSTGRES_USER`,
     `POSTGRES_PASSWORD_FILE=/run/secrets/db_password`, secret `db_password` dari `./secrets/db_password.txt`,
     volume bernama ke `/var/lib/postgresql`, healthcheck `pg_isready`, **tanpa `ports:`**.
   - service `api`: build `./backend`, `env_file: .env`, secret `db_password` yang sama,
     `depends_on: db: condition: service_healthy`, ports `"127.0.0.1:8000:8000"`.
   - network internal bersama.
7. `.env.example` (placeholder saja) dan pastikan `.gitignore` memuat: `.env`, `secrets/`, `__pycache__/`,
   `*.pyc`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `node_modules/`.
8. `.dockerignore` di `backend/` (abaikan `.env`, `secrets/`, cache, `.venv`).

**Cek selesai:**
```fish
docker compose up -d --build
docker compose ps                         # db = healthy, api = running
curl -s http://127.0.0.1:8000/api/v1/health
git status                                # .env & secrets/ TIDAK muncul
```
Buka `http://127.0.0.1:8000/docs` → Swagger tampil.

---

## Tahap 1 — Database, migrasi, seed user

**Kerjakan:**
1. `db/base.py`, `db/session.py` (SQLAlchemy 2.x, session per request via dependency).
2. Model:
   - `users`: id, username (unique), password_hash, role (`admin`/`analyst`/`viewer`), can_send_misp (bool, default false),
     is_active (bool), created_at, updated_at.
   - `audit_logs`: id, actor_username (nullable untuk login gagal), action, target, result (`success`/`denied`/`error`),
     detail (JSONB, TANPA rahasia), ip_address (client), created_at.
3. Alembic: init, migrasi pertama untuk dua tabel di atas.
4. `scripts/entrypoint.sh`: jalankan `alembic upgrade head`, lalu start uvicorn. Pakai di Dockerfile.
5. `scripts/seed_users.py`: buat 4 user dari env (`SEED_ADMIN_USER/PASSWORD`, `SEED_ANALYST_MISP_USER/PASSWORD`,
   `SEED_ANALYST_USER/PASSWORD`, `SEED_VIEWER_USER/PASSWORD`). Idempotent (aman dijalankan ulang).
   analyst-misp → role analyst + `can_send_misp=true`. Tolak password < 12 karakter.

**Cek selesai:**
```fish
docker compose up -d --build
docker compose exec api python -m scripts.seed_users
docker compose exec db psql -U <DB_USER> -d <DB_NAME> -c "select username, role, can_send_misp from users;"
```
Password hash harus berawalan `$argon2`.

---

## Tahap 2 — Login JWT + RBAC + admin user management

**Kerjakan:**
1. `core/security.py`: hash/verify password (pwdlib recommended), buat & verifikasi JWT (PyJWT, HS256, claim `sub`, `role`, `exp`).
   Saat username tidak ada, tetap jalankan verify terhadap dummy hash (mencegah timing attack, seperti tutorial resmi FastAPI).
2. `core/deps.py`: `get_current_user`, `require_roles(*roles)`, `require_misp_permission`.
   User nonaktif → 401/403. Role & izin dibaca ulang dari DB (jangan percaya klaim token saja).
3. Router `auth`: `POST /api/v1/auth/login` (OAuth2PasswordRequestForm), `GET /api/v1/auth/me`.
4. Router `admin` (khusus admin): `GET /api/v1/admin/users`, `POST /api/v1/admin/users`,
   `PATCH /api/v1/admin/users/{id}` (ubah role, `can_send_misp`, `is_active`).
5. `services/audit.py`: catat login sukses/gagal, akses ditolak (403), dan perubahan user. Jangan simpan password/token.
6. Tests (`tests/`): pakai database test terpisah (mis. `<DB_NAME>_test`), jangan pakai DB dev.
   - login benar → 200 + token; login salah → 401
   - viewer `GET /admin/users` → **403**; analyst `PATCH /admin/users/{id}` → **403**
   - admin bisa beri `can_send_misp` ke analyst
   - token kedaluwarsa/rusak → 401
   - akses 403 tercatat di `audit_logs`

**Cek selesai:**
```fish
docker compose exec api pytest -q
```
Di Swagger: Authorize sebagai viewer → coba `GET /api/v1/admin/users` → 403 (screenshot = bukti KM-8).

---

## Tahap 3 — Validasi IP + endpoint cek (tanpa sumber eksternal dulu)

**Kerjakan:**
1. `services/ip_validation.py` pakai modul `ipaddress` standar. Hasil: `valid` atau `rejected` + `reason_code`
   (`INVALID_FORMAT`, `IPV6_NOT_SUPPORTED`, `PRIVATE`, `LOOPBACK`, `LINK_LOCAL`, `MULTICAST`, `RESERVED`, `NOT_GLOBAL`, ...).
2. Model `ip_checks`: id, ip, assessment_status, risk_score (nullable), scoring_version, coverage (mis. "0/2"),
   flags (JSONB), sources (JSONB), checked_by, checked_at.
3. `POST /api/v1/checks` (admin, analyst):
   - Input ditolak → **422** dengan body `assessment_status: "INPUT_DITOLAK"`, `risk_score: null`, `reason_code`. Catat di audit log.
   - Input valid → simpan `ip_checks` dengan dua sumber berstatus `SKIPPED` alasan `ADAPTER_NOT_IMPLEMENTED`,
     `assessment_status: "TIDAK_TERSEDIA"`, `coverage: "0/2"`, `risk_score: null`, `scoring_version: "v1-percobaan"`.
     (Ini placeholder jujur sampai adapter AbuseIPDB/VirusTotal dibuat di task berikutnya.)
4. `GET /api/v1/checks` (semua role, paginasi) dan `GET /api/v1/checks/{id}`.
5. Tests: `8.8.8.8` valid; `10.0.0.5`, `127.0.0.1`, `192.168.1.1`, `169.254.1.1`, `224.0.0.1`, `192.0.2.1`,
   `abc`, `::1`/IPv6 ditolak dengan reason yang tepat; viewer `POST /checks` → 403;
   pastikan tidak ada pemanggilan adapter/HTTP keluar untuk input yang ditolak.

**Cek selesai:** `docker compose exec api pytest -q` hijau + coba manual di Swagger.

---

## Tahap 4 — Kesiapan MISP (mode mock)

**Kerjakan:**
1. `services/misp/base.py`: `Protocol MispClient` dengan `submit_indicator(ip, reason, tags, submitted_by) -> SubmissionResult`
   (`status`, `misp_event_uuid | None`, `error_message | None`).
2. `services/misp/mock.py`: tidak menghubungi apa pun; return status `mock_sent` + id `MOCK-<uuid>`.
   `services/misp/live.py`: kerangka class yang melempar `NotImplementedError` dengan pesan jelas (akan diisi PyMISP).
   `services/misp/__init__.py`: factory berdasarkan `MISP_MODE` (`mock` | `live`).
3. Model `ioc_submissions`: id, check_id (FK, **UNIQUE**), ip, reason (wajib, min 10 karakter), tags (JSONB),
   status (`pending`/`mock_sent`/`sent`/`failed`), misp_event_uuid, error_message, submitted_by, submitted_at.
4. `POST /api/v1/iocs/misp` (admin, atau analyst dengan `can_send_misp`): body `check_id`, `reason`, `tags` opsional.
   - Hanya untuk check yang `assessment_status` bukan `INPUT_DITOLAK`.
   - Kirim ulang untuk check yang sama → **409** berisi id submission yang sudah ada (tidak menggandakan).
   - Hasil gagal disimpan sebagai `failed`, bukan sukses.
   `GET /api/v1/iocs` (semua role).
5. `/health` menampilkan `misp_mode`.
6. Tests: analyst tanpa izin → 403; viewer → 403; analyst-misp → 201 `mock_sent`; kirim dua kali → 409;
   alasan kosong → 422.

**Cek selesai:** `docker compose exec api pytest -q` hijau.

---

## Tahap 5 — Rapikan (opsional, kalau masih ada waktu)

- `ruff check` bersih.
- README bagian "Menjalankan secara lokal" (perintah fish), daftar endpoint, cara seed user.
- Commit per tahap, push branch, buka Pull Request ke `main`.

## Definition of Done TASK-01

- [ ] `docker compose up -d --build` menyalakan db + api tanpa error
- [ ] Login 4 user berhasil, RBAC + uji 403 punya test
- [ ] Validasi IP sesuai aturan, input ditolak tanpa request keluar
- [ ] `ioc_submissions` + endpoint MISP mock siap, anti-duplikat
- [ ] Tidak ada rahasia di riwayat git

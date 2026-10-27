# CLAUDE.md — soc16-threatintels

Konteks tetap untuk Claude Code. Baca file ini sebelum mengerjakan task apa pun.

## Tentang proyek

Tool **Threat Intelligence & IP Reputation Aggregator** untuk PBL "Well Architected SOC 16" (RKS-316).
Tool ini nantinya di-deploy ke VM **soc-ir** (Ubuntu 24.04, zona SOC, <IP_SOC_IR>) dengan pola tarik
(GitHub Actions → GHCR → soc-ir `docker compose pull`). Saat ini dikembangkan di laptop developer
(CachyOS, shell **fish**, Docker + Docker Compose, RAM ~8 GB).

**Status saat ini:** soc-ir dan MISP **belum terpasang**. Integrasi MISP memakai **mode mock**
sampai MISP siap. Kode harus bisa pindah ke MISP asli hanya dengan mengubah `.env`.

## Tech stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2 + pydantic-settings
- Auth: OAuth2 password flow + JWT (**PyJWT**), hashing password **pwdlib[argon2]**
  (mengikuti tutorial resmi FastAPI "OAuth2 with Password (and hashing), Bearer with JWT tokens")
- Database: PostgreSQL di container (`postgres:18-alpine`), driver psycopg 3
- Frontend (task terpisah, BELUM sekarang): Vite + React + TypeScript
- Test: pytest + httpx (TestClient)

## Struktur folder (target)

```
backend/
  app/
    main.py
    core/        config.py, security.py, deps.py, logging.py, timeutil.py
    db/          base.py, session.py
    models/      user.py, audit_log.py, ip_check.py, ioc_submission.py
    schemas/     pydantic schemas
    routers/     health.py, auth.py, admin.py, checks.py, iocs.py
    services/
      ip_validation.py
      audit.py
      misp/      base.py (Protocol), mock.py, live.py (belum diimplementasi), __init__.py (factory)
  alembic/ + alembic.ini
  scripts/       seed_users.py, entrypoint.sh
  tests/
  Dockerfile, requirements.txt, requirements-dev.txt
frontend/        (nanti)
docs/tasks/      file task per tahap
docker-compose.yml
.env.example
secrets/         (gitignored — berisi db_password.txt)
```

## Peran & hak akses (RBAC) — wajib ditegakkan di BACKEND

| Aksi | admin | analyst | viewer |
|---|---|---|---|
| Lihat history cek IP & daftar submission | ✅ | ✅ | ✅ |
| Membuat cek IP (`POST /checks`) | ✅ | ✅ | ❌ 403 |
| Kirim IoC ke MISP (`POST /iocs/misp`) | ✅ | hanya jika `can_send_misp=true` | ❌ 403 |
| Kelola user, ubah role, beri/cabut `can_send_misp` | ✅ | ❌ 403 | ❌ 403 |

Pemetaan rencana tim (dibuat lewat seed, username & password dari `.env`):
admin = developer TI tool; analyst + `can_send_misp` = anggota yang memegang pengiriman MISP;
analyst biasa = analis kedua; viewer = anggota read-only.

Uji akses negatif (viewer/analyst ditolak 403) WAJIB punya test — ini bukti KM-8.

## Aturan domain (dari dokumen riset reputasi IP v1.1 tim)

- Input v1: **satu IPv4 publik** saja. Tolak: privat/internal (termasuk IP lab (rentang privat RFC 1918)), loopback,
  link-local, multicast, unspecified, reserved, alamat dokumentasi, dan yang tidak `is_global`.
  IPv6 → pesan "belum didukung". Input yang ditolak **tidak boleh memicu request keluar apa pun**.
- Sumber v1 (BELUM diimplementasi di task awal): AbuseIPDB + VirusTotal, lewat adapter.
- `assessment_status`: `COMPLETE` (2/2), `DATA_TERBATAS` (1/2), `TIDAK_TERSEDIA` (0/2), `INPUT_DITOLAK`.
- Status per sumber: `OK_SIGNAL`, `OK_NO_SIGNAL`, `NO_RECORD`, `INSUFFICIENT_DATA`, `ERROR`, `SKIPPED`.
- Skor gabungan hanya dihitung jika kedua sumber bisa dinilai; selain itu `risk_score = null`.
  Error/kosong TIDAK BOLEH diubah menjadi skor 0.
- Pengiriman ke MISP: **manual**, oleh user berwenang, **alasan wajib diisi**, klik ulang/retry
  **tidak boleh menggandakan** data. Kegagalan tidak boleh ditampilkan sebagai sukses.
- Tidak ada auto-block berdasarkan skor TI pada v1.

## Aturan keamanan (repo ini PUBLIC)

- JANGAN pernah commit `.env`, isi `secrets/`, API key, password, atau JWT secret.
  Yang boleh di-commit hanya `.env.example` dengan nilai placeholder.
- API key pihak ketiga hanya ada di backend, tidak pernah dikirim ke frontend.
- JANGAN menulis password, token JWT, API key, atau header Authorization ke log.
- Postgres TIDAK di-expose ke host (tanpa `ports:`). API di-bind ke `127.0.0.1` saat dev.
- Jangan matikan verifikasi TLS secara global (nanti untuk MISP self-signed, pakai file CA).
- Jangan memanggil API eksternal (AbuseIPDB, VirusTotal, MISP) di test — gunakan mock/fixture.

## Konvensi

- Semua timestamp disimpan `timestamptz` dalam UTC; respons API memakai ISO 8601 dengan offset WIB (+07:00).
- Prefix API: `/api/v1`. Swagger di `/docs` harus mendokumentasikan juga respons gagal (401/403/409/422).
- Log aplikasi ke stdout format JSON.
- Commit kecil per tahap, gaya Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).
- Developer memakai shell **fish**: kalau memberi perintah, pastikan kompatibel fish
  (mis. `source .venv/bin/activate.fish`, `set -x VAR value`).

## Cara kerja yang diharapkan

1. Kerjakan task **per tahap**. Setelah satu tahap selesai: jalankan pengecekan di bagian
   "Cek selesai", laporkan hasilnya, lalu **berhenti dan tunggu konfirmasi** sebelum tahap berikut.
2. Kalau ragu soal versi library/API, cek dokumentasi resmi; jangan menebak.
3. Kalau ada yang gagal, laporkan apa adanya beserta penyebabnya. Jangan menyembunyikan error.

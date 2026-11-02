# CLAUDE.md — soc16-threatintels

Konteks tetap untuk Claude Code. Baca file ini sebelum mengerjakan task apa pun.

## Tentang proyek

Tool **Threat Intelligence & IP Reputation Aggregator** untuk PBL "Well Architected SOC 16" (RKS-316).
Tool ini nantinya di-deploy ke VM **soc-ir** (Ubuntu 24.04, zona SOC, <IP_SOC_IR>) dengan pola tarik
(GitHub Actions → GHCR → soc-ir `docker compose pull`). Saat ini dikembangkan di laptop developer
(CachyOS, shell **fish**, Docker + Docker Compose, RAM ~8 GB).

**Status:** lihat `docs/tasks/`. `TASK-xx-*.md` = rencana per tahap; `TASK-xx-progress.md` = status,
keputusan, dan known gaps. TASK-01 (fondasi backend) selesai. soc-ir dan MISP **belum terpasang**:
MISP memakai **mode mock**. Pindah ke MISP asli atau sumber reputasi live harus cukup dengan mengubah `.env`.

## Tech stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2 + pydantic-settings
- Auth: OAuth2 password flow + JWT (**PyJWT**), hashing password **pwdlib[argon2]**
  (mengikuti tutorial resmi FastAPI "OAuth2 with Password (and hashing), Bearer with JWT tokens")
- HTTP ke sumber eksternal: **httpx** (client bisa disuntikkan; test memakai `httpx.MockTransport`)
- Database: PostgreSQL di container (`postgres:18-alpine`), driver psycopg 3
- Frontend (TASK-03): Vite + React + TypeScript + Tailwind CSS v4, Node di laptop host (bukan kontainer); rencana di
  `docs/tasks/TASK-03-frontend-workbench.md`
- Test: pytest + httpx (TestClient); lint & format: ruff. Frontend: Vitest + Oxlint

## Perintah (dari root repo, fish)

```fish
docker compose up -d --build        # WAJIB setelah mengubah kode: test jalan di image, kode tidak di-mount
docker compose exec api python -m pytest -q -p no:cacheprovider
docker compose exec api ruff check --no-cache .
docker compose exec api ruff format --no-cache --check .
docker compose up -d --force-recreate api   # setelah .env.example berubah (mount satu file menyimpan inode)
```

Gerbang frontend (dari root repo, fish; jalankan di setiap tahap TASK-03, selain gerbang backend di atas):

```fish
cd frontend
npm ci
npm run lint
npm run build          # tsc -b + vite build
npm test               # vitest run
npm audit --omit=dev   # dan juga: npm audit (penuh); catat hasilnya, jangan --force
cd ..
```

Dev: `cd frontend; npm run dev` (backend harus sudah `docker compose up -d`). Sesi uji tim lewat LAN: `npm run dev:lan`
(lihat README "Uji bersama tim").

## Lokasi modul

- `backend/app/core/` config, security, deps (auth/RBAC), logging, timeutil, secret_policy
- `backend/app/routers/` health, auth, admin, checks, iocs — prefix `/api/v1`
- `backend/app/services/` audit, ip_validation, ip_checks, `misp/` (Protocol, mock, kerangka live),
  `sources/` (adapter AbuseIPDB/VirusTotal + mock, mulai TASK-02), `scoring.py` (mulai TASK-02)
- `backend/alembic/versions/` migrasi; `backend/tests/` test; `backend/tests/fixtures/sources/` fixture respons sumber
- `frontend/` Vite + React + TS (`src/`, `vite.config.ts` berisi proxy `/api`); `docs/tasks/` rencana dan progres per task

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

- Input v1: **satu IPv4 publik** saja. Tolak: privat/internal (termasuk IP lab, rentang privat RFC 1918), loopback,
  link-local, multicast, unspecified, reserved, alamat dokumentasi, dan yang tidak `is_global`.
  IPv6 → pesan "belum didukung". Input yang ditolak **tidak boleh memicu request keluar, akses cache, atau kuota**.
- Sumber v1: AbuseIPDB + VirusTotal lewat adapter (`SOURCES_MODE=mock|live`). Detail rumus, pemetaan status,
  TTL cache, dan batas kuota ada di `docs/tasks/TASK-02-sumber-reputasi-skor.md`; **jangan mengubah bobot,
  koefisien, ambang label, atau TTL tanpa keputusan tim** (statusnya masih "percobaan").
- `assessment_status`: `COMPLETE` (2/2), `DATA_TERBATAS` (1/2), `TIDAK_TERSEDIA` (0/2), `INPUT_DITOLAK`.
- Status per sumber: `OK_SIGNAL`, `OK_NO_SIGNAL`, `NO_RECORD`, `INSUFFICIENT_DATA`, `ERROR`, `SKIPPED`.
  Hanya `OK_SIGNAL` dan `OK_NO_SIGNAL` yang menambah cakupan.
- Skor gabungan hanya dihitung jika kedua sumber bisa dinilai; selain itu `risk_score = null`.
  Error/kosong TIDAK BOLEH diubah menjadi skor 0. Nol laporan AbuseIPDB ≠ `NO_RECORD`.
- Hasil dari adapter mock **wajib** berflag `SUMBER_SIMULASI`; data simulasi tidak boleh tampak seperti data nyata.
- Kuota sumber dipakai **bersama** oleh semua user (satu API key): VirusTotal 4/menit & 500/hari,
  AbuseIPDB check 1.000/hari (terverifikasi 29 Okt 2026).
- Pengiriman ke MISP: **manual**, oleh user berwenang, **alasan wajib diisi**, klik ulang/retry
  **tidak boleh menggandakan** data. Kegagalan tidak boleh ditampilkan sebagai sukses.
- Tidak ada auto-block berdasarkan skor TI pada v1.

## Aturan keamanan (repo ini PUBLIC)

- JANGAN pernah commit `.env`, isi `secrets/`, API key, password, atau JWT secret.
  Yang boleh di-commit hanya `.env.example` dengan nilai placeholder (berawalan `ganti-`).
- Rahasia (password DB, API key AbuseIPDB/VirusTotal) dibaca dari **file Docker secret** (`*_FILE` → `/run/secrets/...`),
  bukan env biasa. Developer yang membuat file itu sendiri; **jangan pernah meminta developer menempelkan
  nilai rahasia ke chat**, dan jangan mencetak isi file di `secrets/`.
- API key pihak ketiga hanya ada di backend, hanya dikirim lewat **header** (bukan query string), tidak pernah ke frontend.
- JANGAN menulis password, token JWT, API key, atau header Authorization/`Key`/`x-apikey` ke log.
  Logger `httpx`/`httpcore` di level WARNING. Pesan error konfigurasi hanya menyebut nama variabel, bukan nilainya.
- Jangan menyimpan data kontak dari respons sumber (whois, RDAP, email/telepon) ke DB maupun fixture.
- Postgres TIDAK di-expose ke host (tanpa `ports:`). API di-bind ke `127.0.0.1` saat dev.
- Jangan matikan verifikasi TLS secara global (nanti untuk MISP self-signed, pakai file CA).
- Frontend: semua variabel `VITE_*` ikut ter-bundle ke browser, jadi **tidak boleh** berisi rahasia. Jangan mengisi
  `server.allowedHosts: true` di Vite (celah DNS rebinding).
- Frontend: kalau `npm audit` melaporkan advisory pada paket `vite` dengan severity apa pun, **jangan jalankan
  `npm run dev:lan`** sampai di-upgrade (advisory `server.fs` Vite berlaku saat dev server dibuka dengan `--host`).
- Jangan memanggil API eksternal (AbuseIPDB, VirusTotal, MISP) di pytest — gunakan mock/fixture.
  Panggilan API nyata hanya lewat skrip smoke yang dijalankan manual oleh developer (memakan kuota).

## Konvensi

- Semua timestamp disimpan `timestamptz` dalam UTC; respons API memakai ISO 8601 dengan offset WIB (+07:00).
- Swagger di `/docs` harus mendokumentasikan juga respons gagal (401/403/409/422/501/502).
- Log aplikasi ke stdout format JSON.
- Satu issue → satu branch (`feat/...`, `fix/...`, `docs/...`, `chore/...`) → PR ke `main` dengan `Closes #<n>`.
  `main` dilindungi ruleset: tidak ada push langsung.
- Commit kecil per tahap, gaya Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).
- Developer memakai shell **fish**: kalau memberi perintah, pastikan kompatibel fish
  (mis. `source .venv/bin/activate.fish`, `set -x VAR value`, `read -s` untuk input rahasia).

## Cara kerja yang diharapkan

1. Kerjakan task **per tahap** (skill `/kerjakan-tahap`). Setelah satu tahap selesai: jalankan pengecekan di bagian
   "Cek selesai", perbarui `TASK-xx-progress.md`, laporkan hasilnya, lalu **berhenti dan tunggu konfirmasi**.
   Jangan push atau membuka PR sebelum developer bilang lanjut.
2. Kerjakan hanya lingkup tahap itu. Temuan di luar lingkup dicatat sebagai known gap, bukan diperbaiki diam-diam.
3. Kalau ragu soal versi library/API, cek dokumentasi resmi; jangan menebak.
4. Kalau ada yang gagal, laporkan apa adanya beserta penyebabnya. Jangan menyembunyikan error.

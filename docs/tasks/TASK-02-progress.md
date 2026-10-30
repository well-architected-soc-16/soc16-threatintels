# TASK-02 — Progress

Diperbarui: 2026-10-30. Rujukan: [`TASK-02-sumber-reputasi-skor.md`](TASK-02-sumber-reputasi-skor.md), issue #20.

## Status per tahap

| Tahap | Isi | PR | Status |
|---|---|---|---|
| Rencana | Rencana TASK-02 dan keputusan grilling (Keputusan 7-14) | #19, #21 | Selesai, ter-merge |
| 0 | Konfigurasi sumber + API key sebagai secret | (belum dibuka) | Selesai di lokal, menunggu "push" dari developer |
| 1 | Adapter AbuseIPDB + VirusTotal, pemetaan status | - | Belum |
| 2 | Skor, label, flag, kontrak respons | - | Belum |
| 3 | Cache + pembatas kuota bersama | - | Belum |
| 4 | Uji API nyata + rapikan | - | Belum |

Hasil terakhir: `pytest` **271 passed**, `ruff check` dan `ruff format --check` bersih, `docker compose ps` `db` dan `api` `healthy`.

## Tahap 0

Dikerjakan di branch `feat/task-02-tahap-0-konfigurasi-sumber`. Tidak ada perubahan perilaku API; hanya konfigurasi dan pengaman.

- `httpx==0.28.1` dipindah dari `requirements-dev.txt` ke `requirements.txt`. Versi itu masih rilis stabil terbaru di PyPI (yang lebih baru hanya `1.0.dev*`), jadi pin tidak berubah.
- `core/config.py`: `SOURCES_MODE`, `ABUSEIPDB_API_KEY_FILE`, `VIRUSTOTAL_API_KEY_FILE`, `SOURCE_TIMEOUT_SECONDS`, `ABUSEIPDB_MAX_AGE_DAYS` (1-365), tiga batas kuota, dan tiga TTL cache, dengan default sesuai rencana. Batas kuota dan TTL harus positif.
- `core/secret_policy.py`: `load_api_key(path, variable)` (validasi file key, bagian (a) rencana) dan `SecretFileError`.
- Guard `SOURCES_MODE=live` "belum didukung" (bagian (b) rencana) adalah validator `Settings` tersendiri yang berjalan sesudah validasi file key. Cukup hapus validator itu di Tahap 3.
- `docker-compose.yml`: secret `abuseipdb_api_key` dan `virustotal_api_key` hanya untuk service `api`.
- `.env.example`: variabel baru dengan `SOURCES_MODE=mock`; tidak ada nilai key.
- `core/logging.py`: logger `httpx` dan `httpcore` dipaku di `WARNING`.
- README: langkah membuat file secret dan tabel konfigurasi.

### Keputusan dan penyimpangan dari rencana

1. **`chmod 644`, bukan `chmod 600 secrets/*.txt`** seperti di "Cek selesai" rencana. Kontainer `api` berjalan sebagai uid 10001 dan membaca file secret lewat bind mount yang mempertahankan pemilik dan mode dari host. File bermode 600 milik uid host tidak terbaca olehnya, dan perintah itu juga akan merusak `db_password.txt` yang sudah ada. Folder `secrets/` tetap `700`. Sejalan dengan README yang sudah ada. Teks "Cek selesai" di file rencana sudah dikoreksi menjadi `644` (lihat known gap 2).
2. **Validasi tambahan: isi file harus satu key** (ASCII yang tampak, tanpa spasi atau baris baru). Tidak tertulis di rencana. Alasannya: file berisi dua baris membuat httpx menolak header, dan pesan galat httpx memuat nilai header (yaitu key). Validasi di sini mencegah key sampai ke log di Tahap 1/3. Mudah dilepas bila tim tidak setuju.
3. **Pesan galat tidak memuat path file**, hanya nama variabel. Path memang bukan rahasia, tetapi aturan CLAUDE.md menyebut hanya nama variabel. `UnicodeDecodeError` juga sengaja tidak disambung (`from None`) karena memuat byte yang gagal didekode; ada test-nya.
4. **Path file key punya default** (`/run/secrets/...`), tidak wajib diisi. Alasan: konstruksi `Settings` di test yang sudah ada tidak perlu diubah, dan nilainya sama dengan yang dipasang compose. Compose tetap mengisi `*_FILE` di `environment`, meniru `DB_PASSWORD_FILE`.
5. **Semua masalah file key dilaporkan sekaligus** pada mode live (kedua variabel dalam satu pesan), supaya developer tidak memperbaiki satu per satu.
6. **Properti `abuseipdb_api_key` dan `virustotal_api_key` membaca file setiap kali diakses**, tidak di-cache. Hanya dimaksudkan untuk mode live; pada mock, file kosong akan ditolak properti ini. Tahap 1/3 memutuskan apakah perlu cache.

### Hasil gerbang

- `docker compose up -d --build` dan `up -d --force-recreate api` (karena `.env.example` berubah): `db` dan `api` `healthy`; `/health` OK.
- `pytest -q -p no:cacheprovider`: **271 passed**.
- `ruff check --no-cache .`: bersih. `ruff format --no-cache --check .`: 55 file sudah terformat.
- Uji negatif: `SOURCES_MODE=live` lewat kontainer sekali pakai (`docker compose run --rm --no-deps -e SOURCES_MODE=live api ...`; stack dev tidak diubah) gagal start. Karena file key masih kosong, pesannya muncul dari validasi file key dan hanya menyebut `SOURCES_MODE`, `ABUSEIPDB_API_KEY_FILE`, dan `VIRUSTOTAL_API_KEY_FILE`. Pesan "belum didukung" untuk file key valid dibuktikan oleh `test_start_live_dengan_key_valid_gagal_belum_didukung_tanpa_bocor` (start nyata via subprocess, key uji tidak muncul di keluaran), bukan lewat kontainer, karena itu membutuhkan key asli.
- `git status`: `.env` dan `secrets/` tidak muncul; pencarian pola rahasia pada diff hanya menemukan nama variabel, path, dan nilai uji fiktif.

### Test baru

- `tests/test_sources_config.py`: default, rentang, `load_api_key` (valid, hilang, folder, kosong, placeholder, bukan satu key, bukan UTF-8), mode mock menerima file apa pun, mode live (urutan (a) sebelum (b), nama variabel, tidak bocor), dan start nyata via subprocess.
- `tests/test_logging.py`: level `httpx`/`httpcore` tetap `WARNING` untuk `LOG_LEVEL` apa pun, request httpx (`MockTransport`) tidak menghasilkan log URL atau key, plus test kontrol yang membuktikan httpx memang mencatat URL tanpa pengaturan itu.
- `tests/test_env_example.py`: variabel sumber ada di `.env.example` dan dikenali `Settings` (karena `extra="ignore"` menyembunyikan salah ketik), `SOURCES_MODE=mock`, dan tidak ada variabel yang menampung key langsung.

## Known gaps

1. **Pengaturan awal bertambah dua file.** `docker compose up` gagal bila `secrets/abuseipdb_api_key.txt` atau `secrets/virustotal_api_key.txt` tidak ada (Keputusan 14). Developer yang sudah punya stack harus menjalankan `touch` sekali setelah pull. README sudah menjelaskan; CI nanti harus membuat kedua file itu juga.
2. ~~Teks "Cek selesai" Tahap 0 di file rencana memuat `chmod 600 secrets/*.txt`~~ **Selesai**: dikoreksi menjadi `chmod 644` dengan alasan singkat (lihat keputusan 1).
3. **Uji start `live` dengan file key valid lewat kontainer** baru bisa dilakukan setelah guard dicabut (Tahap 3); sebelum itu hanya dibuktikan lewat test subprocess.
4. **Peringatan deprecation Starlette `TestClient`** (`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`, dari `fastapi/testclient.py:1`) muncul di ringkasan pytest. **Sudah ada sebelum Tahap 0**: dicek 2026-10-30 dengan menjalankan test `main` (commit `1badd61`) di worktree sementara memakai image yang sama (fastapi 0.162.0, starlette 1.10.0, httpx 0.28.1; `requirements.txt` fastapi dan httpx identik dengan Tahap 0, httpx hanya pindah file): 209 passed, 1 warning, teks sama. Jadi bukan akibat Tahap 0. Belum diperbaiki.
   **Keputusan (developer, 2026-10-31):** Tahap 1 tetap memakai `httpx`. Migrasi ke `httpx2` dikerjakan sebagai issue terpisah setelah demo, karena nama logger dan trust store SSL berubah. Nama logger berubah berarti pengaman logging (`httpx`/`httpcore` dipaku di `WARNING`, lihat Tahap 0) tidak lagi mengenai logger client baru; trust store SSL berubah berarti perilaku verifikasi TLS ke sumber dan nanti ke MISP perlu diuji ulang. Sampai migrasi, warning ini dibiarkan.

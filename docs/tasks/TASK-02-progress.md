# TASK-02 — Progress

Diperbarui: 2026-10-31. Rujukan: [`TASK-02-sumber-reputasi-skor.md`](TASK-02-sumber-reputasi-skor.md), issue #20.

## Status per tahap

| Tahap | Isi | PR | Status |
|---|---|---|---|
| Rencana | Rencana TASK-02 dan keputusan grilling (Keputusan 7-14) | #19, #21 | Selesai, ter-merge |
| 0 | Konfigurasi sumber + API key sebagai secret | #22 | Selesai, ter-merge |
| 1 | Adapter AbuseIPDB + VirusTotal, pemetaan status | (belum dibuka) | Selesai di lokal, menunggu "push" dari developer |
| 2 | Skor, label, flag, kontrak respons | - | Belum |
| 3 | Cache + pembatas kuota bersama | - | Belum |
| 4 | Uji API nyata + rapikan | - | Belum |

Hasil terakhir (Tahap 1): `pytest` **492 passed**, `ruff check` dan `ruff format --check` bersih, `docker compose ps` `db` dan `api` `healthy`.

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

## Tahap 1

Dikerjakan di branch `feat/task-02-tahap-1-adapter-sumber`. Adapter belum dipanggil dari `POST /checks`: `collect_sources`, `assess()`, dan guard `SOURCES_MODE=live` sengaja tidak disentuh (penyambungan = Tahap 2, guard dicabut di Tahap 3). Test `test_checks` yang menuntut `SKIPPED/ADAPTER_NOT_IMPLEMENTED` tetap hijau.

Modul baru di `backend/app/services/sources/`:
- `base.py`: `SourceStatus`, `SourceReason`, `SourceResult` (dataclass beku), Protocol `ReputationSource`, konstanta flag.
- `_common.py`: bagian bersama adapter live (pengambilan HTTP, klasifikasi status, validasi ulang IP).
- `abuseipdb.py`, `virustotal.py`: adapter live (`httpx.Client` disuntikkan) dan fungsi pemetaan murni `map_response_body`.
- `mock.py`: `MockSource` dan tabel IP demo. Payload sintetis dilewatkan ke fungsi pemetaan adapter asli.

Fixture di `tests/fixtures/sources/` (17 file): 2 respons nyata 29 Okt 2026 (IP `118.25.6.39`, apa adanya dari lampiran rencana) dan sisanya simulasi (IP dokumentasi `203.0.113.7`); nama file memuat `nyata` atau `simulasi`.

### Keputusan dan penyimpangan dari rencana

1. **`SourceResult` punya dua field di luar daftar rencana**: `flags` (tuple) dan `retry_after_seconds`. Rencana mewajibkan flag `NO_VENDOR_OPINION` dan `SUMBER_SIMULASI` serta "simpan `Retry-After`", tetapi daftar field-nya tidak punya tempat untuk itu.
2. **Bab 3 dokumen riset tidak ada di repo.** Pemetaan diturunkan dari butir 3-5 rencana Tahap 1, bukan dari Bab 3 langsung. Developer perlu mencocokkan dengan PDF `riset-reputasi-ip-revisi-1.1` (lihat known gap 5).
3. **Hanya `abuseConfidenceScore` yang wajib** pada AbuseIPDB (integer 0-100; `bool`, float, string, null ditolak). `totalReports`, `numDistinctUsers`, `lastReportedAt`, `isWhitelisted` yang hilang atau salah tipe menjadi null di bukti dan tidak menggagalkan skor. Rencana hanya menyebut "field wajib" tanpa daftar.
4. **VirusTotal: `last_analysis_stats` hilang atau bukan objek = `INVALID_RESPONSE`; objek kosong `{}` = `INSUFFICIENT_DATA`.** Rencana hanya mendefinisikan yang kedua. Nilai statistik yang ada harus integer >= 0 (bukan `bool`); kunci yang tidak ada dihitung 0. Hanya lima kunci (`malicious`, `suspicious`, `harmless`, `undetected`, `timeout`) yang disalin ke bukti; kunci lain diabaikan.
5. **`reason` null untuk status non-ERROR** (`NO_RECORD`, `INSUFFICIENT_DATA`, `OK_*`). Rencana tidak mendefinisikan kode alasan untuk status itu; tidak ada kode karangan.
6. **Status HTTP diklasifikasi sebelum body dibaca.** JSON hanya diparse untuk 200 (dan 404 VirusTotal), jadi body rusak pada 401 tetap `AUTH`. 404 VirusTotal tanpa `error.code == "NotFoundError"` (atau body tidak terbaca) = `UPSTREAM`. `NotFoundError` pada status selain 404 bukan `NO_RECORD`.
7. **Redirect tidak diikuti** (`follow_redirects=False` dan `timeout=` dipasang per request, bukan hanya di client). httpx meneruskan header kustom seperti `Key`/`x-apikey` ke tujuan redirect, dan client bisa disuntikkan. 3xx = `UPSTREAM`.
8. **IP divalidasi ulang di dalam adapter** (`require_public_ip`, dipakai juga mock). IP tidak valid atau tidak publik melempar `ValueError` tanpa request. Alasan: VirusTotal menaruh IP di path URL. Hasilnya, adapter memakai IP kanonik (spasi dipangkas).
9. **Parameter `verbose` AbuseIPDB tidak dikirim**: ia mengembalikan laporan individual dengan komentar teks bebas yang bisa memuat data pribadi.
10. **Teks exception httpx tidak pernah disalin ke hasil** (hanya `TIMEOUT` atau `UPSTREAM`); pesannya bisa memuat nilai header. Test memakai exception yang pesannya memuat key palsu.
11. **Mock**: setiap hasil, termasuk `ERROR`, berflag `SUMBER_SIMULASI` dan berbukti `"simulasi": true`; `http_status` dan `duration_ms` null (bukan panggilan HTTP). Sumber yang tidak disebut pada suatu IP demo memakai hasil bawaan (skor 0), mis. V pada `1.0.0.1`. `lastReportedAt` dan `last_analysis_date` sengaja tidak diisi (`source_time` null) supaya tidak tampak seperti tanggal nyata. Test mock hanya memeriksa hasil **per sumber**; skor gabungan dan label di kolom kanan tabel rencana adalah keluaran Tahap 2.
12. **Tidak ada factory `get_sources()`** dan tidak ada pengaturan masa hidup `httpx.Client`; keduanya ikut penyambungan di Tahap 2/3. Properti `abuseipdb_api_key` / `virustotal_api_key` (keputusan Tahap 0 nomor 6) belum dipakai siapa pun.
13. **Keputusan httpx dari Tahap 0 diikuti**: adapter memakai `httpx` (bukan `httpx2`). Lihat known gap 4.

### Hasil gerbang

- `docker compose up -d --build`: `db` dan `api` `healthy`.
- `pytest -q -p no:cacheprovider`: **492 passed** (Tahap 0: 271; 221 test baru), 1 warning (known gap 4).
- `ruff check --no-cache .`: bersih. `ruff format --no-cache --check .`: 66 file sudah terformat.
- Uji mutasi manual (salinan kode di luar repo, tidak di-commit): 10 perubahan sengaja ke kode (redirect diikuti, `bool` dianggap integer, `min(100, ...)` dihapus, timeout per request dihapus, guard IP dihapus, 401 jadi `UPSTREAM`, error membawa skor 0, key di query string, mock tanpa flag simulasi, nol laporan jadi `NO_RECORD`) masing-masing menggagalkan minimal 2 test.
- `git status --porcelain`: tidak ada `.env` atau `secrets/`. Pencarian pola rahasia pada diff hanya menemukan nama variabel dan key uji palsu `kunci-uji-palsu-xyz`. Fixture bersih dari `whois`, `rdap`, email, dan telepon (juga dijaga `tests/test_sources_fixtures.py`).

### Test baru

- `test_sources_abuseipdb.py`, `test_sources_virustotal.py`: satu test (atau satu kasus parametrize) per baris pemetaan butir 3-5 rencana; bentuk request (header, parameter, timeout, tanpa key di URL); key tidak muncul di URL, `caplog` level DEBUG, `repr(result)`, `asdict(result)`, `repr(adapter)` pada jalur sukses dan error; IP tidak valid tidak memicu request.
- `test_sources_mock.py`: satu kasus per baris tabel IP demo, IP di luar tabel, flag simulasi pada semua hasil, tanpa jaringan (`socket.connect` dan `getaddrinfo` diblokir).
- `test_sources_fixtures.py`: nama berlabel nyata/simulasi, JSON valid, bebas data kontak.
- `tests/sources_support.py`: alat bantu (`MockTransport`, pemuat fixture, invarian "hanya `OK_*` yang boleh membawa skor").

## Known gaps

1. **Pengaturan awal bertambah dua file.** `docker compose up` gagal bila `secrets/abuseipdb_api_key.txt` atau `secrets/virustotal_api_key.txt` tidak ada (Keputusan 14). Developer yang sudah punya stack harus menjalankan `touch` sekali setelah pull. README sudah menjelaskan; CI nanti harus membuat kedua file itu juga.
2. ~~Teks "Cek selesai" Tahap 0 di file rencana memuat `chmod 600 secrets/*.txt`~~ **Selesai**: dikoreksi menjadi `chmod 644` dengan alasan singkat (lihat keputusan 1).
3. **Uji start `live` dengan file key valid lewat kontainer** baru bisa dilakukan setelah guard dicabut (Tahap 3); sebelum itu hanya dibuktikan lewat test subprocess.
4. **Peringatan deprecation Starlette `TestClient`** (`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`, dari `fastapi/testclient.py:1`) muncul di ringkasan pytest. **Sudah ada sebelum Tahap 0**: dicek 2026-10-30 dengan menjalankan test `main` (commit `1badd61`) di worktree sementara memakai image yang sama (fastapi 0.162.0, starlette 1.10.0, httpx 0.28.1; `requirements.txt` fastapi dan httpx identik dengan Tahap 0, httpx hanya pindah file): 209 passed, 1 warning, teks sama. Jadi bukan akibat Tahap 0. Belum diperbaiki.
   **Keputusan (developer, 2026-10-31):** Tahap 1 tetap memakai `httpx`. Migrasi ke `httpx2` dikerjakan sebagai issue terpisah setelah demo, karena nama logger dan trust store SSL berubah. Nama logger berubah berarti pengaman logging (`httpx`/`httpcore` dipaku di `WARNING`, lihat Tahap 0) tidak lagi mengenai logger client baru; trust store SSL berubah berarti perilaku verifikasi TLS ke sumber dan nanti ke MISP perlu diuji ulang. Sampai migrasi, warning ini dibiarkan.
5. **Pemetaan Tahap 1 belum dicocokkan dengan Bab 3 dokumen riset.** PDF `riset-reputasi-ip-revisi-1.1` tidak ada di repo, jadi pemetaan diturunkan dari butir 3-5 rencana. Keputusan Tahap 1 nomor 3-6 mengisi celah yang tidak tertulis di rencana (field wajib AbuseIPDB, `stats` hilang vs kosong, `reason` null). Developer perlu mencocokkannya dengan Bab 3 sebelum Tahap 2.
6. **Test `assess()` untuk status non-`OK_*` belum ada.** Keputusan 6 rencana ("tambahkan test-nya") tidak ditempatkan pada tahap mana pun, dan Tahap 1 tidak menyentuh `ip_checks.assess()`. Usul: kerjakan di Tahap 2, saat `assess()` dipakai oleh `SourceResult`.
7. **Belum ada pemakai `SourceResult` di luar test.** Tidak ada `as_dict`/serialisasi untuk `evidence_summary` dan `source_time` ke respons API atau DB (kontrak respons = Tahap 2, kolom cache = Tahap 3).

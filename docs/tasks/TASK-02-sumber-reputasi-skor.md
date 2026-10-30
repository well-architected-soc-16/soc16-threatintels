# TASK-02 — Sumber Reputasi (AbuseIPDB + VirusTotal), Skor, dan Cache

> Taruh file ini di `docs/tasks/TASK-02-sumber-reputasi-skor.md`.
> Prompt ke Claude Code: **"Baca CLAUDE.md dan docs/tasks/TASK-02-sumber-reputasi-skor.md. Kerjakan Tahap 0 saja, jalankan Cek selesai, lalu berhenti dan laporkan."**
> Ulangi untuk Tahap 1, 2, dst. Satu tahap = satu PR kecil (`Refs #20` di PR tahap, `Closes #20` di PR Tahap 4).

Issue induk: **#20**. Branch kerja: satu branch per tahap (`feat/task-02-tahap-<n>-<ringkas>`), mengikuti kebiasaan TASK-01.
Keputusan tambahan hasil sesi grilling (29 Okt 2026) ada di Keputusan nomor 7–14 dan bagian "Known gaps".
Dasar aturan: dokumen tim **`riset-reputasi-ip-revisi-1.1.pdf`** Bab 3 (pemetaan status), Bab 4 (rumus & label),
Bab 5 (cache, kuota, koneksi keluar), Bab 6 (kontrak API), Bab 9 (pengujian).
Di luar lingkup task ini: frontend, MISP live, CI/CD, deploy ke soc-ir, sumber tambahan (ThreatFox, OTX, GreyNoise, dll).

## Fakta yang sudah diverifikasi (29 Okt 2026, akun tim)

| Sumber | Endpoint | Auth | Kuota akun tim | Bukti |
|---|---|---|---|---|
| AbuseIPDB | `GET https://api.abuseipdb.com/api/v2/check` (`ipAddress`, `maxAgeInDays=30`) | header `Key` + `Accept: application/json` | check **1.000/hari** (header `X-RateLimit-Limit: 1000`) | curl manual, HTTP 200 |
| VirusTotal | `GET https://www.virustotal.com/api/v3/ip_addresses/{ip}` | header `x-apikey` | **4/menit, 500/hari, 15.500/bulan** (dashboard akun); dilarang untuk business workflow/produk komersial | curl manual, HTTP 200 |

Dokumentasi resmi untuk dicek ulang bila ragu (jangan menebak):
- AbuseIPDB API v2: https://docs.abuseipdb.com/ (error berupa array `errors[]` berisi `detail` + `status`; 429 saat kuota harian habis; header `Retry-After`, `X-RateLimit-*`; `isWhitelisted` **bisa null**)
- VirusTotal errors: https://docs.virustotal.com/reference/errors (body `{"error":{"code","message"}}`; 401 `WrongCredentialsError`/`AuthenticationRequiredError`/`UserNotActiveError`; 403 `ForbiddenError`; 404 `NotFoundError`; 429 `QuotaExceededError`/`TooManyRequestsError`; 503 `TransientError`; 504 `DeadlineExceededError`; kuota harian reset 00:00 UTC)
- VirusTotal IP object: https://docs.virustotal.com/reference/ip-object

## Keputusan yang dipakai task ini (usulan, dikonfirmasi tim)

1. **API key disimpan sebagai Docker secret (file), bukan env biasa**, sama seperti password DB. Alasan: dokumentasi Docker
   memperingatkan env var bisa terekspos tanpa sengaja (terlihat semua proses, ikut tercetak saat debug).
2. **`SOURCES_MODE=mock|live`** (mirip `MISP_MODE`). Default `mock` di `.env.example`. Mode mock **wajib diberi label
   simulasi** di hasil (flag `SUMBER_SIMULASI`), tidak boleh tampak seperti data nyata.
3. **TTL cache** mengikuti usulan Bab 5 (OK_SIGNAL 6 jam, OK_NO_SIGNAL 24 jam, NO_RECORD 1 jam, ERROR/INSUFFICIENT_DATA
   tidak di-cache), dibuat bisa diatur lewat env. Dokumen menyebut TTL **belum disepakati tim**; nilai ini dipakai sementara.
4. **Kuota internal habis → sumber `SKIPPED` alasan `QUOTA_INTERNAL`**, request HTTP tidak dikirim, dan request user
   tidak dibuat menunggu sampai menit berikutnya. (Bab 3: SKIPPED untuk "batas permintaan internal".)
5. **Pemanggilan dua sumber boleh berurutan** (Bab 5 hanya *membolehkan* paralel). Timeout 10 detik per sumber.
6. **Known gap #4 TASK-01 diselesaikan oleh Bab 3**: hanya `OK_SIGNAL` dan `OK_NO_SIGNAL` yang menambah cakupan.
   `NO_RECORD`, `INSUFFICIENT_DATA`, `ERROR`, `SKIPPED` tidak. Perilaku `assess()` sekarang sudah benar; tambahkan test-nya.
7. **Mode dicatat di `source_cache` dan `source_calls`** (kolom `mode` teks, `CHECK (mode IN ('mock','live'))`).
   Unique cache menjadi `(source, ip, params_key, mode)`; mode live **tidak pernah membaca** baris `mock`, sehingga data
   simulasi tidak bisa muncul sebagai hasil live setelah `.env` diubah. Panggilan mock tetap dicatat di `source_calls`
   (bukti) tetapi limiter **hanya menghitung `mode = 'live'`**, jadi mock tidak pernah `SKIPPED/QUOTA_INTERNAL`.
8. **`SOURCES_MODE=live` ditolak aplikasi ("belum didukung") sampai Tahap 3 selesai.** Alasan: Tahap 2 menyambungkan
   sumber ke `POST /checks`, sedangkan limiter baru ada di Tahap 3. Guard dicabut di Tahap 3.
9. **Mock memakai tabel IP demo terdokumentasi** (lihat Tahap 1); IP di luar tabel mendapat hasil default. README **wajib**
   menyatakan bahwa hasil untuk IP resolver itu fiktif dan menjelaskan kenapa hasil simulasi tidak boleh masuk MISP
   atau blocklist.
10. **Check ber-flag `SUMBER_SIMULASI` tidak boleh dikirim ke MISP**: `POST /iocs/misp` menjawab 422 (Tahap 2), mengikuti
    pola guard `INPUT_DITOLAK`.
11. **Reset kuota harian AbuseIPDB.** Observasi 29 Okt 2026: `X-RateLimit-Reset: 1793318400` = 30 Okt 2026 00:00 UTC.
    Limiter memakai header `X-RateLimit-Reset` bila tersedia, 00:00 UTC sebagai cadangan.
12. **Target demo 4 Nov 2026.** WAJIB: Tahap 0–2 ter-merge sebelum demo. TAMBAHAN: Tahap 3 hanya bila Tahap 0–2 selesai
    cepat, tanpa terburu-buru. Saat demo, hasil mode mock disebut "simulasi", dan bukti uji API nyata 29 Okt (curl
    AbuseIPDB & VirusTotal, HTTP 200, kuota 1.000/hari dan 500/hari) ditunjukkan terpisah.
13. **Issue dan PR.** Satu issue induk (#20), satu branch dan PR per tahap. PR tahap memakai `Refs #20`; hanya PR Tahap 4
    memakai `Closes #20`.
14. **File secret key selalu harus ada** (compose gagal `up` bila file sumber secret tidak ada). Untuk mode mock cukup file
    kosong (`touch`); README dan CI membuatnya. `SOURCES_MODE` bersifat **global** (satu saklar untuk kedua sumber).

---

## Tahap 0 — Konfigurasi sumber + API key sebagai secret

**Kerjakan:**
1. Pindahkan `httpx` dari `requirements-dev.txt` ke `requirements.txt` (dipakai runtime). Cek versi terbaru di PyPI, pin `==`.
2. `core/config.py` tambah: `SOURCES_MODE` (`mock`|`live`, default `mock`), `ABUSEIPDB_API_KEY_FILE`, `VIRUSTOTAL_API_KEY_FILE`,
   `SOURCE_TIMEOUT_SECONDS` (default 10), `ABUSEIPDB_MAX_AGE_DAYS` (default 30, valid 1–365 sesuai docs),
   batas kuota: `ABUSEIPDB_DAILY_LIMIT` (1000), `VT_DAILY_LIMIT` (500), `VT_PER_MINUTE_LIMIT` (4),
   TTL: `CACHE_TTL_OK_SIGNAL_HOURS` (6), `CACHE_TTL_OK_NO_SIGNAL_HOURS` (24), `CACHE_TTL_NO_RECORD_HOURS` (1).
   - Key dibaca dari isi file (seperti `db_password`), disimpan sebagai `SecretStr`, `.strip()`.
   - **Jika `SOURCES_MODE=live`**: file key wajib ada, tidak kosong, dan bukan placeholder (`secret_policy.is_placeholder`).
     Kalau tidak → aplikasi gagal start dengan pesan yang **hanya menyebut nama variabel**, tanpa nilai (pola issue #17).
   - Jika `mock`: isi file key tidak dipakai dan boleh kosong, tetapi **file-nya tetap harus ada** (Keputusan 14).
   - **Pisahkan dua hal**: (a) validasi file key sebagai fungsi tersendiri (file hilang, kosong, placeholder, valid) yang
     dites langsung, tidak lewat `SOURCES_MODE`; (b) guard `SOURCES_MODE=live` → aplikasi gagal start dengan pesan
     "belum didukung" (Keputusan 8), dijalankan sesudah (a) dan dengan test sendiri. Pesan keduanya hanya menyebut
     nama variabel, tanpa nilai. Guard (b) dicabut di Tahap 3.
3. `docker-compose.yml`: tambah secret `abuseipdb_api_key` (`./secrets/abuseipdb_api_key.txt`) dan
   `virustotal_api_key` (`./secrets/virustotal_api_key.txt`), hanya untuk service `api` (bukan `db`).
4. `.env.example`: tambah variabel di atas dengan `SOURCES_MODE=mock` dan path `/run/secrets/...`. Tidak ada nilai key.
5. `core/logging.py`: set logger `httpx` dan `httpcore` ke level `WARNING` (log INFO httpx mencetak URL request).
6. README: langkah membuat file secret key (perintah fish, lihat Cek selesai), termasuk file kosong untuk mode mock.
   Pastikan `secrets/` tetap di `.gitignore`.

**Cek selesai** (developer menjalankan sendiri; **jangan pernah menempel API key ke Claude Code**):
```fish
# mode mock: file kosong sudah cukup (file-nya harus ada agar compose bisa up)
touch secrets/abuseipdb_api_key.txt secrets/virustotal_api_key.txt
# (opsional, untuk Tahap 3/4) isi dengan key dari Bitwarden tanpa menampilkannya:
#   read -s key; printf '%s' $key > secrets/abuseipdb_api_key.txt; set -e key
#   read -s key; printf '%s' $key > secrets/virustotal_api_key.txt; set -e key
chmod 644 secrets/*.txt   # bukan 600: kontainer api (uid 10001) harus bisa membaca bind mount; perlindungan ada di folder secrets/ (700)
git status                                   # secrets/ TIDAK muncul
docker compose up -d --build && docker compose ps
docker compose exec api python -m pytest -q -p no:cacheprovider   # tetap hijau
docker compose exec api ruff check --no-cache .
docker compose exec api ruff format --no-cache --check .
```
Uji negatif: set `SOURCES_MODE=live` di `.env` → kontainer gagal start dengan pesan "belum didukung" yang hanya menyebut
nama variabel, tanpa nilai. (Uji start live yang sebenarnya, termasuk file key kosong/placeholder lewat kontainer,
dilakukan di Tahap 3 setelah guard dicabut; sebelum itu validasi key dibuktikan oleh test fungsi.)

---

## Tahap 1 — Adapter + pemetaan status (Bab 3)

**Kerjakan:**
1. `services/sources/base.py`: `Protocol ReputationSource` dengan `name` dan `fetch(ip) -> SourceResult` (dataclass internal).
   Field hasil per sumber (Bab 6): `source`, `status`, `reason` (= `error_code`), `normalized_score` (A atau V, null bila tidak dinilai),
   `evidence_summary` (dict), `source_time`, `source_time_type` (`last_report`|`last_analysis`|null), `retrieved_at`,
   `expires_at`, `from_cache`, plus `http_status` dan `duration_ms` untuk bukti.
2. `services/sources/abuseipdb.py` dan `services/sources/virustotal.py` memakai `httpx.Client` yang **bisa disuntikkan**
   (untuk test pakai `httpx.MockTransport`, tanpa dependency tambahan). Key **hanya di header**, tidak pernah di query string.
   Timeout dari config.
3. Pemetaan **AbuseIPDB** (Bab 3):
   - 200 + `data.abuseConfidenceScore` integer 0–100: `>0` → `OK_SIGNAL` (A = skor); `=0` → `OK_NO_SIGNAL` (A = 0),
     **termasuk saat `totalReports=0`** (nol laporan ≠ `NO_RECORD`).
   - `evidence_summary`: `abuseConfidenceScore`, `totalReports`, `numDistinctUsers`, `lastReportedAt`, `isWhitelisted`.
     `source_time = lastReportedAt` (boleh null; null **tidak** menggagalkan skor), `source_time_type = last_report`.
   - Field wajib hilang / bukan angka / di luar 0–100 / JSON rusak → `ERROR` + `INVALID_RESPONSE`.
4. Pemetaan **VirusTotal** (Bab 3):
   - 200 + `data.attributes.last_analysis_stats` valid. Hitung `non_timeout = malicious + suspicious + harmless + undetected`.
     - stats kosong, atau `non_timeout == 0` (semua timeout) → `INSUFFICIENT_DATA`.
     - `malicious>0` atau `suspicious>0` → `OK_SIGNAL`, `V = min(100, 8×malicious + 4×suspicious)`.
     - selain itu → `OK_NO_SIGNAL`, V = 0. Jika `harmless == 0` dan hanya `undetected > 0` → tambah flag `NO_VENDOR_OPINION`.
   - `evidence_summary`: isi `last_analysis_stats` saja. `source_time = last_analysis_date` (epoch → UTC),
     `source_time_type = last_analysis`. **Jangan simpan** `whois`, `rdap`, `last_analysis_results` (besar + data kontak).
   - 404 dengan `error.code == "NotFoundError"` → `NO_RECORD`. 404 tanpa kode itu → `ERROR` + `UPSTREAM`
     (Bab 3: pastikan objek tidak ditemukan, bukan URL salah).
5. Pemetaan **error HTTP** (kedua sumber): 401/403 → `ERROR` + `AUTH`; 429 → `ERROR` + `RATE_LIMIT` (simpan `Retry-After` bila ada);
   timeout httpx → `ERROR` + `TIMEOUT`; 5xx / koneksi gagal / status tak terduga → `ERROR` + `UPSTREAM`.
   **Error tidak pernah menjadi skor 0.**
6. `services/sources/mock.py`: adapter mock deterministik (tanpa jaringan) untuk `SOURCES_MODE=mock`;
   `evidence_summary` diberi `"simulasi": true`. Skenario dipilih lewat **tabel IP demo** di bawah (IP resolver publik
   terkenal, supaya hasil "berbahaya" yang jelas palsu tidak mencoreng pihak kecil). IP di luar tabel mendapat hasil
   default: kedua sumber `OK_NO_SIGNAL` (0/0, `RENDAH`, `COMPLETE`). Semua hasil tetap ber-flag `SUMBER_SIMULASI`.
   Pemetaan IP ke skenario di bawah adalah usulan dan boleh disesuaikan tim; angkanya mengikuti contoh Bab 4/9.

   | IP (resolver publik) | AbuseIPDB / VirusTotal | Hasil yang diharapkan |
   |---|---|---|
   | `1.1.1.1` | 90 / 80 (`malicious=10`) | 85,5 `SANGAT_TINGGI`, `COMPLETE` |
   | `1.0.0.1` | 90 / 0 | 49,1 `PERLU_PEMERIKSAAN` + `HASIL_BERBEDA` |
   | `8.8.8.8` | 90 / `ERROR` `TIMEOUT` | null, `DATA_TERBATAS`, 1/2 |
   | `8.8.4.4` | `ERROR` `TIMEOUT` / `NO_RECORD` | null, `TIDAK_TERSEDIA`, 0/2 |
   | `9.9.9.9` | 90 / 80, `isWhitelisted=true` | 85,5 + `WHITELISTED` |
   | `149.112.112.112` | 0 / semua `undetected` | 0,0 `COMPLETE` + `NO_VENDOR_OPINION` |
   | `208.67.222.222` | 0 / semua `timeout` (`INSUFFICIENT_DATA`) | null, `DATA_TERBATAS`, 1/2 |

   README wajib menjelaskan: hasil untuk IP-IP ini **fiktif** (bukan reputasi sebenarnya dari resolver tersebut), dan hasil
   simulasi **tidak boleh** dimasukkan ke MISP atau blocklist karena bukan data nyata.
7. Fixture di `tests/fixtures/sources/`, masing-masing berlabel di nama/isi apakah **nyata (disanitasi)** atau **simulasi**:
   - Nyata, 29 Okt 2026, IP `118.25.6.39` (sudah disanitasi, lihat lampiran di bawah).
   - Simulasi (Bab 9): skor 0, nol laporan, objek tidak ditemukan, statistik kosong, all-undetected, all-timeout,
     field hilang, 401, 403, 429 (dengan `Retry-After`), timeout, JSON rusak.

**Cek selesai:** `docker compose exec api pytest -q` hijau. Ada satu test per baris tabel Bab 3. Test memastikan
key tidak muncul di query string, log (`caplog`), maupun hasil adapter (pakai key palsu, mis. `kunci-uji-palsu-xyz`).

---

## Tahap 2 — Skor, label, flag, dan kontrak respons (Bab 4 & 6)

**Kerjakan:**
1. `services/scoring.py`:
   - `combined = (30×A + 25×V) / 55`, **hanya jika kedua sumber** `OK_SIGNAL`/`OK_NO_SIGNAL`; selain itu `None`.
   - `indication` dari nilai **sebelum pembulatan**: `<25` `RENDAH`, `25–<50` `PERLU_PEMERIKSAAN`, `50–<75` `TINGGI`,
     `75–100` `SANGAT_TINGGI`; `None` bila skor null.
   - Flag: `HASIL_BERBEDA` jika keduanya tersedia dan `|A−V| ≥ 50`; `NO_VENDOR_OPINION` (dari VT);
     `WHITELISTED` jika `isWhitelisted == true` (**tidak memangkas skor**; null → tidak ada flag);
     `SUMBER_SIMULASI` jika ada hasil dari adapter mock.
   - `scoring_version` tetap `v1-percobaan`.
2. `ip_checks.assess()` memakai scoring di atas. DB menyimpan `risk_score` presisi penuh; **respons API membulatkan 1 desimal**.
   `indication` dihitung dari nilai tersimpan saat membaca (tidak perlu kolom/migrasi baru).
3. `schemas/check.py`: `SourceResult` diperluas dengan field Tahap 1 (waktu ditampilkan WIB sesuai konvensi);
   `CheckOut` tambah `indication`. Pertahankan nama field `source` (sudah dipakai TASK-01). Data lama di `ip_checks.sources`
   (hanya `source/status/reason`) harus tetap terbaca → field baru opsional.
4. Router `POST /checks` memanggil `collect_sources()` versi baru. Audit log mencatat status per sumber, **tanpa** evidence/key.
5. Guard MISP (Keputusan 10): `POST /iocs/misp` menjawab **422** untuk check yang flag-nya memuat `SUMBER_SIMULASI`, dengan pesan
   yang jelas. Tidak ada baris `ioc_submissions` (bahkan bukan `pending`), klien MISP tidak dipanggil, tidak ada audit `ioc_submit`.
   Letakkan di samping guard `INPUT_DITOLAK` (`routers/iocs.py`).

**Cek selesai:** test Bab 9 lulus:
- `12 malicious → V=96`, `13 → 100`.
- Contoh Bab 4: `90/80 → 85,5`, `90/0 → 49,1 + HASIL_BERBEDA`, `90/timeout → null, DATA_TERBATAS, 1/2`,
  `0/0 → 0,0, COMPLETE`, `NO_RECORD/timeout → null, TIDAK_TERSEDIA, 0/2`, `90/80 + whitelist → 85,5 + WHITELISTED`.
- Batas label tepat di 25, 50, 75, dan kasus 74,96 (tampil `75.0` tapi label `TINGGI`).
- Data respons nyata 29 Okt (`A=7`, `V=0`) → `3,8`, `RENDAH`, `COMPLETE`, `2/2`, tanpa `HASIL_BERBEDA`.
- Check ber-flag `SUMBER_SIMULASI` dikirim ke `POST /iocs/misp` → 422, tanpa baris submission, klien MISP tidak dipanggil.
  Uji mutasi (guard dihapus) membuat test ini gagal. Check tanpa flag itu tetap bisa dikirim.

---

## Tahap 3 — Cache + pembatas kuota bersama (Bab 5)

**Kerjakan:**
1. Migrasi `0004`: tabel `source_cache` dan `source_calls`.
   - `source_cache`: `source`, `ip`, `params_key` (AbuseIPDB: `maxAgeInDays=30`; VT: `""`), `mode` (`mock`|`live`, CHECK),
     `status`, `normalized_score`, `evidence_summary` (JSONB), `source_time`, `source_time_type`, `retrieved_at`, `expires_at`.
     UNIQUE (`source`, `ip`, `params_key`, `mode`), upsert. Mode live **tidak pernah membaca** baris `mock` (Keputusan 7).
   - `source_calls` (log setiap request keluar = bukti + dasar hitung kuota): `source`, `mode` (`mock`|`live`, CHECK),
     `called_at`, `http_status`, `result_status`, `reason`, `duration_ms`, `retry_after_seconds`. **Tanpa** key, header, atau body.
2. Alur per sumber: cache masih berlaku → pakai (`from_cache=true`, `retrieved_at` asli **tidak diubah**).
   Kedaluwarsa → tidak dipakai menghitung skor baru. `ERROR`/`INSUFFICIENT_DATA` tidak disimpan ke cache.
   Saat satu sumber kedaluwarsa, hanya sumber itu yang diambil ulang.
3. Pembatas kuota **bersama untuk semua user** (bukan per user), berbasis tabel `source_calls`:
   - Dalam satu transaksi dengan `pg_advisory_xact_lock` per sumber: hitung panggilan **`mode = 'live'`** 60 detik terakhir
     (VT ≤ 4) dan sejak reset harian (VT ≤ 500, AbuseIPDB ≤ 1000), cek cooldown dari `Retry-After` terakhir, lalu **reservasi**
     dengan menyisipkan baris `source_calls` sebelum request dikirim. Request HTTP dijalankan **di luar** lock, lalu barisnya
     diperbarui. Panggilan `mode = 'mock'` dicatat tetapi tidak pernah dihitung.
   - Reset harian: VT 00:00 UTC. AbuseIPDB memakai header `X-RateLimit-Reset` dari respons terakhir bila ada, 00:00 UTC
     sebagai cadangan (Keputusan 11).
   - Melebihi batas atau masih cooldown → `SKIPPED` + `QUOTA_INTERNAL`, tanpa request keluar.
   - 429 → tidak ada retry di request yang sama; sumber itu cooldown sesuai `Retry-After` (bila tidak ada, 60 detik).
4. **Cabut guard `SOURCES_MODE=live`** (Keputusan 8) dan buktikan lewat uji start kontainer mode live: file key hilang/kosong/
   placeholder → gagal start, pesan hanya menyebut nama variabel; file key valid (key palsu) → start normal.
   Mode mock tidak boleh menyentuh `SKIPPED/QUOTA_INTERNAL`.
5. Cek ulang setelah tahap ini: input yang ditolak validasi tetap **tidak** menyentuh cache, limiter, maupun jaringan.

**Cek selesai:** test:
- cek IP yang sama dua kali → panggilan kedua `from_cache=true`, adapter tidak dipanggil, `retrieved_at` sama.
- cache kedaluwarsa (manipulasi waktu) → diambil ulang; `ERROR` tidak pernah keluar dari cache.
- 5 cek IP berbeda dalam 1 menit → cek ke-5 VT `SKIPPED/QUOTA_INTERNAL`, AbuseIPDB tetap jalan, status `DATA_TERBATAS`.
- 10 request paralel tidak menembus batas 4/menit (pola uji paralel TASK-01 Tahap 4).
- setelah 429 + `Retry-After`, sumber itu di-skip sampai cooldown habis.
- cache `mock` tidak pernah dibaca saat mode live (baris simulasi ada, mode live tetap mengambil dari sumber).
- panggilan `mock` banyak kali (> 4 dalam semenit) tidak pernah menghasilkan `SKIPPED/QUOTA_INTERNAL`.
- reset harian AbuseIPDB mengikuti `X-RateLimit-Reset`; tanpa header, 00:00 UTC.

---

## Tahap 4 — Uji API nyata + rapikan

**Kerjakan:**
1. `scripts/smoke_sources.py`: dijalankan manual (**bukan bagian pytest**) dengan `SOURCES_MODE=live`, untuk satu IP publik.
   Lewat limiter yang sama (ikut terhitung kuota). Cetak: sumber, HTTP status, status hasil, reason, durasi, dan untuk
   AbuseIPDB `X-RateLimit-Remaining`. **Tidak pernah mencetak key atau header request.**
2. README: cara mengaktifkan mode live, arti status/flag/indication, peringatan kuota VT 4/menit, bahwa mode mock = simulasi,
   tabel IP demo mock beserta catatan hasilnya fiktif dan tidak boleh masuk MISP/blocklist (Keputusan 9). (Catatan fiktif/MISP
   sudah mulai ditulis sejak Tahap 1; Tahap 4 memastikan README lengkap dan konsisten.)
3. `docs/tasks/TASK-02-progress.md`: status per tahap, keputusan, hasil test, known gaps. Tandai known gap #4 TASK-01 selesai.
4. `ruff check` + `ruff format --check` bersih.

**Cek selesai** (developer):
```fish
# ubah SOURCES_MODE=live di .env, lalu:
docker compose up -d --force-recreate api
docker compose exec api python -m scripts.smoke_sources --ip 118.25.6.39
```
Simpan output ke folder bukti **di luar repo** (Bab 9 "API nyata": tanggal, paket akun, HTTP status, field, kuota, durasi).
Lalu coba `POST /api/v1/checks` di Swagger dengan IP yang sama → hasil kedua harus dari cache.

## Known gaps (diputuskan saat grilling, 29 Okt 2026; tidak dikerjakan di task ini)

1. **Tanpa single-flight.** Dua cek IP yang sama hampir bersamaan sama-sama meleset cache dan bisa membuang 1 kuota. Limiter
   tetap menjamin batas tidak terlewati.
2. **Tanpa force refresh.** Analis tidak bisa melewati cache sebelum TTL habis (mis. `OK_NO_SIGNAL` 24 jam).
3. **Riwayat mock dan live bisa bercampur**, terutama di demo laptop 4 Nov. Mulai dari DB kosong, **atau** badge
   `SUMBER_SIMULASI` wajib ada di TASK-03 (frontend). Belum ada filter `simulated` di `GET /checks`.
4. **Data cache kedaluwarsa tidak ditampilkan**, termasuk saat sumber gagal; analis hanya melihat check lama di riwayat.
5. **Syarat non-komersial VirusTotal.** Akun gratis dilarang untuk business workflow/produk komersial. Konfirmasi ke dosen
   sebelum soc-ir dipakai sebagai SOC operasional.

## Definition of Done TASK-02

- [ ] API key hanya di `secrets/` (gitignored) dan header request; tidak ada di log, DB, respons, atau riwayat git
- [ ] Pemetaan status Bab 3 lengkap dengan fixture berlabel nyata/simulasi
- [ ] Rumus, label, flag Bab 4 lulus seluruh contoh Bab 4 & 9
- [ ] Cache per sumber dengan TTL; error tidak di-cache; cache lama tidak jadi hasil baru; data simulasi tidak pernah terbaca di mode live
- [ ] Limiter bersama mencegah lewat 4/menit & 500/hari (VT) dan 1.000/hari (AbuseIPDB); hanya panggilan live yang dihitung
- [ ] Smoke test API nyata berhasil dan buktinya tersimpan
- [ ] Mode mock selalu berlabel `SUMBER_SIMULASI` dan check simulasi ditolak 422 saat dikirim ke MISP

---

## Lampiran — fixture respons nyata (29 Okt 2026, IP 118.25.6.39, disanitasi)

AbuseIPDB (`maxAgeInDays=30`, HTTP 200, `X-RateLimit-Limit: 1000`, `X-RateLimit-Remaining: 999`):
```json
{"data":{"ipAddress":"118.25.6.39","isPublic":true,"ipVersion":4,"isWhitelisted":false,"abuseConfidenceScore":7,"countryCode":"CN","usageType":"Data Center/Web Hosting/Transit","isp":"Tencent Cloud Computing (Beijing) Co., Ltd","domain":"tencentcloud.com","hostnames":[],"isTor":false,"totalReports":0,"numDistinctUsers":0,"lastReportedAt":"2026-09-17T22:17:21+00:00"}}
```
Catatan: `totalReports=0` (jendela 30 hari) tetapi `lastReportedAt` 42 hari sebelumnya dan skor 7. Simpan apa adanya;
jangan menyimpulkan ulang cara AbuseIPDB menghitung skor (Bab 1).

VirusTotal (HTTP 200; dipangkas: `whois`, `rdap`, dan `last_analysis_results` dihapus):
```json
{"data":{"id":"118.25.6.39","type":"ip_address","attributes":{"network":"118.24.0.0/15","country":"CN","asn":45090,"as_owner":"Shenzhen Tencent Computer Systems Company Limited","last_analysis_stats":{"malicious":0,"suspicious":0,"undetected":38,"harmless":54,"timeout":0},"last_analysis_date":1793236459,"reputation":0}}}
```

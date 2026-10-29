# TASK-02 — Sumber Reputasi (AbuseIPDB + VirusTotal), Skor, dan Cache

> Taruh file ini di `docs/tasks/TASK-02-sumber-reputasi-skor.md`.
> Prompt ke Claude Code: **"Baca CLAUDE.md dan docs/tasks/TASK-02-sumber-reputasi-skor.md. Kerjakan Tahap 0 saja, jalankan Cek selesai, lalu berhenti dan laporkan."**
> Ulangi untuk Tahap 1, 2, dst. Satu tahap = satu PR kecil (`Closes #<issue>` di PR terakhir).

Branch kerja: `feat/sumber-reputasi` (atau satu branch per tahap, mengikuti kebiasaan TASK-01).
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
   - Jika `mock`: file key boleh kosong/tidak dipakai.
3. `docker-compose.yml`: tambah secret `abuseipdb_api_key` (`./secrets/abuseipdb_api_key.txt`) dan
   `virustotal_api_key` (`./secrets/virustotal_api_key.txt`), hanya untuk service `api` (bukan `db`).
4. `.env.example`: tambah variabel di atas dengan `SOURCES_MODE=mock` dan path `/run/secrets/...`. Tidak ada nilai key.
5. `core/logging.py`: set logger `httpx` dan `httpcore` ke level `WARNING` (log INFO httpx mencetak URL request).
6. README: langkah membuat file secret key (perintah fish, lihat Cek selesai). Pastikan `secrets/` tetap di `.gitignore`.

**Cek selesai** (developer menjalankan sendiri; **jangan pernah menempel API key ke Claude Code**):
```fish
# buat file secret dari Bitwarden tanpa menampilkan key
read -s key; printf '%s' $key > secrets/abuseipdb_api_key.txt; set -e key
read -s key; printf '%s' $key > secrets/virustotal_api_key.txt; set -e key
chmod 600 secrets/*.txt
git status                                   # secrets/ TIDAK muncul
docker compose up -d --build && docker compose ps
docker compose exec api pytest -q            # tetap hijau
```
Uji negatif: set `SOURCES_MODE=live` dengan file key kosong → kontainer gagal start, pesan tanpa nilai.

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
   `evidence_summary` diberi `"simulasi": true`.
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

**Cek selesai:** test Bab 9 lulus:
- `12 malicious → V=96`, `13 → 100`.
- Contoh Bab 4: `90/80 → 85,5`, `90/0 → 49,1 + HASIL_BERBEDA`, `90/timeout → null, DATA_TERBATAS, 1/2`,
  `0/0 → 0,0, COMPLETE`, `NO_RECORD/timeout → null, TIDAK_TERSEDIA, 0/2`, `90/80 + whitelist → 85,5 + WHITELISTED`.
- Batas label tepat di 25, 50, 75, dan kasus 74,96 (tampil `75.0` tapi label `TINGGI`).
- Data respons nyata 29 Okt (`A=7`, `V=0`) → `3,8`, `RENDAH`, `COMPLETE`, `2/2`, tanpa `HASIL_BERBEDA`.

---

## Tahap 3 — Cache + pembatas kuota bersama (Bab 5)

**Kerjakan:**
1. Migrasi `0004`: tabel `source_cache` dan `source_calls`.
   - `source_cache`: `source`, `ip`, `params_key` (AbuseIPDB: `maxAgeInDays=30`; VT: `""`), `status`, `normalized_score`,
     `evidence_summary` (JSONB), `source_time`, `source_time_type`, `retrieved_at`, `expires_at`.
     UNIQUE (`source`, `ip`, `params_key`), upsert.
   - `source_calls` (log setiap request keluar = bukti + dasar hitung kuota): `source`, `called_at`, `http_status`,
     `result_status`, `reason`, `duration_ms`, `retry_after_seconds`. **Tanpa** key, header, atau body.
2. Alur per sumber: cache masih berlaku → pakai (`from_cache=true`, `retrieved_at` asli **tidak diubah**).
   Kedaluwarsa → tidak dipakai menghitung skor baru. `ERROR`/`INSUFFICIENT_DATA` tidak disimpan ke cache.
   Saat satu sumber kedaluwarsa, hanya sumber itu yang diambil ulang.
3. Pembatas kuota **bersama untuk semua user** (bukan per user), berbasis tabel `source_calls`:
   - Dalam satu transaksi dengan `pg_advisory_xact_lock` per sumber: hitung panggilan 60 detik terakhir (VT ≤ 4) dan sejak
     00:00 UTC (VT ≤ 500, AbuseIPDB ≤ 1000), cek cooldown dari `Retry-After` terakhir, lalu **reservasi** dengan menyisipkan
     baris `source_calls` sebelum request dikirim. Request HTTP dijalankan **di luar** lock, lalu barisnya diperbarui.
   - Melebihi batas atau masih cooldown → `SKIPPED` + `QUOTA_INTERNAL`, tanpa request keluar.
   - 429 → tidak ada retry di request yang sama; sumber itu cooldown sesuai `Retry-After` (bila tidak ada, 60 detik).
4. Cek ulang setelah tahap ini: input yang ditolak validasi tetap **tidak** menyentuh cache, limiter, maupun jaringan.

**Cek selesai:** test:
- cek IP yang sama dua kali → panggilan kedua `from_cache=true`, adapter tidak dipanggil, `retrieved_at` sama.
- cache kedaluwarsa (manipulasi waktu) → diambil ulang; `ERROR` tidak pernah keluar dari cache.
- 5 cek IP berbeda dalam 1 menit → cek ke-5 VT `SKIPPED/QUOTA_INTERNAL`, AbuseIPDB tetap jalan, status `DATA_TERBATAS`.
- 10 request paralel tidak menembus batas 4/menit (pola uji paralel TASK-01 Tahap 4).
- setelah 429 + `Retry-After`, sumber itu di-skip sampai cooldown habis.

---

## Tahap 4 — Uji API nyata + rapikan

**Kerjakan:**
1. `scripts/smoke_sources.py`: dijalankan manual (**bukan bagian pytest**) dengan `SOURCES_MODE=live`, untuk satu IP publik.
   Lewat limiter yang sama (ikut terhitung kuota). Cetak: sumber, HTTP status, status hasil, reason, durasi, dan untuk
   AbuseIPDB `X-RateLimit-Remaining`. **Tidak pernah mencetak key atau header request.**
2. README: cara mengaktifkan mode live, arti status/flag/indication, peringatan kuota VT 4/menit, dan bahwa mode mock = simulasi.
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

## Definition of Done TASK-02

- [ ] API key hanya di `secrets/` (gitignored) dan header request; tidak ada di log, DB, respons, atau riwayat git
- [ ] Pemetaan status Bab 3 lengkap dengan fixture berlabel nyata/simulasi
- [ ] Rumus, label, flag Bab 4 lulus seluruh contoh Bab 4 & 9
- [ ] Cache per sumber dengan TTL; error tidak di-cache; cache lama tidak jadi hasil baru
- [ ] Limiter bersama mencegah lewat 4/menit & 500/hari (VT) dan 1.000/hari (AbuseIPDB)
- [ ] Smoke test API nyata berhasil dan buktinya tersimpan
- [ ] Mode mock selalu berlabel `SUMBER_SIMULASI`

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

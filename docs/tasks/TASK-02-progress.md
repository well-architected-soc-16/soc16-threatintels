# TASK-02 — Progress

Diperbarui: 2026-10-31. Rujukan: [`TASK-02-sumber-reputasi-skor.md`](TASK-02-sumber-reputasi-skor.md), issue #20.

## Status per tahap

| Tahap | Isi | PR | Status |
|---|---|---|---|
| Rencana | Rencana TASK-02 dan keputusan grilling (Keputusan 7-14) | #19, #21 | Selesai, ter-merge |
| 0 | Konfigurasi sumber + API key sebagai secret | #22 | Selesai, ter-merge |
| 1 | Adapter AbuseIPDB + VirusTotal, pemetaan status | #23 | Selesai, ter-merge |
| 2 | Skor, label, flag, kontrak respons | (belum dibuka) | Selesai di lokal, menunggu "push" dari developer |
| 3 | Cache + pembatas kuota bersama | - | Belum |
| 4 | Uji API nyata + rapikan | - | Belum |

Hasil terakhir (Tahap 2): `pytest` **645 passed**, `ruff check` dan `ruff format --check` bersih, `docker compose ps` `db` dan `api` `healthy`.

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

Fixture di `tests/fixtures/sources/` (19 file): 2 respons nyata 29 Okt 2026 (IP `118.25.6.39`, apa adanya dari lampiran rencana) dan sisanya simulasi (IP dokumentasi `203.0.113.7`); nama file memuat `nyata` atau `simulasi`.

Kelengkapan kasus simulasi Bab 9 (dijaga `test_sources_fixtures.py::test_fixture_simulasi_mencakup_kasus_bab_9`): skor 0, nol laporan, objek tidak ditemukan, statistik kosong, all-undetected, all-timeout, field hilang, 401, 403, 429, dan JSON rusak semuanya punya fixture. **Timeout bukan file**: ia exception httpx (`ReadTimeout`/`ConnectTimeout`) di test kedua adapter. Dua fixture yang awalnya belum ada ditambahkan setelah pengecekan: AbuseIPDB 403 (sebelumnya test memakai ulang body 401) dan AbuseIPDB skor 0 dengan laporan (sebelumnya "skor 0" dan "nol laporan" digabung dalam satu file). Isi body 403 AbuseIPDB adalah simulasi buatan sendiri, bukan salinan respons nyata.

### Keputusan dan penyimpangan dari rencana

1. **`SourceResult` punya dua field di luar daftar rencana**: `flags` (tuple) dan `retry_after_seconds`. Rencana mewajibkan flag `NO_VENDOR_OPINION` dan `SUMBER_SIMULASI` serta "simpan `Retry-After`", tetapi daftar field-nya tidak punya tempat untuk itu.
2. **Bab 3 dokumen riset tidak ada di repo.** Pemetaan awalnya diturunkan dari butir 3-5 rencana Tahap 1. Developer lalu mencocokkannya dengan Bab 3 (31 Okt): field wajib AbuseIPDB, `stats` hilang = `INVALID_RESPONSE`, `{}` = `INSUFFICIENT_DATA`, 401 = `AUTH` walau body rusak, dan 404 `NotFoundError` = `NO_RECORD` dinyatakan sesuai; satu koreksi pada `reason` SKIPPED (keputusan 5).
3. **Hanya `abuseConfidenceScore` yang wajib** pada AbuseIPDB (integer 0-100; `bool`, float, string, null ditolak). `totalReports`, `numDistinctUsers`, `lastReportedAt`, `isWhitelisted` yang hilang atau salah tipe menjadi null di bukti dan tidak menggagalkan skor. Rencana hanya menyebut "field wajib" tanpa daftar.
4. **VirusTotal: `last_analysis_stats` hilang atau bukan objek = `INVALID_RESPONSE`; objek kosong `{}` = `INSUFFICIENT_DATA`.** Rencana hanya mendefinisikan yang kedua. Nilai statistik yang ada harus integer >= 0 (bukan `bool`); kunci yang tidak ada dihitung 0. Hanya lima kunci (`malicious`, `suspicious`, `harmless`, `undetected`, `timeout`) yang disalin ke bukti; kunci lain diabaikan.
5. **`reason` wajib untuk `ERROR` dan `SKIPPED`, null untuk status lain** (`NO_RECORD`, `INSUFFICIENT_DATA`, `OK_*`). Awalnya saya menulis "null untuk semua status non-ERROR"; developer mengoreksinya setelah mencocokkan dengan Bab 3 ("SKIPPED; nilai null; sertakan alasan"). Aturan ditegakkan di `SourceResult.__post_init__` (ValueError bila dilanggar), bukan hanya konvensi. Kode alasan SKIPPED ditambahkan ke `SourceReason`: `ADAPTER_NOT_IMPLEMENTED` (sama dengan string di `ip_checks.collect_sources`, dipakai sampai Tahap 2) dan `QUOTA_INTERNAL` (dipakai pembatas kuota, Tahap 3). Tidak ada kode karangan untuk status lain.
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
- `pytest -q -p no:cacheprovider`: **533 passed** (Tahap 0: 271; 262 test baru), 1 warning (known gap 4).
- `ruff check --no-cache .`: bersih. `ruff format --no-cache --check .`: 67 file sudah terformat.
- Uji mutasi manual (salinan kode di luar repo, tidak di-commit): 10 perubahan sengaja ke kode (redirect diikuti, `bool` dianggap integer, `min(100, ...)` dihapus, timeout per request dihapus, guard IP dihapus, 401 jadi `UPSTREAM`, error membawa skor 0, key di query string, mock tanpa flag simulasi, nol laporan jadi `NO_RECORD`) masing-masing menggagalkan minimal 2 test.
- `git status --porcelain`: tidak ada `.env` atau `secrets/`. Pencarian pola rahasia pada diff hanya menemukan nama variabel dan key uji palsu `kunci-uji-palsu-xyz`. Fixture bersih dari `whois`, `rdap`, email, dan telepon (juga dijaga `tests/test_sources_fixtures.py`).

### Test baru

- `test_sources_abuseipdb.py`, `test_sources_virustotal.py`: satu test (atau satu kasus parametrize) per baris pemetaan butir 3-5 rencana; bentuk request (header, parameter, timeout, tanpa key di URL); key tidak muncul di URL, `caplog` level DEBUG, `repr(result)`, `asdict(result)`, `repr(adapter)` pada jalur sukses dan error; IP tidak valid tidak memicu request.
- `test_sources_mock.py`: satu kasus per baris tabel IP demo, IP di luar tabel, flag simulasi pada semua hasil, tanpa jaringan (`socket.connect` dan `getaddrinfo` diblokir).
- `test_sources_base.py`: aturan `reason` (wajib untuk `ERROR` dan `SKIPPED`, ditolak untuk status lain), diuji untuk semua status. Dua mutasi pada pengecekan itu menggagalkan 2 dan 8 test.
- `test_sources_fixtures.py`: nama berlabel nyata/simulasi, JSON valid, bebas data kontak, dan kelengkapan kasus Bab 9.
- `tests/sources_support.py`: alat bantu (`MockTransport`, pemuat fixture, invarian "hanya `OK_*` yang boleh membawa skor").

## Tahap 2

Dikerjakan di branch `feat/task-02-tahap-2-skor-kontrak`. Adapter kini tersambung ke `POST /checks`; guard `SOURCES_MODE=live` tetap ada (dicabut di Tahap 3).

Kode:
- `services/scoring.py` (baru): `combined_score`, `indication`, `derive_flags`; bobot, ambang, dan urutan flag sebagai konstanta.
- `services/sources/factory.py` (baru): `get_sources()` memilih sumber dari `SOURCES_MODE`; mode `live` melempar `RuntimeError` (fail closed).
- `services/ip_checks.py`: `collect_sources(ip, sources)` memanggil sumber berurutan; `assess()` mengembalikan `Assessment` (status, cakupan, skor, flag); `to_stored()` menyiapkan JSON untuk JSONB.
- `schemas/check.py`: `SourceResult` diperluas (semua field baru opsional); `CheckOut` mendapat `indication`.
- `routers/checks.py`: sumber disuntikkan lewat `Depends(get_sources)`; audit `ip_check` mencatat status per sumber.
- `routers/iocs.py`: guard `SUMBER_SIMULASI` → 422.
- Tanpa migrasi Alembic: `sources` dan `flags` sudah JSONB.

### Keputusan dan penyimpangan dari rencana

1. **`indication` adalah `computed_field` dari nilai tersimpan; `risk_score` dibulatkan hanya di serializer respons.** Pembulatan di validator akan mengubah 74,96 menjadi 75.0 lalu `SANGAT_TINGGI`. Test 74,96 melewati API dengan baris tersimpan.
2. **Hasil sumber disimpan dengan waktu UTC (ISO, `+00:00`); WIB hanya di respons.** `evidence_summary.lastReportedAt` tetap apa adanya dari AbuseIPDB (UTC); `source_time` adalah field yang dinormalkan dan ditampilkan WIB.
3. **Flag tingkat cek dikumpulkan dari semua hasil, bukan hanya yang bisa dinilai.** Tanpa itu, cek simulasi yang `TIDAK_TERSEDIA` (mis. `8.8.4.4`) lolos dari guard MISP. Urutan flag tetap (`HASIL_BERBEDA`, `NO_VENDOR_OPINION`, `WHITELISTED`, `SUMBER_SIMULASI`) dan tanpa duplikat, jadi `GET` sama persis dengan `POST`. Flag tak dikenal dari sumber tidak diteruskan.
4. **Sumber dicari berdasarkan nama, bukan posisi.** `WHITELISTED` hanya dibaca dari hasil AbuseIPDB.
5. **Tidak ada `except Exception` di `collect_sources`.** Adapter sudah mengubah semua kegagalan httpx menjadi `ERROR`. `ValueError` dari `require_public_ip` berarti input yang ditolak lolos ke adapter, dan itu harus gagal keras, bukan dicatat sebagai `UPSTREAM`.
6. **`get_sources` mode `live` melempar `RuntimeError`**, berlapis di atas guard `Settings`. Adapter live tidak dibangun sebelum pembatas kuota ada.
7. **Guard MISP diletakkan tepat setelah guard `INPUT_DITOLAK`**, sebelum `_find_existing` dan insert apa pun. Izin MISP tetap diperiksa lebih dulu, jadi analyst tanpa izin tetap mendapat 403, bukan 422. Seperti guard `INPUT_DITOLAK`, penolakan ini tidak menulis audit.
8. **`assess()` memakai `Assessment`, bukan tuple**, dan `assessment_status` ditulis eksplisit (`assessed == 0` → `TIDAK_TERSEDIA`, `assessed == total` → `COMPLETE`, selain itu `DATA_TERBATAS`). Perilakunya sama dengan sebelumnya; daftar sumber kosong tetap `TIDAK_TERSEDIA`, `0/0`.
9. **`SOURCE_NAMES` pindah dari `ip_checks` ke `sources/factory.py`**; urutan hasil selalu AbuseIPDB lalu VirusTotal.
10. **`make_check` di conftest menerima `risk_score`, `coverage`, `flags`, `sources`.** Test lama `test_checks` yang mengharapkan `SKIPPED/ADAPTER_NOT_IMPLEMENTED` diganti: ekspektasi "null, bukan 0" dipertahankan dengan IP `8.8.4.4`. Spy `collect_sources` di tiga test diubah ke tanda tangan baru; tidak ada test yang dihapus.

11. **`scoring_version` tetap `v1-percobaan`** (dikonfirmasi developer). Bobot 30/25, ambang 25/50/75, dan selisih 50 tidak diubah. Dijaga `assert body["scoring_version"] == "v1-percobaan"` di `test_checks.py` dan `test_checks_scoring_api.py` (semua IP demo), dan konstanta `scoring.SCORING_VERSION`.
12. **`isWhitelisted: null` tidak menghasilkan flag `WHITELISTED`** (dikonfirmasi developer); hanya `true` yang menghasilkannya, hanya dari AbuseIPDB, dan tidak memangkas skor. Dijaga `test_whitelisted_hanya_jika_is_whitelisted_true` (kasus `null`, `false`, dan hilang) serta `test_is_whitelisted_null_dari_respons_abuseipdb_tidak_menghasilkan_flag` yang memakai fixture respons dengan `"isWhitelisted": null` lewat adapter asli.

### Cek selesai (rencana Tahap 2)

- `12 malicious → V=96`, `13 → 100`: sudah diuji di `test_sources_virustotal.py` (Tahap 1).
- Contoh Bab 4 lewat adapter mock dan lewat API (`test_scoring.py`, `test_checks_scoring_api.py`): `90/80 → 85,5`, `90/0 → 49,1 + HASIL_BERBEDA`, `90/timeout → null, DATA_TERBATAS, 1/2`, `0/0 → 0,0 COMPLETE`, `NO_RECORD/timeout → null, TIDAK_TERSEDIA, 0/2`, `90/80 + whitelist → 85,5 + WHITELISTED`. Semuanya tambahan `SUMBER_SIMULASI`.
- Batas label tepat di 25, 50, 75 (lewat rumus `A=V=n`) dan 74,96 (tampil `75.0`, label `TINGGI`, lewat API).
- Data nyata 29 Okt (`A=7`, `V=0`) lewat adapter asli di atas `MockTransport`: `3,8`, `RENDAH`, `COMPLETE`, `2/2`, `flags: []`, `source_time` AbuseIPDB `2026-09-18T05:17:21+07:00`.
- Cek `SUMBER_SIMULASI` ke `POST /iocs/misp`: 422, tanpa baris submission, klien MISP tidak dipanggil, tanpa audit `ioc_submit*`. Kontrol positif: cek tanpa flag itu, dan cek data nyata lewat API, tetap 201.

### Hasil gerbang

- `docker compose up -d --build`: `db` dan `api` `healthy`; `/health` OK.
- `pytest -q -p no:cacheprovider`: **645 passed** (Tahap 1: 533; 112 test baru), 1 warning (known gap 4).
- `ruff check --no-cache .`: bersih. `ruff format --no-cache --check .`: 72 file sudah terformat.
- Uji mutasi manual (salinan di luar repo, tidak di-commit), masing-masing menggagalkan minimal 1 test dari lima file terkait: guard MISP dihapus (10 test), label dari nilai yang sudah dibulatkan (3), `SUMBER_SIMULASI` hanya dari sumber yang bisa dinilai (5), bobot 30→31 (10), ambang `≥50` jadi `>50` (2), status non-OK menambah cakupan (13), skor disimpan sudah dibulatkan (1), skor gabungan digeser +1 (11), audit memuat evidence (1), ambang label `<25` jadi `≤25` (3).
- `git status --porcelain`: tidak ada `.env` atau `secrets/`.

### Test baru

- `test_scoring.py`: rumus, pembulatan, bukti skor kelipatan 1/11 (seluruh pasangan A,V; tanpa seri pembulatan), batas label, semua flag (termasuk simulasi tanpa sumber yang bisa dinilai, urutan, dedup), `assess()` untuk tiap status, tabel IP demo, data nyata, `isWhitelisted: null` dari respons asli, dan JSON-serialisasi hasil tersimpan.
- `test_checks_scoring_api.py`: kontrak respons per IP demo, GET sama dengan POST, presisi penuh di DB, label dari nilai tersimpan lewat API, cek lama tiga-field, data nyata dengan waktu WIB, kegagalan sumber (401, 429 dengan `Retry-After`, timeout), audit tanpa evidence/key, key tidak bocor, input ditolak dan viewer tidak memanggil sumber, OpenAPI.
- `test_iocs_simulasi.py`: guard MISP end-to-end dan kontrol positif.

## Catatan untuk Tahap 3

Ditambahkan di akhir Tahap 2 (dari known gap 9), bagian dari rencana Tahap 3:

1. **Cache dan pembatas kuota hanya boleh dipanggil setelah `validate_ip` lolos, di dalam alur `collect_sources`; bukan di dependency FastAPI** (`get_sources` atau dependency baru). Dependency berjalan sebelum body diperiksa, jadi input yang ditolak (dan viewer yang akan mendapat 403) bisa mengakses cache atau menghabiskan kuota. Ini melanggar aturan CLAUDE.md: input yang ditolak tidak boleh memicu request keluar, akses cache, atau kuota. `get_sources` cukup membangun objek tanpa efek samping (tanpa request, tanpa baca/tulis cache, tanpa kuota).
2. **Test yang wajib ditulis di Tahap 3** (cache dan limiter belum ada, jadi belum bisa ditulis sekarang): untuk setiap input yang ditolak (`PRIVATE`, `LOOPBACK`, `INVALID_FORMAT`, `IPV6_NOT_SUPPORTED`, dst.) dan untuk viewer (403), pakai spy pada cache dan limiter lalu pastikan **nol** pembacaan cache, **nol** penulisan cache, dan **nol** hitungan kuota; ditambah satu test bahwa membangun `get_sources()` tidak menyentuh keduanya. Lakukan uji mutasi: memindahkan akses cache/limiter ke dependency harus membuat test ini gagal. Pola yang sudah ada dan bisa ditiru: `test_input_ditolak_tidak_memanggil_sumber_yang_disuntikkan` dan `test_viewer_tidak_memanggil_sumber`.
3. Tinjau known gap 11 (`except` di `collect_sources`) sebelum guard `SOURCES_MODE=live` dicabut.

## Known gaps

1. **Pengaturan awal bertambah dua file.** `docker compose up` gagal bila `secrets/abuseipdb_api_key.txt` atau `secrets/virustotal_api_key.txt` tidak ada (Keputusan 14). Developer yang sudah punya stack harus menjalankan `touch` sekali setelah pull. README sudah menjelaskan; CI nanti harus membuat kedua file itu juga.
2. ~~Teks "Cek selesai" Tahap 0 di file rencana memuat `chmod 600 secrets/*.txt`~~ **Selesai**: dikoreksi menjadi `chmod 644` dengan alasan singkat (lihat keputusan 1).
3. **Uji start `live` dengan file key valid lewat kontainer** baru bisa dilakukan setelah guard dicabut (Tahap 3); sebelum itu hanya dibuktikan lewat test subprocess.
4. **Peringatan deprecation Starlette `TestClient`** (`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead`, dari `fastapi/testclient.py:1`) muncul di ringkasan pytest. **Sudah ada sebelum Tahap 0**: dicek 2026-10-30 dengan menjalankan test `main` (commit `1badd61`) di worktree sementara memakai image yang sama (fastapi 0.162.0, starlette 1.10.0, httpx 0.28.1; `requirements.txt` fastapi dan httpx identik dengan Tahap 0, httpx hanya pindah file): 209 passed, 1 warning, teks sama. Jadi bukan akibat Tahap 0. Belum diperbaiki.
   **Keputusan (developer, 2026-10-31):** Tahap 1 tetap memakai `httpx`. Migrasi ke `httpx2` dikerjakan sebagai issue terpisah setelah demo, karena nama logger dan trust store SSL berubah. Nama logger berubah berarti pengaman logging (`httpx`/`httpcore` dipaku di `WARNING`, lihat Tahap 0) tidak lagi mengenai logger client baru; trust store SSL berubah berarti perilaku verifikasi TLS ke sumber dan nanti ke MISP perlu diuji ulang. Sampai migrasi, warning ini dibiarkan.
5. ~~Pemetaan Tahap 1 belum dicocokkan dengan Bab 3 dokumen riset~~ **Selesai**: dicocokkan dengan Bab 3 oleh developer, 31 Okt; satu koreksi (`reason` SKIPPED, lihat keputusan 5). PDF riset tidak ditambahkan ke repo.
6. ~~Test `assess()` untuk status non-`OK_*` belum ada~~ **Selesai di Tahap 2**: `test_scoring.py` menguji bahwa `NO_RECORD`, `INSUFFICIENT_DATA`, `ERROR`, dan `SKIPPED` tidak menambah cakupan (Keputusan 6 rencana).
7. ~~Belum ada pemakai `SourceResult` di luar test~~ **Selesai di Tahap 2**: `ip_checks.to_stored` (JSON, waktu UTC) dan skema respons `SourceResult` (waktu WIB).
8. **Mode mock membuat semua cek baru ber-flag `SUMBER_SIMULASI` sehingga tidak ada cek yang bisa dikirim ke MISP lewat alur normal** sampai sumber live aktif (Tahap 3). Itu disengaja (Keputusan 10), tetapi demo MISP 4 Nov harus memakai cek bertanda data nyata atau menunggu Tahap 3. Test memakai adapter live di atas `MockTransport` untuk membuktikan cek tanpa flag tetap bisa dikirim.
9. **`get_sources` dijalankan sebagai dependency sebelum body `POST /checks` diperiksa.** Pada mode mock itu hanya membuat objek, tanpa jaringan. Aturan untuk Tahap 3 ada di bagian "Catatan untuk Tahap 3": cache dan pembatas kuota tidak boleh disentuh di dependency.
10. ~~Pembulatan memakai `round()` Python dan titik tengah bisa dibulatkan ke arah yang tidak terduga~~ **Ditutup dengan bukti (Tahap 2)**: `(30A + 25V) / 55 = (6A + 5V) / 11`, jadi skor selalu kelipatan 1/11 dan seri di titik tengah 1 desimal (`x.x5`) mustahil (`20(6A + 5V) = 22k + 11`: genap vs ganjil). `test_skor_kelipatan_sepelas_jadi_tidak_ada_seri_pembulatan_dan_label_stabil` memeriksa seluruh 101×101 pasangan A,V dan juga bahwa label dari nilai asli sama dengan label dari nilai yang dibulatkan. Akibatnya kasus 74,96 (tampil `75.0`, label `TINGGI`) adalah **pengaman desain** (label dari nilai tersimpan) yang tidak terjadi dari input nyata dengan rumus ini. Bukti ini gugur bila bobot atau jumlah sumber berubah (mutasi bobot 30→31 menggagalkan test), jadi test itu harus ikut ditinjau saat tim mengubah rumus.
11. **Tanpa `except` di `collect_sources`, bug di satu adapter membuat seluruh `POST /checks` menjadi 500**, padahal Bab 5 menyatakan hasil sumber lain tetap ditampilkan. Ini kompromi sadar di Tahap 2 (keputusan 5): adapter sudah mengubah semua kegagalan httpx menjadi `ERROR`, dan `ValueError` dari `require_public_ip` berarti input yang ditolak lolos ke adapter sehingga harus gagal keras. Tetapi exception lain (bug parsing, `KeyError`, dll.) ikut membatalkan cek, dan tidak ada baris cek maupun audit yang tersimpan. **Tinjau ulang sebelum mode live**: opsi yang perlu diputuskan adalah menangkap exception per sumber (kecuali kelas yang menandai input tidak valid), mencatat hanya nama kelasnya di log, menyimpan sumber itu sebagai `ERROR` + `UPSTREAM`, dan membiarkan sumber lain tetap tampil.

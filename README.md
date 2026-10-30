# SOC 316 Threat Intelligence Tools

**Threat Intelligence & IP Reputation Aggregator** untuk proyek **Well Architected SOC 16**, Project Based Learning (PBL) Semester 3, Program Studi D4 Rekayasa Keamanan Siber, Politeknik Negeri Batam.

Aplikasi ini dirancang untuk membantu analis SOC memeriksa reputasi alamat IP, menggabungkan informasi dari sumber threat intelligence eksternal, dan menyediakan konteks tambahan saat menganalisis alert atau insiden.

> **Status:** fondasi backend (TASK-01) sudah dapat dijalankan secara lokal: REST API dengan login, hak akses per peran, validasi IP, riwayat pemeriksaan, dan pengiriman IoC ke MISP dalam **mode mock**. **Belum ada**: sumber reputasi eksternal (AbuseIPDB dan VirusTotal), perhitungan skor, frontend, MISP asli, CI/CD, dan deployment ke `soc-ir`. Pemeriksaan IP saat ini hanya memvalidasi input dan menyimpan hasil `TIDAK_TERSEDIA` tanpa skor; belum ada data reputasi nyata. Rincian kemajuan dan keterbatasan ada di [`docs/tasks/TASK-01-progress.md`](docs/tasks/TASK-01-progress.md).

## Tujuan

- Menyediakan antarmuka web untuk pemeriksaan reputasi alamat IP.
- Menggabungkan hasil dari sumber eksternal agar informasi lebih mudah dibandingkan.
- Menyediakan REST API beserta dokumentasi Swagger untuk pengujian dan integrasi.
- Mendukung pengiriman indikator ke MISP dan pengayaan use case deteksi SOC.
- Mendokumentasikan pengembangan, pengujian, dan deployment sebagai luaran PBL.

**Threat intelligence** adalah informasi ancaman yang dianalisis untuk membantu pengambilan keputusan keamanan. **Indicator of Compromise (IoC)** adalah indikator yang dapat berkaitan dengan aktivitas berbahaya, misalnya alamat IP yang dilaporkan terlibat dalam serangan.

## Ruang Lingkup

Repository ini berisi pengembangan tools threat intelligence, termasuk backend, frontend, pengujian, dokumentasi, dan konfigurasi deployment yang akan ditambahkan secara bertahap.

Website e-commerce dikembangkan pada repository terpisah: [soc16-ecommerce](https://github.com/well-architected-soc-16/soc16-ecommerce).

Tools ini mendukung proses analisis SOC. SIEM, pengelolaan kasus insiden, dan respons otomatis tetap menjadi bagian dari integrasi sistem SOC secara keseluruhan.

## Target Fitur

| Fitur | Hasil yang dituju | Status |
|---|---|---|
| Pemeriksaan reputasi IP | Pengguna memasukkan alamat IP dan memperoleh informasi reputasinya | Sebagian: validasi input dan penyimpanan hasil sudah ada; data reputasi belum |
| Agregasi sumber eksternal | Hasil dari sumber yang dipilih disajikan dalam format yang konsisten | Direncanakan (adapter belum dibuat) |
| Penyajian hasil | Hasil menampilkan sumber, waktu pemeriksaan, dan konteks reputasi yang tersedia | Sebagian: sumber, status, dan waktu tampil; skor belum dihitung |
| REST API | Pemeriksaan dapat diakses melalui endpoint yang terdokumentasi | Tersedia (lihat [Daftar Endpoint](#daftar-endpoint)) |
| Dokumentasi Swagger | Endpoint, parameter, respons, dan kesalahan dapat diperiksa dan diuji | Tersedia di `/docs`, termasuk respons gagal |
| Frontend web | Pengguna dapat melakukan pemeriksaan melalui browser | Direncanakan |
| Integrasi MISP | Indikator hasil analisis dapat dikirim ke MISP | Sebagian: mode mock saja; MISP asli belum |

Sumber v1 adalah AbuseIPDB dan VirusTotal; adapter dan perhitungan skor belum diimplementasikan. Perbedaan penilaian antar-sumber perlu tetap terlihat agar hasil dapat ditelusuri.

## Hubungan dengan SOC

Alur yang dituju:

1. Analis mengambil alamat IP dari alert atau log yang sedang diperiksa.
2. Analis memasukkan alamat IP melalui frontend atau REST API.
3. Backend mengueri sumber reputasi eksternal yang telah dipilih.
4. Aplikasi menyajikan hasil sebagai konteks tambahan untuk triase.
5. Indikator yang relevan dikirim ke MISP sesuai mekanisme yang disepakati tim.

Rencana penempatan tools adalah pada host `soc-ir` di zona SOC. Akses ke sumber eksternal perlu dikoordinasikan dengan pengelola jaringan sesuai kebijakan firewall proyek.

Panduan RKS301 KM-5 mensyaratkan minimal satu sumber TI eksternal benar-benar digunakan untuk memperkaya sedikitnya satu use case. Keberhasilan integrasi perlu dibuktikan melalui hasil pengujian dan alert yang diperkaya; pemasangan tools saja belum memenuhi target tersebut.

## Teknologi dan Deployment

| Komponen | Arah pengembangan | Status |
|---|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2 | Berjalan (lokal) |
| Autentikasi | OAuth2 password flow + JWT (PyJWT), hash password argon2 (pwdlib) | Berjalan (lokal) |
| Dokumentasi API | Swagger/OpenAPI di `/docs` | Tersedia |
| Frontend | Vite + React + TypeScript | Belum dimulai |
| Sumber reputasi | AbuseIPDB dan VirusTotal lewat adapter | Belum diimplementasikan |
| Integrasi indikator | MISP | Mode mock; MISP asli belum |
| Penyimpanan data | PostgreSQL 18 (psycopg 3) di kontainer | Berjalan (lokal) |
| CI/CD | GitHub Actions dengan pemeriksaan keamanan dan build | Belum dibuat |
| Deployment | Kontainer dengan pola tarik pada host tujuan (`soc-ir`), mengikuti arah RPP | Belum diimplementasikan; saat ini hanya Docker Compose untuk pengembangan |

Versi dependensi dikunci di `backend/requirements.txt` dan `backend/requirements-dev.txt`.

## Memulai

Ambil salinan repository (repository ini public):

```bash
gh repo clone well-architected-soc-16/soc16-threatintels
cd soc16-threatintels
git status
```

Jika repository sudah di-clone, gunakan folder lokal yang sudah ada.

### Menjalankan secara lokal

Prasyarat: Git, Docker dan Docker Compose, serta `openssl`. Perintah di bawah ditulis untuk shell **fish**. Semuanya dijalankan dari root repository.

> **Repository ini public.** Jangan pernah meng-commit `.env`, isi `secrets/`, password, token JWT, atau API key. `.env` dan `secrets/` sudah ada di `.gitignore`; tetap periksa `git status` sebelum commit.

**1. Siapkan konfigurasi.** Salin contoh, lalu isi nilai rahasianya dengan nilai acak:

```fish
cp .env.example .env

sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY="(openssl rand -hex 32)"|" .env

for v in SEED_ADMIN_PASSWORD SEED_ANALYST_MISP_PASSWORD SEED_ANALYST_PASSWORD SEED_VIEWER_PASSWORD
    sed -i "s|^$v=.*|$v="(openssl rand -hex 16)"|" .env
end
```

Nilai contoh di `.env.example` (`ganti-...`) **harus diganti**, karena nilainya diketahui semua orang (repository ini public). Aplikasi menolak start jika `JWT_SECRET_KEY` berawalan `ganti-` (tanpa membedakan huruf besar/kecil) atau kurang dari 32 byte, dan seed menolak password yang berawalan `ganti-`; pesan error hanya menyebut nama variabelnya, bukan nilainya. Akibatnya, menyalin `.env.example` tanpa mengisinya membuat kontainer `api` berhenti saat start. Password akun awal dapat dilihat di `.env` (baris `SEED_*_PASSWORD`); simpan di tempat yang aman atau ganti dengan password pilihan sendiri (minimal 12 karakter). Variabel lain dijelaskan di [Konfigurasi](#konfigurasi).

**2. Buat file secret.** Password Postgres dan API key sumber reputasi dibaca dari file (Docker secret), bukan dari variabel lingkungan:

```fish
mkdir -p secrets
openssl rand -hex 24 > secrets/db_password.txt
touch secrets/abuseipdb_api_key.txt secrets/virustotal_api_key.txt
chmod 700 secrets
chmod 644 secrets/*.txt
```

File perlu dapat dibaca oleh proses di dalam kontainer (itu sebabnya `644`; kontainer `api` berjalan sebagai pengguna non-root), sedangkan foldernya tetap tertutup untuk pengguna lain.

Kedua file API key **harus ada** agar `docker compose up` berjalan, tetapi pada `SOURCES_MODE=mock` (default) isinya tidak dipakai, jadi file kosong dari `touch` sudah cukup. Mode `live` belum didukung (aplikasi menolak start). Nanti, saat mode live tersedia, isi key tanpa menampilkannya di layar atau riwayat shell, jangan menempelkannya ke chat atau issue:

```fish
read -s key; printf '%s' $key > secrets/abuseipdb_api_key.txt; set -e key
read -s key; printf '%s' $key > secrets/virustotal_api_key.txt; set -e key
```

Satu file berisi satu key saja (tanpa spasi atau baris tambahan).

**3. Jalankan.**

```fish
docker compose up -d --build
docker compose ps
```

`db` dan `api` harus berstatus `healthy`. Migrasi database (`alembic upgrade head`) berjalan otomatis saat kontainer `api` mulai; jika migrasi gagal, kontainer berhenti. API hanya di-bind ke `127.0.0.1:8000`, dan Postgres tidak dibuka ke host.

**4. Buat akun awal (seed).** Perintah ini membuat 4 akun dari variabel `SEED_*` di `.env`:

```fish
docker compose exec api python -m scripts.seed_users
```

Contoh keluaran: `admin: dibuat`, `analyst_misp: dibuat`, `analyst: dibuat`, `viewer: dibuat`. Aman dijalankan ulang: akun yang sudah ada dilewati (`sudah ada`) dan password-nya tidak diubah. Jika ada variabel yang kosong, password kurang dari 12 karakter, atau username kembar, seluruh seed dibatalkan dan tidak ada akun yang dibuat.

| Akun (default) | Peran | Izin kirim ke MISP |
|---|---|---|
| `admin` | admin | Ya (admin) |
| `analyst_misp` | analyst | Ya (`can_send_misp`) |
| `analyst` | analyst | Tidak |
| `viewer` | viewer | Tidak |

**5. Periksa.**

```fish
curl -s http://127.0.0.1:8000/api/v1/health
```

Hasil yang diharapkan: `{"status":"ok","db":"ok","misp_mode":"mock","time":"...+07:00"}`. Swagger tersedia di <http://127.0.0.1:8000/docs>.

Perintah sehari-hari:

```fish
docker compose logs -f api      # log aplikasi (JSON)
docker compose down             # hentikan; data database tetap ada
docker compose down -v          # hentikan dan HAPUS data database (seed ulang setelahnya)
```

### Mencoba API

Di Swagger (`/docs`): klik **Authorize**, isi `username` dan `password` salah satu akun (kolom `client_id` dan `client_secret` dikosongkan), lalu coba endpoint. Contoh bukti uji akses negatif: login sebagai `viewer`, lalu `GET /api/v1/admin/users` harus menghasilkan **403**.

Lewat terminal (fish, membutuhkan `jq`). Ganti `PASSWORD_ANDA`; perhatikan bahwa password yang diketik di terminal tersimpan di riwayat shell:

```fish
set TOKEN (curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
    --data-urlencode "username=analyst" \
    --data-urlencode "password=PASSWORD_ANDA" | jq -r .access_token)

curl -s http://127.0.0.1:8000/api/v1/auth/me -H "Authorization: Bearer $TOKEN"

curl -s -X POST http://127.0.0.1:8000/api/v1/checks \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"ip":"8.8.8.8"}'
```

Hasil cek untuk IP publik saat ini berupa `assessment_status: "TIDAK_TERSEDIA"`, `coverage: "0/2"`, `risk_score: null`, dan kedua sumber berstatus `SKIPPED` dengan alasan `ADAPTER_NOT_IMPLEMENTED`. Itu perilaku yang disengaja sampai adapter dibuat: data yang tidak ada tidak pernah diubah menjadi skor 0.

IP yang ditolak (privat, loopback, link-local, multicast, dokumentasi, reserved, IPv6, atau format salah) dijawab **422** dengan `assessment_status: "INPUT_DITOLAK"` dan `reason_code`; input yang ditolak tidak memicu permintaan keluar apa pun.

### Daftar Endpoint

Semua endpoint berawalan `/api/v1`. Selain `/health` dan `/auth/login`, semuanya membutuhkan header `Authorization: Bearer <token>`.

| Method | Path | Akses | Keterangan | Respons gagal |
|---|---|---|---|---|
| GET | `/health` | publik | Status API, database, dan `misp_mode` | 503 (database tidak terjangkau) |
| POST | `/auth/login` | publik | Login (form `username` dan `password`), mengembalikan JWT | 401, 422 |
| GET | `/auth/me` | semua peran | Profil akun yang sedang login | 401 |
| GET | `/admin/users` | admin | Daftar user | 401, 403 |
| POST | `/admin/users` | admin | Buat user | 401, 403, 409 (username sudah ada), 422 |
| PATCH | `/admin/users/{id}` | admin | Ubah `role`, `can_send_misp`, `is_active` | 401, 403, 404, 409 (admin tidak boleh menurunkan atau menonaktifkan dirinya sendiri), 422 |
| POST | `/checks` | admin, analyst | Cek satu IPv4 publik | 401, 403, 422 (`INPUT_DITOLAK`) |
| GET | `/checks` | semua peran | Riwayat cek (`limit` 1-100, `offset`; terbaru dulu) | 401, 422 |
| GET | `/checks/{id}` | semua peran | Detail satu cek | 401, 404 |
| POST | `/iocs/misp` | admin, atau analyst dengan `can_send_misp` | Kirim IoC ke MISP; `reason` wajib (minimal 10 karakter) | 401, 403, 404, 409 (sudah pernah dikirim; berisi `submission_id`), 422, 501 (`MISP_MODE=live` belum diimplementasikan), 502 (pengiriman gagal) |
| GET | `/iocs` | semua peran | Daftar pengiriman IoC (paginasi seperti `/checks`) | 401, 422 |

Pengiriman IoC bersifat manual dan tidak menggandakan data: satu cek hanya punya satu pengiriman, jadi klik ulang menghasilkan 409. Pengiriman yang `failed` dapat dikirim ulang (respons 200, baris yang sama). Kegagalan tidak pernah ditampilkan sebagai sukses.

### Hak Akses

Hak akses ditegakkan di backend, bukan di tampilan.

| Aksi | admin | analyst | viewer |
|---|---|---|---|
| Lihat riwayat cek IP dan daftar IoC | Ya | Ya | Ya |
| Membuat cek IP (`POST /checks`) | Ya | Ya | 403 |
| Kirim IoC ke MISP (`POST /iocs/misp`) | Ya | Hanya jika `can_send_misp` | 403 |
| Kelola user dan izin (`/admin/users`) | Ya | 403 | 403 |

Role dan status akun dibaca ulang dari database di setiap request, jadi perubahan hak akses atau penonaktifan berlaku langsung walaupun token lama belum kedaluwarsa. Login, penolakan akses (403), perubahan user, pengecekan IP, dan pengiriman IoC dicatat di tabel `audit_logs` tanpa menyimpan password maupun token.

### Konfigurasi

Dibaca dari `.env` (lihat `.env.example`). Password database dan API key sumber reputasi tidak ada di sini: dibaca dari `secrets/db_password.txt`, `secrets/abuseipdb_api_key.txt`, dan `secrets/virustotal_api_key.txt`.

| Variabel | Default | Keterangan |
|---|---|---|
| `APP_ENV` | `dev` | Nama lingkungan |
| `LOG_LEVEL` | `INFO` | Level log (format JSON ke stdout) |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` | `db`, `5432`, `soc16ti`, `soc16ti` | Koneksi Postgres di jaringan Compose |
| `DB_PASSWORD_FILE` | `/run/secrets/db_password` | Lokasi file password di dalam kontainer; jangan diubah untuk Compose |
| `JWT_SECRET_KEY` | (wajib diisi) | Kunci penanda tangan JWT; acak, minimal 32 **byte**, tidak boleh berawalan `ganti-`. Aplikasi menolak start jika tidak terpenuhi |
| `JWT_EXPIRE_MINUTES` | `30` | Masa berlaku token |
| `MISP_MODE` | `mock` | `mock` tidak menghubungi apa pun; `live` belum diimplementasikan dan menjawab 501 |
| `SOURCES_MODE` | `mock` | Satu saklar untuk AbuseIPDB dan VirusTotal. `mock` memakai data simulasi (berflag `SUMBER_SIMULASI`) tanpa request keluar. `live` **belum didukung**: aplikasi menolak start (sementara, sampai Tahap 3 TASK-02) |
| `ABUSEIPDB_API_KEY_FILE`, `VIRUSTOTAL_API_KEY_FILE` | `/run/secrets/abuseipdb_api_key`, `/run/secrets/virustotal_api_key` | Lokasi file key di dalam kontainer; jangan diubah untuk Compose. Pada `live` file wajib ada, tidak kosong, dan bukan nilai contoh (`ganti-...`); pesan galat hanya menyebut nama variabel |
| `SOURCE_TIMEOUT_SECONDS` | `10` | Batas waktu request per sumber |
| `ABUSEIPDB_MAX_AGE_DAYS` | `30` | `maxAgeInDays` untuk AbuseIPDB (1-365) |
| `ABUSEIPDB_DAILY_LIMIT`, `VT_DAILY_LIMIT`, `VT_PER_MINUTE_LIMIT` | `1000`, `500`, `4` | Kuota akun tim, dipakai bersama semua user (satu API key per sumber) |
| `CACHE_TTL_OK_SIGNAL_HOURS`, `CACHE_TTL_OK_NO_SIGNAL_HOURS`, `CACHE_TTL_NO_RECORD_HOURS` | `6`, `24`, `1` | TTL cache per status sumber; nilai percobaan, belum disepakati tim |
| `SEED_*_USER`, `SEED_*_PASSWORD` | lihat `.env.example` | Akun awal untuk `scripts.seed_users`; password minimal 12 karakter dan tidak boleh berawalan `ganti-` |

### Menjalankan test dan lint

Test memakai database terpisah (`<DB_NAME>_test` dan `<DB_NAME>_migration_test`, dibuat otomatis) dan tidak menyentuh database dev. Test tidak memanggil layanan eksternal.

```fish
docker compose exec api python -m pytest -q -p no:cacheprovider
docker compose exec api ruff check --no-cache .
docker compose exec api ruff format --no-cache --check .
```

Setelah mengubah kode, jalankan `docker compose up -d --build` agar image `api` terbarui sebelum menjalankan test.

`tests/test_env_example.py` memastikan nilai contoh di `.env.example` selalu ditolak aplikasi dan seed. File itu di-mount read-only ke kontainer `api` oleh `docker-compose.yml` (khusus dev). Karena mount satu file menyimpan inode-nya, setelah `.env.example` diubah atau di-pull jalankan `docker compose up -d --force-recreate api` agar kontainer melihat isi terbaru; tanpa itu test bisa lulus terhadap isi lama. Jika file tidak ditemukan, test gagal (tidak di-skip).

### Struktur backend

```
backend/
  app/
    main.py            aplikasi FastAPI dan pendaftaran router
    core/              config, security (JWT, hash), deps (autentikasi, RBAC), logging, timeutil
    db/                base dan session SQLAlchemy
    models/            users, audit_logs, ip_checks, ioc_submissions
    schemas/           skema Pydantic
    routers/           health, auth, admin, checks, iocs
    services/          audit, ip_validation, ip_checks, misp/ (Protocol, mock, kerangka live)
  alembic/             migrasi database
  scripts/             entrypoint.sh, seed_users.py
  tests/
docs/tasks/            rencana dan catatan kemajuan per task
```

## Alur Kontribusi

Gunakan branch untuk setiap perubahan setelah fondasi awal repository selesai:

1. Buat issue yang menjelaskan tugas dan hasil yang diharapkan.
2. Perbarui branch `main`, lalu buat branch pekerjaan.
3. Buat perubahan dan periksa hasilnya.
4. Commit dan push branch tersebut.
5. Ajukan pull request dengan ringkasan perubahan dan bukti pemeriksaan.
6. Minta review anggota lain sebelum digabungkan ke `main`, sesuai kesepakatan tim.

Contoh memulai perubahan dokumentasi dari working tree yang bersih:

```bash
git switch main
git pull --ff-only origin main
git switch -c docs/update-project-overview
```

Contoh penamaan branch: `feat/ip-lookup`, `fix/input-validation`, dan `docs/api-guide`. Reviewer ditentukan sesuai ketersediaan serta akses anggota.

## Pengelolaan Konfigurasi dan Bukti

- Tambahkan `.gitignore` sebelum memasukkan kode, konfigurasi lokal, atau dependensi.
- Simpan API key, token, dan password di luar kode; jangan sertakan dalam commit, issue, atau log.
- Jika konfigurasi lingkungan diperlukan, sediakan `.env.example` berisi nama variabel dan nilai contoh tanpa rahasia asli.
- Catat sumber data, versi komponen, serta hasil pengujian agar dapat ditelusuri.
- Samarkan data sensitif sebelum menyertakan contoh log atau bukti pengujian.
- Laporkan kegagalan dan keterbatasan integrasi sesuai hasil yang sebenarnya.

## Tahapan Pengembangan

- [ ] Melengkapi README dan `.gitignore`.
- [ ] Menetapkan fitur minimum dan kriteria keberhasilannya.
- [ ] Memilih sumber reputasi serta memeriksa kuota dan ketentuan penggunaannya.
- [ ] Menetapkan tech stack dan rancangan API.
- [ ] Mengimplementasikan pemeriksaan IP dan dokumentasi Swagger.
- [ ] Mengembangkan frontend.
- [ ] Menguji integrasi MISP dan pengayaan satu use case SOC.
- [ ] Menyiapkan pipeline CI/CD dan deployment.
- [ ] Melengkapi bukti pengujian dan dokumentasi penggunaan.

Checklist diperbarui setelah hasil pekerjaan diperiksa.

## Pengelola

Repository berada di bawah [Organization well-architected-soc-16](https://github.com/well-architected-soc-16).

| Anggota | Tanggung jawab terkait repository |
|---|---|
| Fharel Aditya Pratama | Pengembangan tools TI serta pengelolaan DevOps/GitHub |
| Bagus/Kafka | Pengelola Organization cadangan dan koordinasi integrasi dengan e-commerce |
| Anggota Tim 16 lainnya | Koordinasi kebutuhan jaringan, log, deteksi, dan pengujian sesuai pembagian tugas |

## Acuan Proyek

- **RPP_PBL_RKS316_Revisi.docx** — ruang lingkup tools TI, luaran REST API/Swagger/frontend, integrasi MISP, dan arah pipeline DevSecOps.
- **Panduan Proyek SOC - RKS301 (MAIN PBL)** — kriteria minimum SOC, khususnya KM-5 tentang penggunaan TI untuk pengayaan use case dan bukti pengujiannya.

Dokumen acuan dikelola oleh tim. Rincian implementasi pada README perlu diperbarui mengikuti keputusan tim dan arahan dosen.

## Lisensi

Lisensi repository belum ditetapkan. Pemilihan lisensi akan dibahas bersama tim sebelum publikasi atau distribusi kode.

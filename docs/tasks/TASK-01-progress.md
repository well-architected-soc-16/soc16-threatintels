# TASK-01 — Progress

Diperbarui: 2026-10-29. Rujukan: [`TASK-01-fondasi-backend.md`](TASK-01-fondasi-backend.md), issue #10.

## Status per tahap

| Tahap | Isi | PR | Status |
|---|---|---|---|
| 0 | Kerangka proyek, Docker Compose (API + Postgres) | #11 | Selesai, ter-merge |
| 1 | Database, migrasi Alembic, seed user | #12 | Selesai, ter-merge |
| 2 | Login JWT, RBAC, manajemen user admin, audit log | #13 | Selesai, ter-merge |
| 3 | Validasi IP dan endpoint `/checks` (tanpa sumber eksternal) | #14 | Selesai, ter-merge |
| 4 | Kesiapan MISP (mode mock), `/iocs/misp` anti-duplikat | #15 | Selesai, ter-merge |
| 5 | Rapikan: `ruff` bersih, README (menjalankan lokal, daftar endpoint, seed user) | #16 | Selesai; PR ini menutup issue #10 |

Hasil terakhir: `pytest` **155 passed**, `ruff check` dan `ruff format --check` bersih.

## Tahap 5

- `ruff check` dan `ruff format --check` bersih pada seluruh `backend/`.
- README diperbarui: status dan tabel teknologi disesuaikan dengan kondisi sebenarnya, ditambah panduan menjalankan secara lokal (fish), seed user, contoh pemakaian API, daftar endpoint beserta respons gagalnya, tabel hak akses, tabel konfigurasi, cara menjalankan test dan lint, dan struktur backend. Kata "privat" untuk repository dikoreksi (repository ini public). `.env.example` diperjelas bahwa nilai contoh wajib diganti.
- **Panduan diuji dari awal**: repo di-clone ke folder baru tanpa `.env` dan `secrets/`, lalu blok perintah fish diekstrak langsung dari README dan dijalankan (project Compose terpisah). Hasilnya: konfigurasi dan secret terisi, `docker compose up -d --build` menyalakan `db` dan `api` dengan migrasi 0001-0003 otomatis, seed `dibuat` lalu `sudah ada` saat diulang, `/health` OK, login lewat `jq` + `/auth/me` + `POST /checks` sesuai deskripsi, viewer mendapat 403, IP privat mendapat 422, dan `pytest` **155 passed** dengan `ruff` bersih.
- Checklist "Tahapan Pengembangan" di README sengaja tidak diubah; itu checklist proyek tim dan diperbarui setelah hasil pekerjaan diperiksa tim.

## Keputusan Tahap 4

1. **Retry submission `failed` dipertahankan.** Submission `failed` boleh dikirim ulang memakai baris yang sama (respons 200, tidak ada baris baru); status lain tetap 409.
   - Transisi `failed` -> `pending` adalah satu `UPDATE ... WHERE status = 'failed'`. Di antara request yang bersamaan hanya satu yang mendapat `rowcount = 1`; sisanya menerima 409.
   - Setiap retry yang lolos tercatat di audit log (`ioc_submit_retry`, dalam transaksi yang sama dengan klaim); hasilnya tercatat sebagai `ioc_submit` dengan `detail.retry = true`. Retry yang kalah klaim tercatat sebagai `ioc_submit_duplicate`, bukan retry.
   - Diuji: 10 request retry paralel menghasilkan tepat 1x200 dan 9x409, klien MISP dipanggil sekali, 1 baris, 1 audit `ioc_submit_retry`. Uji mutasi (menghapus `WHERE status = 'failed'`) membuat test ini gagal.
2. **Pending yang nyangkut dan idempotensi event MISP: dicatat sebagai known gaps, sengaja belum diimplementasi** (lihat bagian di bawah).
3. **`MISP_MODE=live` yang belum diimplementasi sekarang menjawab 501**, bukan 502. Submission tetap tersimpan `failed` agar tidak pernah tampak sukses. 502 dipakai untuk kegagalan klien MISP yang sebenarnya.
4. **Roundtrip migrasi berjalan di database test, bukan DB dev.**
   - `tests/test_migrations.py` menjalankan `upgrade head`, `alembic check` (tanpa drift), `downgrade -1` satu revisi demi satu revisi sampai kosong, lalu `upgrade head` lagi.
   - Fixture `migration_engine` memakai database terpisah **`<DB_NAME>_migration_test`** (bukan `<DB_NAME>_test`, supaya roundtrip yang menjatuhkan tabel tidak merusak skema yang dipakai test lain). Skemanya dikosongkan sebelum tiap test.
   - Pengaman `_assert_test_db`: nama database wajib berakhiran `_test` dan tidak boleh sama dengan DB dev; dipakai juga oleh fixture `db`.
   - `alembic/env.py` menerima koneksi yang disuntikkan lewat `config.attributes["connection"]`, sehingga test tidak pernah memakai engine dev.
   - Setelah perubahan ini, tidak ada lagi alasan menjalankan `alembic downgrade` pada DB dev untuk memverifikasi migrasi.
5. **Check berstatus `INPUT_DITOLAK` tidak bisa dikirim ke MISP**, dan ada test-nya:
   - `test_check_input_ditolak_tidak_boleh_dikirim_422`: respons 422, tidak ada baris `ioc_submissions` (bahkan bukan `pending`), klien MISP tidak dipanggil, tidak ada audit `ioc_submit`. Uji mutasi (guard dihapus) membuat test ini gagal.
   - `test_input_ditolak_dari_api_tidak_pernah_menjadi_check_yang_bisa_dikirim`: lewat jalur nyata, `POST /checks` yang ditolak tidak menyimpan check apa pun, sehingga tidak ada `check_id` yang bisa dikirim (404).

## Definition of Done TASK-01

- [x] `docker compose up -d --build` menyalakan db + api tanpa error (diverifikasi di tiap tahap; migrasi berjalan otomatis lewat entrypoint)
- [x] Login 4 user berhasil, RBAC + uji 403 punya test (Tahap 2; juga dicoba manual dengan 4 user seed)
- [x] Validasi IP sesuai aturan, input ditolak tanpa request keluar (Tahap 3; terbukti dengan spy adapter + blokir socket + uji mutasi)
- [x] `ioc_submissions` + endpoint MISP mock siap, anti-duplikat (Tahap 4, PR #15)
- [x] Tidak ada rahasia di riwayat git (dipindai 2026-10-29: 19 commit di semua ref; nilai `SEED_*`, `JWT_SECRET_KEY`, dan `db_password` tidak ditemukan; `.env` dan `secrets/` tidak pernah ter-track)

Seluruh Definition of Done terpenuhi. Yang **tidak** termasuk TASK-01 dan masih terbuka: frontend, adapter AbuseIPDB/VirusTotal, scoring, CI/CD, dan deploy ke `soc-ir` (lihat juga Known gaps).

## Known gaps

Belum diimplementasi dan **tidak dikerjakan di TASK-01**. Perlu diputuskan sebelum `MISP_MODE=live` diisi; dengan mock keduanya praktis tidak terjadi.

1. **Submission `pending` yang nyangkut.** Submission di-commit sebagai `pending` sebelum klien MISP dipanggil. Jika proses mati di antara dua titik itu, baris tertinggal `pending` selamanya. Check tersebut lalu selalu dijawab 409 dan tidak bisa di-retry (retry hanya untuk `failed`). Belum ada batas waktu, pembersih, maupun aksi admin untuk membereskannya; pemulihan saat ini manual di database. Arah solusi: batas waktu `pending` yang kedaluwarsa menjadi `failed` (sehingga bisa di-retry), atau aksi admin.
2. **Idempotensi event MISP.** UUID event belum dibuat saat submission `pending` dan belum dipakai ulang saat retry. Dengan klien live, retry setelah timeout (MISP sebenarnya sudah membuat event, tetapi balasannya tidak sampai) dapat membuat event ganda di MISP. Arah solusi: buat UUID saat klaim, simpan di baris submission, kirim bersama permintaan, dan pakai ulang saat retry. Perilaku MISP terhadap UUID yang ditentukan klien perlu dicek ke dokumentasi MISP/PyMISP sebelum diimplementasi.

Temuan lain selama pengerjaan (juga belum ditangani):

3. **Retry menimpa `reason`, `tags`, dan `submitted_by`** pada baris yang sama. Nilai lama hilang, dan audit log sengaja tidak menyimpan teks alasan, jadi alasan percobaan pertama tidak terlacak.
4. **`coverage` untuk `NO_RECORD` dan `INSUFFICIENT_DATA` belum ditetapkan.** `assess()` hanya menghitung `OK_SIGNAL` dan `OK_NO_SIGNAL` sebagai "bisa dinilai". Perlu keputusan saat adapter AbuseIPDB/VirusTotal dibuat.
5. **Audit login gagal menyimpan username yang dicoba** (di `detail`, dipotong 64 karakter). Jika seseorang salah mengetik password di kolom username, nilai itu ikut tersimpan.
6. **Belum ada pembatasan percobaan login** (rate limit atau lockout).
7. **Alamat IP klien di audit diambil dari koneksi langsung.** Di belakang reverse proxy nilainya akan berupa IP proxy; perlu penanganan `X-Forwarded-For` yang tepercaya saat deploy.
8. ~~**Nilai contoh di `.env.example` lolos validasi.**~~ **Diselesaikan di issue #17** (lihat bagian di bawah). Sisa yang masih terbuka: test pembanding dengan isi `.env.example` belum ada karena file itu tidak terjangkau dari container.
9. **`MISP_MODE=live`** masih kerangka (`LiveMispClient` melempar `NotImplementedError`); verifikasi TLS dengan file CA dan penyimpanan API key MISP belum dirancang.

## Issue #17: tolak secret placeholder

Menutup known gap nomor 8. Branch `fix/tolak-secret-placeholder`.

- **Aturan** (`app/core/secret_policy.py`, dipakai bersama oleh konfigurasi dan seed): nilai dianggap placeholder jika berawalan `ganti-` (tanpa membedakan huruf besar/kecil, spasi di tepi diabaikan). Deteksi memakai pola ini; `.env.example` **tidak** dibaca saat runtime.
- **Aplikasi**: `Settings` menolak `JWT_SECRET_KEY` yang placeholder atau kurang dari 32 **byte** (dihitung dari UTF-8, bukan jumlah karakter). Karena `Settings` dimuat saat `import app.main` dan oleh `alembic/env.py`, kontainer berhenti di langkah migrasi pertama entrypoint sebelum uvicorn start.
- **Seed**: `scripts.seed_users` membatalkan seluruh seed jika ada `SEED_*_PASSWORD` yang placeholder; pesan hanya menyebut nama variabel.
- **Nilai tidak bocor**: `hide_input_in_errors=True` pada `Settings`, ditambah pesan validator yang hanya menyebut nama variabel dan alasan. Diuji pada teks error (`str`, `repr`, traceback) dan pada keluaran proses nyata (stdout + stderr) untuk `import app.main` dan `alembic current`.
- **Diuji**: `tests/test_secret_policy.py` dan tambahan di `tests/test_seed_users.py`. Dibuktikan juga manual: kontainer dengan `--env-file .env.example` apa adanya keluar dengan kode 1 dan pesan jelas tanpa nilai; dengan secret acak (stack dev) start normal.

**Belum ada: test pembanding dengan isi `.env.example`.** Tujuannya mencegah `.env.example` diedit menjadi nilai yang lolos validasi. Test itu tidak dapat berjalan di container sekarang karena `.env.example` berada di luar build context `./backend` dan tidak di-mount, jadi tidak ditambahkan agar tidak di-skip. Menunggu keputusan sebelum compose diubah. Opsi:

  - **A. Bind mount read-only di service `api` (hanya dev):** `./.env.example:/app/.env.example:ro` di `docker-compose.yml`. Satu baris, image `runtime` tidak berubah, file tetap satu sumber. Test dibuat **gagal keras** (bukan skip) jika file tidak ada. Konsekuensi: test hanya jalan lewat Compose; di CI harus memakai mount yang sama atau menjalankan test dari root repo.
  - **B. Salin ke build context** (mis. `backend/tests/fixtures/`): bekerja tanpa mount, tetapi menduplikasi file sehingga bisa melenceng dari `.env.example` yang asli, padahal itulah yang hendak dijaga.
  - **C. Ubah build context ke root repo:** `.env.example` ikut ter-COPY, tetapi mengubah Dockerfile dan `.dockerignore`, dan berisiko menyalin file lain ke image.
  - **D. Jalankan test itu di host/CI di luar container:** tidak perlu mengubah compose, tetapi butuh Python dan dependensi di host.
  - Rekomendasi: **A**.

## Catatan untuk CI/CD

- **CI harus membuat secret acak saat job berjalan**, misalnya `openssl rand -hex 32` untuk `JWT_SECRET_KEY` dan `openssl rand -hex 16` untuk tiap `SEED_*_PASSWORD`. Jangan menjalankan test atau aplikasi dengan `.env.example` apa adanya: setelah issue #17 itu **gagal start dengan sengaja**. Jangan juga meng-commit nilai tetap ke workflow (repository ini public); gunakan nilai yang dibuat per-run atau GitHub Actions secrets.
- Test sudah membuat database sendiri (`<DB_NAME>_test`, `<DB_NAME>_migration_test`) dan hanya membutuhkan `JWT_SECRET_KEY` valid, variabel `DB_*`, dan `DB_PASSWORD_FILE` yang menunjuk file berisi password Postgres.

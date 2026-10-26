# Panduan Kontribusi – Well Architected SOC 16

Aturan main biar semua perubahan kepantau di board **SOC316 - PBL** (GitHub Projects di level Organization).

## Alur Kerja

1. **Bikin issue dulu**
   - Mau nambah fitur, update, atau benerin bug? Bikin issue di repo yang sesuai.
   - Pakai template yang tersedia (Fitur / Bug).
   - Pastikan issue masuk ke board **SOC316 - PBL** dan set **Assignee**.

2. **Geser kartu ke `In Progress`** waktu mulai ngerjain.

3. **Kerja di branch sendiri**, jangan langsung di `main`.
   - Format nama branch:
     - `feat/<nama-fitur>` → fitur baru, contoh: `feat/login-page`
     - `fix/<nama-bug>` → perbaikan bug, contoh: `fix/upload-error`
     - `docs/<topik>` → dokumentasi
     - `chore/<topik>` → konfigurasi, dependensi, dll.

4. **Commit yang jelas**
   - Contoh: `feat: tambah halaman login`, `fix: perbaiki validasi upload`.
   - Satu commit = satu perubahan logis.

5. **Buka Pull Request (PR)**
   - Tulis `Closes #<nomor-issue>` di deskripsi PR biar issue otomatis tertutup saat PR di-merge.
   - Geser kartu ke **`Review`**.
   - Kabarin di grup: "PR #<nomor> siap direview".

6. **Review**
   - Minimal **1 anggota lain** ngecek PR sebelum merge.
   - Yang ngereview cek: kode jalan, nggak ada secret/password/token ikut ke-commit, sesuai issue.

7. **Merge** → kartu otomatis pindah ke **`Done`** (via workflow board).

## Aturan Wajib

- ❌ Jangan push langsung ke `main`.
- ❌ Jangan commit kredensial, password, token, atau file `.env`. Cek `.gitignore` sebelum commit.
- ✅ Setiap perubahan harus punya issue di board.
- ✅ Kalau ada perubahan yang terlanjur masuk tanpa issue, bikin issue susulan yang menjelaskan perubahannya.

## Arti Kolom Board

| Kolom | Artinya |
|---|---|
| **Todo** | Sudah direncanakan, belum dikerjakan |
| **In Progress** | Sedang dikerjakan |
| **Review** | PR sudah dibuka, menunggu dicek |
| **Done** | Sudah di-merge / selesai |

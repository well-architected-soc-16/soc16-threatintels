---
name: kerjakan-tahap
description: Kerjakan SATU tahap dari file task di docs/tasks/ (mis. TASK-02 tahap 1), jalankan Cek selesai dan gerbang kualitas, perbarui file progress, lalu berhenti dan laporkan. Dipanggil manual oleh developer.
argument-hint: "[TASK-xx] [nomor-tahap]"
disable-model-invocation: true
---

# Kerjakan satu tahap task

Argumen: task `$0`, tahap `$1`. Jika salah satu kosong, tanya dulu, jangan menebak.

## 1. Siapkan

1. Baca `CLAUDE.md`, lalu file `docs/tasks/$0-*.md` (bagian umum + **hanya** Tahap $1) dan
   `docs/tasks/$0-progress.md` jika ada. Jika file task tidak ditemukan, berhenti dan laporkan.
2. Pastikan tahap sebelumnya sudah ter-merge ke `main` menurut progress. Jika belum, berhenti dan tanya.
3. `git status` harus bersih. Buat branch dari `main` terbaru:
   `git switch main && git pull && git switch -c <jenis>/<task>-tahap-<n>-<ringkas>`.
4. Jika tahap butuh keputusan yang tidak tertulis di file task, **tanya sebelum menulis kode**.

## 2. Kerjakan

- Hanya isi Tahap $1. Temuan di luar lingkup → catat sebagai known gap.
- Kalau ragu versi library/API, cek dokumentasi resmi dan tulis link-nya di laporan.
- Jangan pernah meminta atau membaca nilai rahasia (`.env`, `secrets/`). Jika butuh API key nyata, berhenti dan
  beri developer perintah fish untuk menyiapkannya sendiri.

## 3. Gerbang kualitas (semua wajib, jalankan setelah build ulang)

```fish
docker compose up -d --build
docker compose ps
docker compose exec api python -m pytest -q -p no:cacheprovider
docker compose exec api ruff check --no-cache .
docker compose exec api ruff format --no-cache --check .
```

Lalu jalankan perintah "Cek selesai" milik Tahap $1. Perintah yang butuh aksi developer (mis. membuat file secret,
smoke test API nyata) **jangan dijalankan sendiri**; tulis di laporan sebagai langkah untuk developer.

Pemeriksaan rahasia sebelum commit:
- `git status --porcelain` tidak boleh memuat `.env` (selain `.env.example`) atau apa pun di `secrets/`.
- `git diff --cached` tidak boleh memuat nilai yang mirip key/password/token. Cari minimal:
  `git diff --cached | grep -n -i -E "api[_-]?key|x-apikey|password|secret|token|bearer"` dan periksa setiap hasilnya
  (nama variabel dan placeholder `ganti-...` boleh; nilai asli tidak).
- Fixture respons sumber tidak boleh memuat `whois`, `rdap`, email, atau telepon.

Jika ada yang gagal: perbaiki bila masih dalam lingkup tahap, lalu ulangi gerbang. Jika tidak bisa, berhenti dan
laporkan apa adanya. **Jangan** menonaktifkan, men-skip, atau melemahkan test agar lulus.

## 4. Catat dan commit (lokal saja)

1. Perbarui `docs/tasks/$0-progress.md`: baris status tahap, keputusan yang diambil beserta alasannya,
   hasil gerbang (jumlah test lulus, ruff), dan known gaps baru. Buat file itu jika belum ada, mengikuti
   format `TASK-01-progress.md`.
2. Commit kecil gaya Conventional Commits yang menyebut tahap, mis. `feat: adapter AbuseIPDB dan VirusTotal ($0 tahap $1)`.
3. **Jangan push dan jangan membuka PR.** Tunggu developer bilang "push".

## 5. Laporan ke developer (bahasa Indonesia sederhana)

1. **Hasil:** selesai / sebagian / gagal, dalam satu kalimat.
2. **Yang dikerjakan:** daftar singkat file/fitur.
3. **Bukti:** output gerbang (jumlah test, ruff), hasil Cek selesai.
4. **Keputusan & penyimpangan** dari file task, beserta alasan.
5. **Known gaps** baru.
6. **Langkah untuk developer:** perintah fish yang harus dijalankan sendiri, lalu "push" untuk membuka PR
   (judul PR + `Closes #<issue>` bila ini tahap terakhir).

# TASK-03 — Progress

Diperbarui: 2026-11-02. Rujukan: [`TASK-03-frontend-workbench.md`](TASK-03-frontend-workbench.md), issue #28.

## Status per tahap

| Tahap | Isi | PR | Status |
|---|---|---|---|
| Rencana | Rencana TASK-03, keputusan grilling (Keputusan 13-28), `PRODUCT.md` | #30 | Selesai, ter-merge |
| 0 | Scaffold `frontend/`, Tailwind, proxy, gerbang kualitas | (belum dibuka) | Selesai di branch lokal; uji LAN proxy dan `:8000` lolos, uji `/@fs` via LAN belum; menunggu "push" |
| 1 | Rencana desain, API client, login, shell layout | | Belum |
| 2 | Cek IP, bukti, riwayat | | Belum |
| 3 | Kirim ke MISP, tampilan Kiriman MISP | | Belum |
| 4 | Bukti demo, uji akses negatif, polish, README | | Belum |

Hasil terakhir (Tahap 0): backend `pytest` **763 passed**, `ruff check` dan `ruff format --check` bersih, `docker compose ps` `db` dan `api` `healthy`. Frontend `npm run lint`, `npm run build`, `npm test` (**3 passed**) hijau; `npm audit --omit=dev` dan `npm audit` keduanya **0 vulnerabilities**.

## Tahap 0

Dikerjakan di branch `feat/task-03-tahap-0-scaffold-frontend`. Tidak ada perubahan backend.

- `npm create vite@latest frontend -- --template react-ts` (create-vite 9.3.3, non-interaktif, tanpa auto-install). Aset demo template dihapus (`App.css`, `hero.png`, `react.svg`, `vite.svg`, `favicon.svg`, `icons.svg`, README bawaan); `index.css` hanya berisi `@import "tailwindcss";`; `App.tsx` hanya stub `<h1>SOC16 TI</h1>`; `index.html` berbahasa `id` dengan judul "SOC16 TI".
- Versi terpasang (dikunci `package-lock.json`, dicek ke registry npm hari ini): Vite 8.3.5, React/ReactDOM 19.3.1, TypeScript 7.0.2, Tailwind CSS dan `@tailwindcss/vite` 4.3.3, Vitest 5.0.5, Oxlint (bawaan template). Dependency runtime hanya `react`, `react-dom`, `tailwindcss`, `@tailwindcss/vite` (Keputusan 2).
- `vite.config.ts`: plugin `react()` + `tailwindcss()`, `server.proxy` `'/api'` → `http://127.0.0.1:8000` dengan `changeOrigin: true`, tanpa rewrite. `server.host` dan `server.allowedHosts` tidak diisi.
- Skrip: `dev:lan` (`vite --host`) dan `test` (`vitest run`) ditambahkan; `dev`, `build`, `lint` bawaan template.
- `.gitignore` root: `frontend/dist/` ditambahkan. Tidak ada file `.env*` di `frontend/`.
- `CLAUDE.md`: status frontend, perintah gerbang frontend, lokasi modul, dan dua aturan keamanan (Keputusan 28). README: bagian "Frontend (dev)" dan "Uji bersama tim (LAN)", baris frontend di tabel teknologi.

### Keputusan dan penyimpangan dari rencana

1. **Test contoh = guard konfigurasi Vite** (`frontend/vite.config.test.ts`, 3 test), bukan test kosong. Isinya memastikan proxy `/api` tidak berubah, `server.host` tidak terisi (LAN hanya lewat `dev:lan`), dan `allowedHosts` bukan `true`. `tsconfig.node.json` ikut memasukkan file ini; importnya memakai `./vite.config.ts` karena `module: nodenext` mewajibkan ekstensi (build awal sempat gagal karena itu, sudah diperbaiki).
2. **Lint memakai Oxlint** (default `create-vite` 9), bukan ESLint. Rencana hanya menulis "bila template menyediakan"; tidak ada dependency tambahan. Konfigurasi bawaan template dibiarkan (`.oxlintrc.json`).
3. **Favicon dihapus tanpa pengganti.** Favicon bawaan adalah aset demo template; identitas visual ditentukan di rencana desain Tahap 1.
4. **Environment test = `node`** (bawaan Vitest), tanpa jsdom/testing-library, sesuai Keputusan 6.
5. **Syarat Node lebih sempit dari rencana.** Rencana menulis "Node 22.12+"; Vitest 5 hanya mendukung `^22.12`, `^24`, dan `>=26` (Node 23 dan 25 tidak). README sudah ditulis demikian. Laptop developer memakai Node v26.12.1 (lolos).
6. **`npm audit` penuh dijalankan sebelum `dev:lan`** (Keputusan 25): 0 temuan, jadi tidak ada advisory `vite` yang memblokir.

### Hasil "Cek selesai" Tahap 0

Dijalankan agen (localhost, dev server `npm run dev` tanpa `--host`, lalu dihentikan):

- `http://localhost:5173/api/v1/health` → HTTP 200 dengan JSON health dari backend (`status: ok`, `db: ok`, `misp_mode: mock`): proxy jalan tanpa CORS.
- `http://localhost:5173/docs` → HTTP 200 tetapi isinya **fallback SPA Vite**, bukan Swagger (0 penanda "swagger"; Swagger asli hanya di `127.0.0.1:8000/docs`). Jangan dibaca sebagai "Swagger terbuka".
- Uji `/@fs` (Keputusan 26), hanya kode HTTP yang dicetak: kontrol positif `/@fs/<repo>/frontend/package.json` → **200**; semua 3 file di `secrets/` × 3 varian (polos, `?raw??`, `?import&raw??`) → **403**; `.env` × 3 varian → **403**. Prosedur hash Keputusan 27 tidak diperlukan karena tidak ada yang bukan 403.
- `git status` tidak memuat `node_modules/`, `dist/`, atau `.env`.

Uji LAN, dijalankan developer dari HP di jaringan yang sama dengan `npm run dev:lan` (hasil dilaporkan developer, bukan diamati agen):

- `http://<IP-laptop>:5173/` → halaman stub "SOC16 TI" tampil (sisanya putih, sesuai: `App.tsx` baru stub).
- `http://<IP-laptop>:5173/api/v1/health` → **JSON health muncul**, isi sama dengan uji localhost: proxy jalan lewat LAN.
- `http://<IP-laptop>:8000/docs` → **tidak dapat dijangkau**: API tidak terbuka ke LAN (di-bind ke `127.0.0.1`).

**Belum dibuktikan:** uji `/@fs` (Keputusan 26) lewat `http://<IP-laptop>:5173/...` dari perangkat lain. Hasil localhost di atas belum membuktikan perilaku lewat IP LAN. Dicatat sebagai known gap 1 sampai diuji.

## Known gaps baru (Tahap 0)

1. **Uji `/@fs` lewat IP LAN belum dilakukan.** Hanya yang lewat localhost yang terbukti (semua 403). Perlu diulang dari perangkat lain sebelum sesi uji tim pertama; sampai itu selesai, jangan anggap Keputusan 26 terpenuhi sepenuhnya.
2. **Paragraf "Status" di README (baris 7) sudah usang** dan sudah usang sebelum tahap ini: masih menyebut sumber reputasi dan frontend belum ada. Tidak diubah karena di luar lingkup Tahap 0; perlu dirapikan di Tahap 4 atau PR docs sendiri.
3. **Rentang `^` di `package.json`.** Reproduksibilitas dijamin `package-lock.json` dan `npm ci`; `npm install` tanpa lockfile bisa menarik versi minor yang lebih baru.
4. **Warning deprecation Starlette/httpx** di pytest (`starlette.testclient` menyarankan `httpx2`) sudah ada sebelum tahap ini; tidak disentuh.

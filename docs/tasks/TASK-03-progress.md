# TASK-03 — Progress

Diperbarui: 2026-11-02. Rujukan: [`TASK-03-frontend-workbench.md`](TASK-03-frontend-workbench.md), issue #28.

## Status per tahap

| Tahap | Isi | PR | Status |
|---|---|---|---|
| Rencana | Rencana TASK-03, keputusan grilling (Keputusan 13-28), `PRODUCT.md` | #30 | Selesai, ter-merge |
| 0 | Scaffold `frontend/`, Tailwind, proxy, gerbang kualitas | #31 | Selesai, ter-merge; uji LAN proxy, `:8000`, dan `/@fs` (12 dari 12 varian 403) lolos |
| 1 | Rencana desain, API client, login, shell layout | | Rencana desain disetujui (2 Nov); login, API client, dan shell selesai di branch lokal; **menunggu uji manual developer** (login 3 role, paksa 401) dan "push" |
| 2 | Cek IP, bukti, riwayat | | Belum |
| 3 | Kirim ke MISP, tampilan Kiriman MISP | | Belum |
| 4 | Bukti demo, uji akses negatif, polish, README | | Belum |

Hasil terakhir (Tahap 1): backend `pytest` **763 passed**, `ruff check` dan `ruff format --check` bersih, `db` dan `api` `healthy`. Frontend `npm run lint` (tanpa warning), `npm run build`, `npm test` (**78 passed**, 8 file), `npm audit --omit=dev` dan `npm audit` keduanya **0 vulnerabilities**; grep `localStorage|sessionStorage|document.cookie|console.|dangerouslySetInnerHTML|VITE_` di `frontend/src` kosong.

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

Uji `/@fs` lewat IP LAN (Keputusan 26), dijalankan developer dari browser HP (Cara 2, bukan curl; hasil dilaporkan developer, bukan diamati agen):

- Kontrol positif `/@fs/<repo>/frontend/package.json` → isi `package.json` tampil (memang boleh dilayani).
- `/@fs/<repo>/secrets/db_password.txt` (polos, `?raw??`, `?import&raw??`) dan `/@fs/<repo>/.env` → semuanya **403**, tanpa isi file.

Uji itu cakupannya lebih sempit, jadi dilengkapi dengan Cara 1 (Termux di HP, `curl` yang hanya mencetak kode HTTP, `http://<IP-laptop>:5173`; hasil dilaporkan developer):

- Kontrol positif `/@fs/<repo>/frontend/package.json` → **200**.
- Semua 3 file di `secrets/` (`abuseipdb_api_key.txt`, `db_password.txt`, `virustotal_api_key.txt`) × 3 varian (polos, `?raw??`, `?import&raw??`) → **403** (9 dari 9).
- `.env` × 3 varian → **403** (3 dari 3).

Jadi uji Keputusan 26 terpenuhi penuh lewat IP LAN dari perangkat lain (12 dari 12 varian 403 dengan kontrol 200). Prosedur hash Keputusan 27 tidak diperlukan.

## Known gaps baru (Tahap 0)

1. **Uji `/@fs` valid untuk Vite 8.3.5 pada hari ini saja.** Hasilnya bergantung pada versi Vite terpasang. Ulangi bila Vite di-upgrade, dan jalankan `npm audit` penuh sebelum setiap sesi `dev:lan` (Keputusan 25).
2. **Paragraf "Status" di README (baris 7) sudah usang** dan sudah usang sebelum tahap ini: masih menyebut sumber reputasi dan frontend belum ada. Tidak diubah karena di luar lingkup Tahap 0; perlu dirapikan di Tahap 4 atau PR docs sendiri.
3. **Rentang `^` di `package.json`.** Reproduksibilitas dijamin `package-lock.json` dan `npm ci`; `npm install` tanpa lockfile bisa menarik versi minor yang lebih baru.
4. **Warning deprecation Starlette/httpx** di pytest (`starlette.testclient` menyarankan `httpx2`) sudah ada sebelum tahap ini; tidak disentuh.

## Tahap 1 — Keputusan desain (disetujui developer dengan perubahan, 2 Nov 2026)

Status: **DISETUJUI dengan perubahan** (lihat "Keputusan developer atas rencana" di bawah: simulasi memakai ungu, `pending` abu netral, merah untuk kegagalan dicatat sebagai pengecualian Keputusan 10). Tahap 2–4 mengikuti rencana ini; perubahan = tanya dulu.

### Dasar dan batas

- Mode permukaan: **Operate** (meja kerja analis, bukan halaman pemasaran). Dunia visual hanya meminjamkan tipe, palet, kepadatan, dan satu gerakan khas; layout, navigasi, dan kontrol tetap standar web.
- Arah sudah dipaku brief (Keputusan 1, 2, 9, 10, 13 dan Aturan tampilan): tema gelap slate, satu aksen biru, warna verdict hanya untuk label, tanpa dependency/CDN, keberanian hanya di strip ringkasan. Karena itu **undian arah (concept tournament) tidak dijalankan**; yang diputuskan di sini hanya hal yang brief biarkan terbuka (angka warna, tipe, ukuran, bentuk strip).
- Skenario fisik: analis duduk di lab dengan laptop atau proyektor di ruangan yang diredupkan, membaca bukti beberapa menit per IP. Itu yang membuat tema gelap beralasan (Keputusan 10), bukan selera.
- Sumber kontras: dihitung dengan rumus kontras relatif WCAG 2.x pada hex di bawah (angka di kolom "Kontras").

### Warna inti (6, hex bernama)

| Nama | Hex | Peran | Kontras |
|---|---|---|---|
| Tanah | `#0E141B` | latar halaman dan area bukti | teks utama di atasnya 15,44:1 |
| Panel | `#151D27` | rel kiri/kanan, top bar, kartu | teks utama 14,16:1 |
| Garis | `#64768A` | batas kontrol (input, tombol, chip) dan fokus netral; pembatas dekoratif = warna yang sama pada 35% opasitas | 3,64:1 pada Panel, 3,97:1 pada Tanah (lolos 3:1 untuk batas kontrol) |
| Teks | `#E6EBF1` | teks utama, angka, IP | 14,16:1 pada Panel |
| Teks redup | `#9FADBD` | label sekunder, keterangan, waktu | 7,43:1 pada Panel |
| Aksen | `#5AA2FF` | **hanya** elemen interaktif: tombol utama, tautan, tab aktif, cincin fokus | 6,51:1 pada Panel; teks gelap `#06101C` di atas tombol Aksen 7,32:1 |

Seluruh antarmuka **tanpa hijau**, termasuk untuk "sukses" (keputusan developer 1). Kontras pembatas dekoratif sengaja rendah (≈1,3:1); batas yang dibutuhkan untuk mengenali kontrol memakai Garis penuh.

### Warna semantik (wajib dari Aturan tampilan, di luar hitungan 6)

Label selalu **teks + warna** (Aturan tampilan 8). Kolom "Chip" untuk daftar/riwayat; kolom "Strip" hanya untuk blok skor di strip ringkasan (satu-satunya area berwarna solid).

| Keadaan | Chip (teks / latar) | Kontras chip | Strip (teks / isi blok) | Kontras strip |
|---|---|---|---|---|
| `RENDAH` | `#D3DCE6` / `#2A3644` (abu-slate, bukan biru, bukan hijau) | 8,86:1 | `#D3DCE6` / `#2A3644` + garis Garis | 8,86:1 |
| `PERLU_PEMERIKSAAN` | `#F5D547` / `#2B2610` (kuning) | 10,44:1 | `#1A1500` / `#E8C21A` | 10,57:1 |
| `TINGGI` | `#FFA347` / `#33200C` (oranye) | 7,82:1 | `#1A0F02` / `#F08A24` | 7,52:1 |
| `SANGAT_TINGGI` | `#FF8A80` / `#3D1517` (merah) | 6,98:1 | `#FFFFFF` / `#C4262E` | 5,73:1 |
| `null` → "N/A" | `#B4C0CE` pada Panel, **batas putus-putus** | 9,19:1 | `#B4C0CE`, tanpa isi, batas putus-putus | 9,19:1 |
| `SUMBER_SIMULASI` (warna khusus non-verdict, **ungu**) | teks `#E9D5FF` / latar `#2A1A40`, bingkai tebal 4px bergaris diagonal `#C084FC`/`#2A1A40`, teks "SIMULASI · bukan data nyata" | teks 11,68:1; garis `#C084FC` 7,00:1 pada Tanah; pola 6,02:1 | sama, membingkai seluruh strip | 11,68:1 |
| Gagal (`failed`, 501/502, sumber `ERROR`; pengecualian Keputusan 10) | teks dan batas `#FF8A80` **tanpa isi** + glif "✕" + teks "Gagal" | 8,11:1 pada Tanah, 7,44:1 pada Panel | n/a | n/a |
| `pending` | abu netral: teks `#B4C0CE` pada Panel, batas Garis, glif "…" + teks "Sedang diproses (pending)" | 9,19:1 | n/a | n/a |
| Terkirim `mock_sent` | chip **berbatas Garis tanpa isi**, teks `#E6EBF1` "Terkirim (mock)", tanpa hijau | 14,16:1 | n/a | n/a |
| Terkirim `sent` | chip netral yang sama + glif "✓" + teks "Terkirim ke MISP" | 14,16:1 | n/a | n/a |

Jarak warna ungu simulasi dari Aksen biru (`#5AA2FF`, hue 214°): `#C084FC` hue 270°, ΔE76 ≈ 40 (jelas berbeda untuk penglihatan normal). Pasangan ungu–biru mudah tertukar bagi penderita buta warna, karena itu pembedanya **tidak boleh hanya warna**: bingkai tebal bergaris diagonal dan teks tetap wajib. Aksen hanya untuk elemen interaktif; simulasi tidak pernah tampil sebagai tombol atau tautan.

### Tipografi (tanpa unduhan, tanpa CDN; Keputusan 13a)

- **UI:** `system-ui, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif`. Satu keluarga untuk judul, label, tombol, dan teks; tidak ada display font.
- **Mono (syarat fungsional, Keputusan 13b):** `ui-monospace, "SF Mono", Menlo, Consolas, "DejaVu Sans Mono", monospace` untuk IP, `misp_event_uuid`, kode status/flag/reason (`OK_SIGNAL`, `RATE_LIMIT`), angka `http_status`, dan Raw JSON.
- **Angka:** `font-variant-numeric: tabular-nums` untuk skor, cakupan, dan waktu.
- **Skala tetap** (rem, basis 16px, rasio ≈1,2; bukan fluid):

| Token | Ukuran | Dipakai untuk |
|---|---|---|
| `kecil` | 0,75rem (12px) | kode di samping penjelasan, keterangan waktu; **tidak ada teks di bawah 12px** |
| `padat` | 0,875rem (14px) | baris tabel/riwayat, bukti per sumber, chip |
| `isi` | 1rem (16px) | teks utama, input, tombol |
| `sub` | 1,2rem | judul tab dan bagian rel kanan |
| `judul` | 1,44rem | nama halaman (login), IP di strip |
| `skor` | 4rem (64px), bobot 700 | **hanya** angka skor / "N/A" di strip ringkasan |

Panjang baris teks penjelasan ≤ 75ch; tabel boleh lebih lebar.

### Layout (ASCII)

Halaman login: satu formulir kecil di tengah, bukan hero.

```
┌──────────────────────────────────────────────┐
│                                              │
│                    SOC16 TI                  │
│        Masuk untuk memeriksa reputasi IP     │
│                                              │
│        Username  [____________________]     │
│        Password  [____________________]     │
│                                              │
│        [ Masuk ]                             │
│        (pesan error satu baris, inline)      │
│                                              │
└──────────────────────────────────────────────┘
```

Workbench ≥ 1024px. Lebar rel: **272 / fluid / 304px** pada ≥ 1280px; **232 / fluid / 264px** pada 1024–1279px. Rel kanan sticky.

```
┌ TOP BAR 56px (Panel) ───────────────────────────────────────────────────────────────────────────┐
│ SOC16 TI │ [ IPv4 publik, mis. 118.25.6.39 ] [Cek IP] │ Workbench · Kiriman MISP │ MISP: mock │ user · role │ sesi 14.33 WIB │ Keluar │
├ REL KIRI (Panel) ──┬ PANEL TENGAH (Tanah) ─────────────────────────────┬ REL KANAN (Panel, sticky) ──┤
│ Riwayat            │ ╔ STRIP RINGKASAN ═══════════════════════════════╗ │ Cakupan 2/2                 │
│ [saring IP…]       │ ║ 1.1.1.1  COMPLETE        ▨ SIMULASI · bukan data║ │ ■ AbuseIPDB   ■ VirusTotal  │
│ ──────────────     │ ║ ┌────────┐                                      ║ │ Kesegaran                   │
│ 1.1.1.1  SANGAT_T… │ ║ │  92.4  │ SANGAT_TINGGI                        ║ │ Flag (chip berpenjelasan)   │
│ 1.0.0.1  TINGGI    │ ║ └────────┘ Indikasi sangat tinggi · periksa     ║ │ ──────────────              │
│ 8.8.8.8  N/A       │ ║            segera, tanpa auto-block             ║ │ Status MISP / form kirim    │
│ …                  │ ╚═════════════════════════════════════════════════╝ │ [Salin hasil] [Cek ulang]   │
│ [Muat lagi]        │ Ringkasan │ AbuseIPDB │ VirusTotal │ Raw JSON       │ Pivot ↗ AbuseIPDB · VT      │
│                    │ (bukti per sumber)                                  │                             │
├────────────────────┴─────────────────────────────────────────────────────┴─────────────────────────────┤
│ FOOTER  Sumber: AbuseIPDB, VirusTotal · scoring_version · Skor = label indikasi, bukan probabilitas     │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Di bawah 1024px panel ditumpuk dalam urutan **bukti → keputusan → riwayat** (Keputusan 9). Top bar menjadi dua baris (judul + akun di atas, search + nav di bawah). Pada 1024–1279px strip membungkus jadi dua baris (IP/status di atas, skor + label di bawah).

**Tahap 1 hanya membangun shell dan login**: top bar, tiga panel kosong berisi teks placeholder, footer, serta formulir login. Strip dan isi panel dibangun di Tahap 2 mengikuti rencana ini.

### Gerakan khas (satu-satunya "keberanian"; Keputusan 13e)

**Strip ringkasan** adalah satu-satunya area dengan blok warna solid dan teks 64px: skor (atau "N/A") di blok berwarna verdict, label di sampingnya, dan **pengukur cakupan** berupa dua sel bernama (AbuseIPDB, VirusTotal) yang terisi bila sumber menjawab dan putus-putus kosong (dengan kode `reason`) bila tidak. Sisa layar tenang: Panel dan Tanah, teks 14–16px, tanpa isi warna kecuali chip label. Untuk `null`, blok skor tidak berisi warna dan menampilkan "N/A" beserta `assessment_status`, sehingga tidak ada kondisi yang bisa dibaca "aman".

### Komponen dan keadaan

- Kontrol standar saja: tombol (utama = isi Aksen; sekunder = berbatas Garis; tanpa tombol bahaya karena tidak ada aksi destruktif), input teks, tab bergaris bawah, tabel polos, chip. Tanpa ikon pack: glif teks ("✕", "✓", "↗", "▨") atau SVG inline kecil bila perlu.
- Setiap komponen interaktif punya keadaan: default, hover, **fokus**, aktif, nonaktif, memuat, galat. Fokus: cincin 2px Aksen dengan offset 2px (6,51:1 pada Panel), memakai `:focus-visible`, terlihat di semua kontrol; semua kontrol terjangkau keyboard.
- Memuat: satu keadaan di strip (batang tak-tentu + teks "Memeriksa… bisa sampai belasan detik"); tombol berubah "Memeriksa…" dan nonaktif.
- Keadaan kosong menjelaskan langkah berikutnya (satu kalimat), bukan layar sambutan.

### Gerakan (motion)

Hanya sebagai respons aksi user, 150–200 ms: buka/tutup panel konfirmasi MISP, pergantian tab, batang memuat saat pengecekan berjalan. Tanpa animasi saat halaman dimuat dan tanpa efek dekoratif. Di bawah `prefers-reduced-motion: reduce`: semua transisi 0 ms dan batang memuat diganti teks statis "Memeriksa…".

### Prinsip

1. Layar menjawab tiga hal: IP apa, apa bukti tiap sumber, apa aksi analis. Selain itu dibuang.
2. Satu tempat berani (strip); sisanya tenang. Warna solid besar hanya di blok skor.
3. Warna tidak pernah sendirian: setiap status punya teks, dan bentuknya berbeda bila warnanya sama.
4. Ketidakpastian terlihat: N/A, putus-putus, dan bingkai simulasi tidak boleh tampak seperti kondisi normal.
5. Kontrol yang dikenal analis, tanpa kontrol baru untuk gaya.
6. Terbaca di proyektor 1280×720 dan 1024×768: tidak ada teks di bawah 12px, kontras AA ke atas.

### Keputusan developer atas rencana (2 Nov 2026)

1. **Tanpa hijau sama sekali: disetujui.** `mock_sent` = chip netral berbatas "Terkirim (mock)". `sent` (MISP asli) juga netral, dengan glif centang dan teks "Terkirim ke MISP".
2. **DIUBAH: `SUMBER_SIMULASI` dan `pending` tidak memakai kuning.** Kuning adalah warna verdict (`PERLU_PEMERIKSAAN`) dan Keputusan 10 membatasi warna verdict hanya untuk label indikasi. Simulasi memakai satu warna khusus non-verdict (ungu) + pola diagonal + bingkai tebal + teks "SIMULASI · bukan data nyata", cukup berbeda dari biru Aksen (tabel di atas). `pending` memakai abu netral + teks "Sedang diproses (pending)". Aturan tampilan 4 di `TASK-03-frontend-workbench.md` sudah diperbarui, kontras dihitung ulang.
3. **Merah untuk `failed`: disetujui sebagai PENGECUALIAN eksplisit Keputusan 10** (status kegagalan, bukan verdict). Bentuk berbeda: `failed` = chip berbingkai tanpa isi + ikon ✕ + teks "Gagal"; `SANGAT_TINGGI` = chip terisi + teks label. Tercatat di Keputusan 10 dan Aturan tampilan 5.
4. **System font stack disetujui** untuk sans dan monospace. `.woff2` SIL OFL hanya bila diminta nanti (tanya dulu).
5. **6 warna inti + 7 keadaan semantik diterima**; undian arah (concept tournament) tidak dijalankan, disetujui.
6. **Plugin Impeccable**, bukan `frontend-design` resmi, dipilih dengan sengaja: github.com/pbakaus/impeccable, Apache-2.0, versi **4.8.0** (`SKILL.md` dan `impeccable --version` terpasang). Keputusan 13 diperbarui; butir 13a–13h tetap, 13i ditambahkan.

Catatan verifikasi untuk butir 6: yang dibaca dari berkas terpasang adalah `version: 4.8.0` dan `license: Apache 2.0` di `~/.claude/skills/impeccable/SKILL.md`, serta URL repo yang disebut di berkas skill. Impeccable terpasang sebagai skill mandiri di `~/.claude/skills/` (tidak tercantum di `installed_plugins.json`), sehingga tidak tampil di `/plugin`. `scripts/VERSION` berisi `0.1.18` (kemungkinan versi mesin pendukung, bukan versi plugin); lisensi dan repo tidak diverifikasi di luar berkas lokal.

### Risiko yang tersisa

- **Pada 1024px** panel tengah hanya ±528px (rel 232 + 264). Strip membungkus dua baris; tabel bukti di tab harus bisa menggulir horizontal atau membungkus. Diuji di Tahap 4.
- **Ungu dan biru** mudah tertukar bagi penderita buta warna; ditutup oleh pola, bingkai tebal, dan teks, bukan warna saja. Perlu dicek lewat screenshot di Tahap 4.

### Lokasi berkas Impeccable (Keputusan 13i)

- `PRODUCT.md` dipindah ke `frontend/PRODUCT.md`; `DESIGN.md` nanti di `frontend/DESIGN.md`. Keduanya boleh di-commit.
- Dengan `PRODUCT.md` di `frontend/`, root proyek Impeccable adalah `frontend/`. Jalankan dari `frontend/` atau beri `--target frontend/...`; dari root repo tanpa `--target`, `impeccable context` tidak menemukannya (diuji).
- `.impeccable/` (state, config, cache lokal) masuk `.gitignore` sebagai pencegahan. Bila nanti `DESIGN.md` membutuhkan `.impeccable/design.json` di repo, periksa isinya (tidak boleh memuat path pribadi) sebelum meng-commit-nya dengan sengaja.

### Setelah disetujui

- Tahap 1 membangun login dan shell sesuai rencana ini, lalu `DESIGN.md` ditulis dari shell yang sudah jadi (lewat Impeccable, `impeccable-documenter`), bukan sebelum kode.
- Bukti tampilan: developer mengirim screenshot (Keputusan 13h); tidak ada Playwright atau alat baru.

## Tahap 1 — Pelaksanaan

Dikerjakan di branch `feat/task-03-tahap-1-api-client-login-shell`. Tidak ada perubahan backend. Rencana desain di atas diikuti.

**Yang dibangun** (`frontend/src`): `api/types.ts` (tipe tulis tangan, diverifikasi terhadap `backend/app`: `ReasonCode` 10 nilai, `Indication` 4, `Role` 3, `SourceReason`, flag), `api/client.ts` (klien `fetch`), `lib/errors.ts`, `lib/session.ts`, `lib/can.ts`, `lib/health.ts`, `auth/` (`TokenStore`, `performLogin`, `AuthProvider`, `useAuth`), `components/` (`LoginPage`, `Shell`, `TopBar`, `Button`, `Chip`, `Icon`, `useHealth`), `index.css` (token desain), serta `frontend/PRODUCT.md` dan `frontend/DESIGN.md`.

### Keputusan dan penyimpangan dari rencana

1. **`DESIGN.md` ditulis dari shell yang sudah jadi, bukan sebelum kode.** Tahap 1 butir 0 dan Keputusan 13g menyuruh menulisnya setelah rencana disetujui dan sebelum butir 1. Alasan penyimpangan: Impeccable memang mendokumentasikan sistem dari artefak yang terbangun (bukan dari niat), sehingga nilai radius, transisi, dan spasi bisa diambil dari CSS hasil build. Dokumen ini hanya memuat yang sudah terbangun; strip ringkasan ditandai "Tahap 2". Sidecar `.impeccable/design.json` **tidak** ditulis: berada di folder yang di-`.gitignore`, dan live mode Impeccable tidak dikonfigurasi. Kalimat deskriptif di `DESIGN.md` (nama "Meja Kerja Analis di Ruang Redup", nama warna, aturan bernama) adalah usulan saya dan belum dikonfirmasi developer, sedangkan panduan Impeccable meminta ditanyakan; silakan ubah bila tidak cocok.
2. **Jam sesi dirakit dari `formatToParts`, bukan `format()`.** Diukur di Node 26: `Intl.DateTimeFormat('id-ID', …).format()` menghasilkan `14.33` (titik), sedangkan Keputusan 15 menulis `14:33`. Jam dan menit diambil dari `formatToParts` dan digabung dengan `:`, supaya hasilnya sama di semua peramban. Zona tetap `Asia/Jakarta`, `hourCycle: 'h23'` (tengah malam `00:05`, bukan `24:05`).
3. **Ikon gambar sendiri (SVG), bukan glif teks.** `craft-floor.md` Impeccable menolak glif Unicode sebagai pengganti ikon; Keputusan 2 hanya melarang icon pack. Baru satu ikon dipakai di Tahap 1 (✕ untuk kegagalan). Ikon ✓ dan ↗ menyusul di Tahap 2–3.
4. **Revalidasi sesi lewat `GET /auth/me`** pada setiap pergantian tampilan (dan saat shell dimuat). Tanpa ini shell kosong tidak pernah memanggil API terautentikasi, sehingga cek "token tidak valid → kembali ke login" mustahil dijalankan. Konsekuensinya: sesi yang dinonaktifkan atau kedaluwarsa baru terdeteksi saat user berpindah tampilan atau melakukan aksi, bukan secara proaktif (sesuai Keputusan 22).
5. **401 basi diabaikan.** Klien hanya memicu logout global bila token yang mengirim request masih token saat ini; respons 401 dari sesi sebelumnya (setelah logout atau login ulang) tidak mengeluarkan sesi baru. Logout juga membatalkan request yang masih berjalan (`AbortController`).
6. **Pengecualian 401 untuk login per-pemanggilan** (`handleUnauthorized: false`), bukan pencocokan URL. Panggilan `GET /auth/me` tepat setelah login juga memakainya; bila gagal, token dibuang (tidak ada keadaan setengah login).
7. **Token di `TokenStore`** (kelas dengan field privat `#token`), bukan `useRef`, karena aturan lint React menandai akses ref di dalam closure yang dibuat saat render. Token tidak tampil di `JSON.stringify` maupun `Object.keys`. `credentials: 'omit'` dan `cache: 'no-store'` pada semua `fetch`.
8. **`/health` diulang tiap 30 detik** (selain saat berganti tampilan) agar badge tidak menampilkan "sehat" untuk backend yang sudah mati. 503 dengan badan `HealthResponse` → "API: DB error"; backend mati atau badan bukan `HealthResponse` → "API: tidak terjangkau". Sebelum ada hasil, badge menampilkan "MISP: …" (tidak mengarang).
9. **Galat validasi FastAPI tidak pernah menyalin `input` atau `ctx`** (422 pada login bisa memantulkan password); hanya nama field yang ditampilkan. Ada test dengan nilai pancingan.
10. **Urutan DOM panel = urutan visual desktop** (riwayat, bukti, keputusan); layar < 1024px memakai CSS `order` (bukti → keputusan → riwayat). Konsekuensi: Tab di layar sempit melewati riwayat lebih dulu.
11. **Kolom pencarian IP belum ada di top bar**; itu bagian Tahap 2 (Keputusan di peta layar). Tahap 1 memuat judul, navigasi, badge, role, jam sesi, dan Keluar.
12. **Lint memakai Oxlint** dan sempat menandai dua hal yang diperbaiki, bukan diabaikan: kasus test `1e999` yang ternyata menjadi `null` lewat `JSON.stringify` (sekarang diuji dengan JSON mentah), dan akses ref saat render.

### Bukti uji otomatis

- 78 test Vitest: klien API (header Bearer, `auth:false`, form-urlencoded, 401 normal/basi/setelah logout, jaringan, bukan-JSON, 503 membawa badan, `abortAll`), parser galat (tiga bentuk 422, 404/409/501/502, tanpa salin `input`), `session` (base64url panjang mod 4 berbeda, karakter `-`/`_`, UTF-8, `exp` rusak, jam WIB), `can` (viewer tanpa cek dan MISP; analyst tanpa `can_send_misp` tanpa MISP), `health`, alur login (`performLogin`), dan render markup `LoginPage`/`Shell` lewat `react-dom/server` (`method="post"`, atribut `autocomplete`, tanpa tautan eksternal, urutan panel, jam sesi, tanpa `%`).
- **Uji mutasi** (merusak kode sengaja, memastikan test gagal, lalu memulihkan): dekode base64url, penjaga 401 basi, penyalinan `input`, `method="post"`, urutan panel `order-*`, token tidak dibuang saat `/auth/me` gagal, dan `/auth/me` ikut logout global semuanya **tertangkap**. Dua temuan: (a) pengecualian login awalnya **lolos** karena test memakai `auth:false`, sehingga penjaga lain yang menahannya; test yang tepat sasaran ditambahkan dan kini menangkapnya. (b) Satu mutasi (membalik flag pada `POST /auth/login`) tidak menggagalkan test karena ekuivalen: request itu tanpa token, jadi flag tidak berpengaruh.
- Smoke dev server (`npm run dev`, localhost): semua modul (`main.tsx`, `App.tsx`, `AuthProvider.tsx`, `Shell.tsx`, `LoginPage.tsx`, `TopBar.tsx`, `index.css`) ter-compile (HTTP 200), log bebas error/warn, proxy `/api/v1/health` 200, `/api/v1/auth/me` tanpa token 401. Detektor Impeccable (`detect --json src index.html`) tanpa temuan. Dev server dihentikan.

### "Cek selesai" Tahap 1 — langkah developer (belum dijalankan)

Agen tidak memegang password akun seed, jadi login nyata dan paksa-401 belum diuji di peramban. Jalankan sendiri:

1. `docker compose up -d`, lalu `cd frontend; npm run dev`, buka `http://localhost:5173`.
2. **Login 3 role** (admin, analyst, viewer): top bar menampilkan username, badge role yang benar, "MISP: mock", dan "sesi berakhir HH:mm WIB".
3. **Password salah** → pesan "Username atau password salah" (bukan "Sesi berakhir"); isian password terkosongkan.
4. **Paksa 401, cara A (tanpa ubah konfigurasi):** login sebagai viewer di UI. Di Swagger (`http://127.0.0.1:8000/docs`) login sebagai admin lalu `PATCH /api/v1/admin/users/{id}` dengan `{"is_active": false}` untuk akun viewer. Di UI, klik "Kiriman MISP" → kembali ke login dengan "Sesi berakhir, login lagi". Aktifkan lagi akun viewer setelahnya (`{"is_active": true}`). Admin tidak bisa menonaktifkan dirinya sendiri.
5. **Paksa 401, cara B (kedaluwarsa):** ubah sementara `JWT_EXPIRE_MINUTES=1` di `.env`, `docker compose up -d --force-recreate api`, login, tunggu > 1 menit, ganti tampilan. Kembalikan nilainya ke 30 dan recreate lagi.
6. **Refresh halaman** (F5) → kembali ke login (konsekuensi Keputusan 3).
7. **Backend mati:** `docker compose stop api` → badge menjadi "API: tidak terjangkau" dalam ≤ 30 detik atau saat berganti tampilan; `docker compose start api` memulihkannya.
8. **Pemeriksaan peramban (DevTools):** tab Application → Local Storage, Session Storage, Cookies kosong; tab Network → hanya request ke `localhost:5173` (tanpa CDN); setelah submit login, URL tidak berisi username/password.
9. **Screenshot untuk kritik desain** (Keputusan 13h), dikirim ke agen: login dan shell pada 1280×720, 1024×768, dan lebar < 1024px (panel bertumpuk).

## Known gaps baru (Tahap 1)

1. **Uji manual login nyata, paksa-401, dan screenshot belum dilakukan** (butuh akun seed dan peramban); daftar langkah di atas.
2. **Tidak ada uji peramban otomatis** (Playwright dilarang, Keputusan 13h; testing-library tidak dipakai, Keputusan 6). Perilaku klik dan submit di peramban sungguhan hanya tercakup oleh logika murni (`performLogin`, klien API) dan render markup, bukan oleh interaksi nyata.
3. **Deteksi sesi berakhir tidak proaktif**: baru terjadi saat ganti tampilan atau aksi terautentikasi. Jam "sesi berakhir" berasal dari `exp`, sedangkan penegakannya tetap 401 dari backend.
4. **Tab order di layar < 1024px** lebih dulu melewati riwayat (keputusan 10).
5. **Kalimat deskriptif `DESIGN.md` belum dikonfirmasi developer** (keputusan 1).
6. **Sidecar `.impeccable/design.json` tidak ada**; live mode Impeccable tidak dikonfigurasi. Bila nanti dibutuhkan, periksa isinya (tanpa path pribadi) sebelum di-commit.

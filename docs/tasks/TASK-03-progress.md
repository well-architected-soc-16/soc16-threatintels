# TASK-03 — Progress

Diperbarui: 2026-11-03 (Tahap 3). Rujukan: [`TASK-03-frontend-workbench.md`](TASK-03-frontend-workbench.md), issue #28.

## Status per tahap

| Tahap | Isi | PR | Status |
|---|---|---|---|
| Rencana | Rencana TASK-03, keputusan grilling (Keputusan 13-28), `PRODUCT.md` | #30 | Selesai, ter-merge |
| 0 | Scaffold `frontend/`, Tailwind, proxy, gerbang kualitas | #31 | Selesai, ter-merge; uji LAN proxy, `:8000`, dan `/@fs` (12 dari 12 varian 403) lolos |
| 1 | Rencana desain, API client, login, shell layout | #32 | Selesai, ter-merge. Uji manual developer lolos (3 Nov) |
| 2 | Cek IP, bukti, riwayat | #33 | Selesai, ter-merge. Seluruh langkah "Cek selesai" 1-12 lulus (developer: 1-4 dan 9; agen di Brave headless: 5-8 dan 10-12) |
| 3 | Kirim ke MISP, tampilan Kiriman MISP | | Selesai di branch lokal. Uji developer (a, c, d, e sebagian) dan uji peramban agen (klik ganda, konfirmasi, fokus, mode live: kirim gagal 501, kirim ulang, konfirmasi IP yang sama) lulus; menunggu jawaban dua keputusan agen dan "push" |
| 4 | Bukti demo, uji akses negatif, polish, README | | Belum |

Hasil terakhir (Tahap 3): backend `pytest` **763 passed**, `ruff check` dan `ruff format --check` bersih, `db` dan `api` `healthy`. Frontend `npm run lint` (tanpa warning), `npm run build`, `npm test` (**376 passed**, 18 file), `npm audit --omit=dev` dan `npm audit` keduanya **0 vulnerabilities**; grep `localStorage|sessionStorage|document.cookie|console.|dangerouslySetInnerHTML|VITE_|window.confirm|innerHTML` di `frontend/src` kosong (exit 1).

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

- Tahap 1 membangun login dan shell sesuai rencana ini, lalu `DESIGN.md` ditulis dari shell yang sudah jadi, bukan sebelum kode (lihat penyimpangan 1 di "Tahap 1 — Pelaksanaan").
- Bukti tampilan: developer mengirim screenshot (Keputusan 13h); tidak ada Playwright atau alat baru.

## Tahap 1 — Pelaksanaan

Dikerjakan di branch `feat/task-03-tahap-1-api-client-login-shell`. Tidak ada perubahan backend. Rencana desain di atas diikuti.

**Yang dibangun** (`frontend/src`): `api/types.ts` (tipe tulis tangan, diverifikasi terhadap `backend/app`: `ReasonCode` 10 nilai, `Indication` 4, `Role` 3, `SourceReason`, flag), `api/client.ts` (klien `fetch`), `lib/errors.ts`, `lib/session.ts`, `lib/can.ts`, `lib/health.ts`, `auth/` (`TokenStore`, `performLogin`, `AuthProvider`, `useAuth`), `components/` (`LoginPage`, `Shell`, `TopBar`, `Button`, `Chip`, `Icon`, `useHealth`), `index.css` (token desain), serta `frontend/PRODUCT.md` dan `frontend/DESIGN.md`.

### Keputusan dan penyimpangan dari rencana

1. **`DESIGN.md` ditulis dari shell yang sudah jadi, bukan sebelum kode.** Tahap 1 butir 0 dan Keputusan 13g menyuruh menulisnya setelah rencana disetujui dan sebelum butir 1. Alasan penyimpangan: Impeccable memang mendokumentasikan sistem dari artefak yang terbangun (bukan dari niat), sehingga nilai radius, transisi, dan spasi bisa diambil dari CSS hasil build. **Cara penulisan:** ditulis tangan oleh agen mengikuti `document.md` (scan mode); subagent `impeccable-documenter` **tidak** dijalankan, dan langkah 3 alur itu (wawancara bahasa deskriptif: Creative North Star, nama warna, filosofi elevasi) **dilewati**. Finish reviewer dan `comp-diff` juga tidak dijalankan (Keputusan 13h: bukti tampilan lewat screenshot developer, tanpa alat baru). Dokumen ini hanya memuat yang sudah terbangun; strip ringkasan ditandai "Tahap 2". Sidecar `.impeccable/design.json` **tidak** ditulis: berada di folder yang di-`.gitignore`, dan live mode Impeccable tidak dikonfigurasi. Kalimat deskriptif di `DESIGN.md` (nama "Meja Kerja Analis di Ruang Redup", nama warna, aturan bernama) adalah usulan saya dan belum dikonfirmasi developer, sedangkan panduan Impeccable meminta ditanyakan; silakan ubah bila tidak cocok.
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
12. **Backend mati di balik proxy Vite = HTTP 502, bukan kegagalan `fetch`.** Diukur dengan `docker compose stop api` lalu `curl` ke dev server (localhost): `POST /auth/login`, `GET /health`, dan `GET /auth/me` semuanya menjawab **502, `content-type: text/plain`, 0 byte** (log Vite: `http proxy error … ECONNREFUSED 127.0.0.1:8000`). Sebelum perbaikan ini, login memetakan 502 ke `unexpected` ("Login gagal. Coba lagi…") alih-alih "API tidak terjangkau". Sekarang predikat bersama `isUnreachable` (di `api/client.ts`) menganggap `fetch` gagal serta 502/503/504 **tanpa badan JSON** sebagai tidak terjangkau, dipakai oleh login, `parseCheckError`, dan `parseIocError`. 502 dengan badan `IocOut` (kegagalan MISP) dan 503 dengan badan `HealthResponse` tetap diperlakukan sebagai balasan backend; 500 tanpa badan tetap galat server. API dinyalakan kembali dan `healthy` setelah pengukuran.
13. **Lint memakai Oxlint** dan sempat menandai dua hal yang diperbaiki, bukan diabaikan: kasus test `1e999` yang ternyata menjadi `null` lewat `JSON.stringify` (sekarang diuji dengan JSON mentah), dan akses ref saat render.

### Bukti uji otomatis

- 92 test Vitest: klien API (header Bearer, `auth:false`, form-urlencoded, 401 normal/basi/setelah logout, jaringan, bukan-JSON, 503 membawa badan, `abortAll`, predikat `isUnreachable`), parser galat (tiga bentuk 422, 404/409/501/502, tanpa salin `input`), `session` (base64url panjang mod 4 berbeda, karakter `-`/`_`, UTF-8, `exp` rusak, jam WIB), `can` (viewer tanpa cek dan MISP; analyst tanpa `can_send_misp` tanpa MISP), `health`, alur login (`performLogin`), render markup `LoginPage`/`Shell` lewat `react-dom/server`, serta penjaga palet (`design.test.ts`: tidak ada warna hue 75–170°, `RENDAH` abu-slate, simulasi ≥ 40° dari aksen) (`method="post"`, atribut `autocomplete`, tanpa tautan eksternal, urutan panel, jam sesi, tanpa `%`).
- **Uji mutasi** (merusak kode sengaja, memastikan test gagal, lalu memulihkan): dekode base64url, penjaga 401 basi, penyalinan `input`, `method="post"`, urutan panel `order-*`, token tidak dibuang saat `/auth/me` gagal, `/auth/me` ikut logout global, predikat `isUnreachable` (dilonggarkan dan dihapus syarat badan kosongnya), serta penjaga palet (RENDAH dikehijauan, token hijau baru, warna format `oklch` yang tak terbaca parser, ungu digeser dekat biru) semuanya **tertangkap**. Dua temuan: (a) pengecualian login awalnya **lolos** karena test memakai `auth:false`, sehingga penjaga lain yang menahannya; test yang tepat sasaran ditambahkan dan kini menangkapnya. (b) Satu mutasi (membalik flag pada `POST /auth/login`) tidak menggagalkan test karena ekuivalen: request itu tanpa token, jadi flag tidak berpengaruh.
- Smoke dev server (`npm run dev`, localhost): semua modul (`main.tsx`, `App.tsx`, `AuthProvider.tsx`, `Shell.tsx`, `LoginPage.tsx`, `TopBar.tsx`, `index.css`) ter-compile (HTTP 200), log bebas error/warn, proxy `/api/v1/health` 200, `/api/v1/auth/me` tanpa token 401. Detektor Impeccable (`detect --json src index.html`) tanpa temuan. Dev server dihentikan.

**Pelajaran pengujian:** versi pertama `design.test.ts` membaca CSS lewat `import … ?raw`, tetapi Vitest mengosongkan isi file CSS yang diimpor, sehingga test gagal pada file yang belum diubah dan hasil mutasinya tidak bermakna. Ditemukan karena baseline dijalankan lebih dulu; test dipindah ke akar `frontend/` dan membaca dengan `node:fs`. Uji mutasi hanya sah bila baseline lulus.

### "Cek selesai" Tahap 1 — hasil uji manual developer (3 Nov 2026)

Dilaporkan developer (bukan diamati agen). Lolos: login 3 role (admin, analyst, viewer); password salah; paksa 401 (pesan "Sesi berakhir, login lagi"); F5 kembali ke login; API dihentikan menampilkan "API tidak terjangkau"; storage peramban kosong; tidak ada request keluar origin. Satu temuan yang dijelaskan developer: `?token=` yang terlihat di tab Network adalah WebSocket `vite-hmr` (hot reload dev server), bukan token login. Screenshot 1280×720, 1024×768, dan 800×390 sudah dibuat developer (disimpan di luar repo).

Catatan polish dari developer: **panel samping tidak setinggi area utama di desktop** (dicatat sebagai known gap 7). Penyebab yang terbaca dari kode: kedua `aside` memakai `lg:self-start` dan `lg:sticky` dengan `max-h`, sehingga tingginya mengikuti isi, bukan tinggi baris grid, dan warna latar Panel berhenti di bawah isi.

Jawaban developer atas pertanyaan agen: (1) pesan yang terpotong memang "bila perlu", tidak ada lanjutan; (2) nama di `DESIGN.md` (North Star, nama warna, aturan bernama) **tetap**, dengan syarat aturan No Green tidak bentrok dengan `RENDAH` (diverifikasi: tidak ada warna di rentang hijau; `RENDAH` hue 212°, saturasi 24–28%; ditambah penjaga otomatis dan kalimat penegas di `DESIGN.md`); (3) Impeccable sebagai skill mandiri, versi 4.8.0.

### Langkah uji manual Tahap 1 (sudah dijalankan developer; disimpan sebagai prosedur ulang)

Agen tidak memegang password akun seed, jadi login nyata dan paksa-401 belum diuji di peramban. Jalankan sendiri:

1. `docker compose up -d`, lalu `cd frontend; npm run dev`, buka `http://localhost:5173`.
2. **Login 3 role** (admin, analyst, viewer): top bar menampilkan username, badge role yang benar, "MISP: mock", dan "sesi berakhir HH:mm WIB".
3. **Password salah** → pesan "Username atau password salah" (bukan "Sesi berakhir"); isian password terkosongkan.
4. **Paksa 401, cara A (tanpa ubah konfigurasi):** login sebagai viewer di UI. Di Swagger (`http://127.0.0.1:8000/docs`) login sebagai admin lalu `PATCH /api/v1/admin/users/{id}` dengan `{"is_active": false}` untuk akun viewer. Di UI, klik "Kiriman MISP" → kembali ke login dengan "Sesi berakhir, login lagi". Aktifkan lagi akun viewer setelahnya (`{"is_active": true}`). Admin tidak bisa menonaktifkan dirinya sendiri. Akun nonaktif memang menghasilkan 401 `"Akun nonaktif"` (dibaca dari `backend/app/core/deps.py`, bukan 403), jadi langkah ini memicu logout global.
5. **Paksa 401, cara B (kedaluwarsa):** ubah sementara `JWT_EXPIRE_MINUTES=1` di `.env`, `docker compose up -d --force-recreate api`, login, tunggu > 1 menit, ganti tampilan. Kembalikan nilainya ke 30 dan recreate lagi.
6. **Refresh halaman** (F5) → kembali ke login (konsekuensi Keputusan 3).
7. **Backend mati:** `docker compose stop api` → badge menjadi "API: tidak terjangkau" dalam ≤ 30 detik atau saat berganti tampilan, dan percobaan login pada halaman login menampilkan "API tidak terjangkau. Pastikan backend berjalan, lalu coba lagi." (bukan "Login gagal"). `docker compose start api` memulihkannya.
8. **Pemeriksaan peramban (DevTools):** tab Application → Local Storage, Session Storage, Cookies kosong; tab Network → hanya request ke `localhost:5173` (tanpa CDN); setelah submit login, URL tidak berisi username/password.
9. **Screenshot untuk kritik desain** (Keputusan 13h), dikirim ke agen: login dan shell pada 1280×720, 1024×768, dan lebar < 1024px (panel bertumpuk).

## Known gaps baru (Tahap 1)

1. ~~Uji manual login nyata, paksa-401, dan screenshot~~ **sudah dilakukan developer** (lihat hasil di atas). Tersisa: bukti screenshot belum diperiksa agen untuk kritik desain (Keputusan 13h) — dikirim bila diminta.
2. **Tidak ada uji peramban otomatis** (Playwright dilarang, Keputusan 13h; testing-library tidak dipakai, Keputusan 6). Perilaku klik dan submit di peramban sungguhan hanya tercakup oleh logika murni (`performLogin`, klien API) dan render markup, bukan oleh interaksi nyata.
3. **Deteksi sesi berakhir tidak proaktif**: baru terjadi saat ganti tampilan atau aksi terautentikasi. Jam "sesi berakhir" berasal dari `exp`, sedangkan penegakannya tetap 401 dari backend.
4. **Tab order di layar < 1024px** lebih dulu melewati riwayat (keputusan 10).
5. ~~Kalimat deskriptif `DESIGN.md` belum dikonfirmasi~~ **dikonfirmasi developer: tetap** (3 Nov).
6. **Sidecar `.impeccable/design.json` tidak ada**; live mode Impeccable tidak dikonfigurasi. Bila nanti dibutuhkan, periksa isinya (tanpa path pribadi) sebelum di-commit.
7. **Panel samping tidak setinggi area utama di desktop** (polish, dijadwalkan di Tahap 4). Perbaikan kemungkinan: `lg:self-stretch` dengan isi yang sticky di dalamnya, atau latar Panel pada kolom grid.

## Tahap 2 — Pelaksanaan

Dikerjakan di branch `feat/task-03-tahap-2-workbench-cek-bukti-riwayat`. Tidak ada perubahan backend. Mengikuti "Keputusan desain" yang disetujui.

**Yang dibangun** (`frontend/src`):
- `lib/format.ts`: `formatScore`, `formatTime`, label indikasi, teks status/reason/flag, bukti defensif, rasio vendor, `buildCopyText`, `pivotLinks`. `lib/history.ts`: merge/dedup/filter riwayat.
- `api/checks.ts`, `api/guards.ts` (penjaga bentuk `CheckOut`/`CheckPage`), `workbench/store.ts` (alur kerja tanpa framework, dipakai React lewat `useSyncExternalStore`), `workbench/useWorkbench.ts`.
- Komponen: `SearchBar`, `HistoryRail`, `SummaryStrip` (blok skor + pengukur cakupan), `Tabs` (WAI-ARIA), `SourceTabs` (Ringkasan, AbuseIPDB, VirusTotal, Raw JSON), `EvidencePanel`, `DecisionRail` (cakupan, kesegaran, flag, Cek ulang, Salin hasil, pivot, slot MISP), `Badges`, `tone`; ikon ✓ dan tautan-keluar gambar sendiri; token strip dan `.simulasi-frame` di `index.css`.

### Keputusan dan penyimpangan dari rencana

1. **Alur kerja dalam store tanpa framework** (pola yang sama dengan `performLogin`), karena tidak ada peramban otomatis. Store menjaga: klik ganda diabaikan, token anti-basi untuk detail (klik A lalu B), submit mengalahkan GET detail yang berjalan, hasil `aborted` (logout) diabaikan diam-diam, 401 tidak menampilkan pesan, `offset = jumlah dimuat` dengan dedup per `id`.
2. **Penjaga bentuk di tepi** (`isCheckOut`/`isCheckPage`). Ditemukan saat test: store menerima balasan 2xx apa pun. Balasan JSON lain yang lolos (gateway, versi backend berbeda) kini ditolak dengan pesan "respons tidak terbaca", bukan membuat tampilan crash. Pada submit, pesan menyuruh memeriksa riwayat karena pengecekan mungkin sudah tersimpan di server.
3. **Butir [NANTI] yang dikerjakan:** Raw JSON, penyaring IP client-side ("menyaring yang sudah dimuat"), Salin hasil, dan tautan pivot. **Yang dilewati: bar 0-100 untuk `abuseConfidenceScore`.** Alasannya: Aturan tampilan 9 melarang grafik dan `craft-floor.md` menolak bar yang menggantikan isi; angkanya sudah tampil sebagai teks.
4. **Tautan pivot belum diverifikasi dari dokumentasi resmi.** AbuseIPDB `https://www.abuseipdb.com/check/<ip>` hanya terkonfirmasi dari contoh di [proyek pihak ketiga](https://github.com/df2k2/magento2-abuse-api); VirusTotal `https://www.virustotal.com/gui/ip-address/<ip>` hanya dari [satu issue GitHub (misp-modules #644)](https://www.github.com/MISP/misp-modules/issues/644). Tautan dibuat hanya dari `check.ip` berbentuk IPv4, di-encode, dan `target="_blank" rel="noopener noreferrer"`. Penutupnya: developer mengklik keduanya di peramban biasa (3 Nov 2026, dilaporkan developer): masing-masing membuka tab baru dengan halaman IP yang dituju dan datanya jelas. Kebenaran URL dengan demikian terbukti dalam praktik, tetapi tetap bukan dari dokumentasi resmi kedua situs; bila situs mengubah rutenya, tautan ini yang pertama rusak.
5. **Salin hasil di sesi `dev:lan` pasti memakai cadangan.** `navigator.clipboard` hanya ada di konteks aman (HTTPS atau localhost). Lewat `http://<IP-laptop>:5173` ia tidak ada, sehingga tombol menampilkan teks yang sudah terpilih di `<textarea>` readonly (jalur normal, bukan galat). Perlu diuji lewat `dev:lan`, bukan hanya di localhost.
6. **Badge cache hanya bila `retrieved_at` ada.** Check lama TASK-01 datang dengan `from_cache: false` bawaan; tanpa penjagaan ini semuanya salah berlabel "Ambil baru".
7. **Bukti sumber dibaca defensif:** field bertipe salah menjadi "—", kunci VirusTotal yang hilang menjadi "—" (bukan 0) dengan catatan rasio, penyebut 0 menjadi "tidak ada vendor yang menilai" (bukan `0 / 0` atau `NaN`), key `simulasi` tidak dirender, `lastReportedAt` UTC mentah tidak dirender (waktu dari `source_time`). Kamus status/reason/flag memakai `Object.hasOwn` sehingga kunci seperti `constructor` tidak menarik properti prototipe.
8. **Chip `SUMBER_SIMULASI` per-sumber disembunyikan** di baris Ringkasan dan tab sumber (sudah ada tag di strip, riwayat, dan rel keputusan; mengulangnya hanya menambah bising).
9. **Peringatan `HASIL_BERBEDA` netral** (kotak berbatas Teks, tanpa warna), karena kuning milik label verdict.
10. **Slot MISP di rel kanan** sudah menampilkan "Hasil simulasi tidak boleh dikirim ke MISP." untuk hasil simulasi (Aturan tampilan 4 tidak boleh ditunda); untuk hasil nyata berisi penanda "tersedia pada tahap berikutnya" sampai Tahap 3.
11. **Pencarian dan klik riwayat memindahkan ke tampilan Workbench** bila sedang di Kiriman MISP, supaya hasil terlihat.
12. **Kotak pencarian dikosongkan setelah berhasil**, dipertahankan bila gagal (agar mudah dikoreksi). Viewer tidak mendapat kotak pencarian maupun tombol Cek ulang (hanya tampilan; kontrol sebenarnya 403 di backend).
13. **`useSyncExternalStore` wajib punya `getServerSnapshot`** untuk render server; ditemukan karena test render Shell gagal. Diperbaiki di `useWorkbench`.
14. **Uji kontrak dengan sampel dari skema backend sungguhan.** `src/testing/backend-mock-samples.json` dan `backend-rejected-samples.json` dihasilkan dari kode backend (adapter mock + `assess` + skema respons) di kontainer `api`; datanya fiktif. **Ini bukan uji end-to-end:** gateway cache/kuota, router, dan database dilewati, sehingga `expires_at` bernilai null dan `from_cache` false di sampel, sedangkan respons `POST /checks` nyata mengisinya dari gateway. Cakupan cache/kedaluwarsa hanya diuji dengan fixture tulis tangan. Hasilnya cocok dengan tabel IP demo TASK-02 (label, cakupan, flag) dan menggantikan angka tebakan fixture tulis tangan (mis. skor 1.1.1.1 yang sebenarnya `85.5`, bukan `77`). Skrip pembuatnya `src/testing/gen_backend_samples.py` (terbukti menghasilkan keluaran identik). Pembuatan ulang (fish):
    ```fish
    docker compose exec -T api python - mock < frontend/src/testing/gen_backend_samples.py > frontend/src/testing/backend-mock-samples.json
    docker compose exec -T api python - rejected < frontend/src/testing/gen_backend_samples.py > frontend/src/testing/backend-rejected-samples.json
    ```
15. **Pelajaran dari Tahap 1 diterapkan:** baseline dijalankan sebelum uji mutasi, dan uji mutasi massal (14 perusakan: skor null jadi nol, label null jadi RENDAH, penjaga cache, `+00:00` berlabel WIB, simulasi dimatikan, penjaga IPv4 pivot, penyebut 0, XSS lewat HTML mentah, Cek ulang untuk viewer, teks larangan MISP, "Muat lagi" tanpa batas, dedup riwayat, klik ganda submit, respons detail basi) semuanya **tertangkap**. Satu percobaan awal gagal dijalankan karena pola pencarian saya salah, bukan karena test lemah, lalu diulang dengan pola benar dan tertangkap. Enam mutasi tambahan untuk keputusan 16-19 (aria-controls di semua tab, tooltip untuk `+00:00`, label waktu dikarang, kolom pencarian `disabled`, offset 56px kembali, viewer mendapat pencarian) juga semuanya tertangkap.

16. **Tinggi top bar diukur, bukan angka keras.** Setelah kolom pencarian masuk top bar, header satu baris sekitar 82px (perkiraan dari kelas Tailwind), sedangkan rel kiri/kanan menempel di 56px; sekitar 26px bagian atas rel akan tertutup saat halaman digulir (lebih bila header membungkus atau ada pesan galat). Diperbaiki: pembungkus sticky di `Shell` + `ResizeObserver` (`useTopBarHeight`) menulis `--topbar-h`, dipakai rel lewat `lg:top-[var(--topbar-h,5rem)]` dan `lg:max-h-[calc(100vh-var(--topbar-h,5rem))]`. Uji gulir di Chromium sungguhan (lihat "Hasil pengujian Tahap 2") menemukan kekurangan kedua: rel yang tingginya `100vh` dikurangi top bar saja terdorong footer di dasar halaman, sehingga judulnya menyelip di bawah top bar. Diperbaiki dengan mengukur tinggi footer juga (`--footer-h`, hook `useCssVarHeight`) dan mengurangkannya dari `max-h` rel.
17. **Tooltip ISO (Keputusan 20)**: komponen `TimeText` membungkus waktu yang benar-benar dikonversi dalam `<time dateTime title=ISO>`; string `+00:00` atau asing tampil mentah tanpa `<time>` dan tanpa label WIB.
18. **Label waktu sumber menurut `source_time_type` (Aturan tampilan 3)**: "Laporan terakhir" / "Analisis terakhir"; jenis null berlabel netral "Waktu dari sumber", tidak dikarang. Sebelumnya label dikeraskan di tab dan `sourceTimeLabel` yang sudah teruji tidak terpakai.
19. **ARIA tab**: `aria-controls` hanya pada tab terpilih (hanya panel aktif yang dirender); sebelumnya tiga tab menunjuk id yang tidak ada. Kolom pencarian memakai `readOnly` (bukan `disabled`) saat memeriksa agar fokus keyboard tidak jatuh ke `<body>`. Tombol Cek ulang tetap `disabled` saat memeriksa (fokus pada tombol itu hilang; dicatat sebagai gap).
20. **Bug paginasi nyata, ditemukan hanya dengan backend sungguhan.** Bila orang lain membuat pengecekan di tengah paginasi, offset bergeser: halaman berikutnya memuat ulang satu baris yang sama (dibuang dedup), dan baris terbaru itu sendiri tidak pernah termuat. Akibatnya riwayat berhenti 1 baris di bawah total (42 dari 43), "Muat lagi" tidak pernah hilang, dan klik berikutnya tidak berefek. Test unit sebelumnya hanya menguji dedup, bukan keadaan macet ini. Diperbaiki di `workbench/store.ts`: bila halaman berikutnya tumpang-tindih, halaman terdepan diambil ulang untuk memunculkan baris baru di atas (`refreshHead`, galatnya diabaikan diam-diam); bila tetap tidak ada kemajuan, tombol ditutup. Dijaga 4 test dengan server palsu yang bisa bertambah di tengah paginasi.
21. **Baris riwayat tanpa badge SIMULASI itu benar**, bukan cacat: database dev berisi 3 baris bukan-mock, yaitu check live nyata `id=3` (118.25.6.39, 31 Okt, VirusTotal dari cache) dan dua check lama TASK-01 (`id=1`, `id=2`, `SKIPPED/ADAPTER_NOT_IMPLEMENTED`). Ketiganya tampil benar di UI nyata: tanpa bingkai simulasi, `RENDAH` abu-slate, label waktu "Analisis terakhir 30 Okt 2026 15:01:36 WIB", "Cache, berlaku sampai…" untuk sumber ber-cache, "Ambil baru" untuk yang lain, dan check lama tanpa label cache palsu serta field kosong "tidak tersedia".
22. **Cara pengujian peramban (pengecualian sekali pakai atas Keputusan 13h, disetujui developer 3 Nov).** Brave 156 headless (Chromium) yang sudah terpasang dikendalikan skrip sementara di `/tmp` lewat Chrome DevTools Protocol memakai WebSocket bawaan Node, tanpa dependency baru dan tanpa menyentuh repo. Login memakai akun analyst sementara `agen_uji` (password acak di file berizin 600, tidak pernah dicetak). Skrip dan profil dibuang setelah selesai; hanya screenshot yang disisakan di luar repo (`/tmp/uji/shots`). Backend dipastikan `SOURCES_MODE=mock` dan `MISP_MODE=mock` sebelum membuat pengecekan, sehingga tidak ada kuota yang terpakai.

### Bukti uji otomatis

- 267 test Vitest di 15 file. Termasuk: pemformat (skor, label, waktu `+07:00`/`+00:00`, status/reason/flag, bukti, rasio vendor, salin hasil, pivot), riwayat (merge/prepend/filter), penjaga bentuk, store (submit, INPUT_DITOLAK, klik ganda, detail basi, submit vs detail, aborted, 401, `loadMore`), render komponen untuk tujuh IP demo dan check lama TASK-01, RBAC tampilan (viewer tanpa pencarian dan Cek ulang), kasus XSS, dan uji kontrak dengan keluaran asli backend.
- Smoke dev server (`npm run dev`, localhost): 16 modul baru ter-compile (HTTP 200), log bebas error, proxy dan 401 tanpa token terbaca; dihentikan setelahnya.

### Hasil pengujian Tahap 2 (3 Nov 2026)

Langkah 1-4: dijalankan developer (lulus). Langkah 5-8 dan 10-12: dijalankan agen di Brave headless terhadap backend sungguhan (mock), 51 pemeriksaan otomatis terakhir **lulus semua** setelah perbaikan keputusan 16 dan 20. Langkah 5-7 juga diuji lewat API (9 dari 9 lulus).

| Langkah | Hasil terukur |
|---|---|
| 2. tujuh IP demo | Skor, label, cakupan, status, badge SIMULASI, dan blok putus-putus untuk N/A cocok dengan tabel TASK-02; `149.112.112.112` bergaris `rgb(42, 54, 68)` hue 212° (bukan hijau); HASIL_BERBEDA tampil di Ringkasan; WHITELISTED dan NO_VENDOR_OPINION tampil di rel keputusan. Badge SIMULASI di riwayat cocok dengan flag dari API (59 dari 62; sisanya 3 baris bukan-mock, keputusan 21). |
| 3. input ditolak | `10.10.50.10` PRIVATE, `127.0.0.1` LOOPBACK, `2001:db8::1` IPV6_NOT_SUPPORTED, `abc` INVALID_FORMAT: pesan backend + kode tampil; panel tengah dan riwayat tidak berubah; isian dipertahankan. |
| 5. Cek ulang | Tepat 1 POST baru; dua baris IP yang sama di paling atas (API: id berbeda, total +2). |
| 6. klik riwayat | 0 POST baru, jumlah baris tetap, tepat satu baris `aria-current`; API: GET detail tidak mengubah total, id tidak ada -> 404. |
| 7. Muat lagi | 20 baris awal dari total 43-54; setelah semua termuat jumlah baris = total (tanpa baris ganda) dan tombol hilang, termasuk saat orang lain menambah pengecekan di tengah (keputusan 20). |
| 8. salin hasil | `localhost` aman: "Tersalin", isi clipboard sungguhan memuat IP, skor, dan kalimat bukan probabilitas, tanpa `%`. Konteks tidak aman disimulasikan dengan mengganti `isSecureContext` menjadi false (bukan lewat `dev:lan` nyata): `<textarea>` readonly terfokus, seluruh teks terpilih, petunjuk menyebut Ctrl+C. |
| 9. tautan pivot | Atribut benar: `target="_blank"`, `rel="noopener noreferrer"`, href `https://www.abuseipdb.com/check/<ip>` dan `https://www.virustotal.com/gui/ip-address/<ip>`. **Kebenaran URL tidak bisa dibuktikan oleh agen**: AbuseIPDB mengenali peramban otomatis dan menampilkan "Please Don't Scrape AbuseIPDB" (juga 403 Cloudflare lewat `curl`), VirusTotal 200 untuk path apa pun (situs satu halaman) dan gagal dimuat di headless. **Dibuktikan developer** dengan mengklik keduanya di peramban biasa: tab baru terbuka dengan halaman IP yang dituju dan datanya jelas (dilaporkan developer). |
| 10. keyboard tab | ArrowRight/Left berputar, End/Home ke ujung, fokus selalu pada tab terpilih, tepat satu tab ber-`tabindex=0`, outline fokus `2px solid` Aksen, Tab dari tab berpindah ke panel. |
| 11. layar | Screenshot 1280×720, 1024×768, 800×390 (dan login, tujuh IP, tab, data live, data lama, salin cadangan) di `/tmp/uji/shots` (di luar repo). Pada 800×390 urutan tumpukan terukur bukti > keputusan > riwayat. |
| 12. gulir | Pada 1280×720 dan 1024×768, di posisi atas/tengah/dasar, rel kiri dan kanan selalu berada di antara bawah top bar dan awal footer; `--topbar-h` dan `--footer-h` sama dengan tinggi nyata; saat pesan galat membuat top bar naik (83→114px dan 133→143px), variabel mengikuti dan rel tidak tertutup. |

Data uji dibersihkan: 76 baris `ip_checks` milik `agen_uji` dan 48 baris `source_cache` untuk IP `20.20.20.*` dihapus (sisa tepat 17 baris developer: admin 15, analyst 2); tidak ada submission MISP yang terkait; akun `agen_uji` dinonaktifkan (login 401). 112 baris `audit_logs` oleh `agen_uji` **tetap ada** (catatan permanen). Cache mock untuk IP demo bersama (mis. 1.1.1.1) tidak dihapus karena tidak bisa dipisahkan dari milik developer; isinya data mock yang sama.

### "Cek selesai" Tahap 2 — daftar langkah (1-8 dan 10-12 sudah lulus; tersisa 9)

Agen tidak punya password akun seed dan tidak ada peramban, jadi bagian ini belum diuji di peramban:

1. `docker compose up -d`, lalu `cd frontend; npm run dev` (mode `SOURCES_MODE=mock`, bawaan). Login sebagai admin atau analyst.
2. **Tujuh IP demo**, satu per satu, screenshot masing-masing: `1.1.1.1` (SANGAT_TINGGI), `1.0.0.1` (HASIL_BERBEDA), `8.8.8.8` (N/A, DATA_TERBATAS 1/2, ERROR TIMEOUT), `8.8.4.4` (N/A, TIDAK_TERSEDIA 0/2), `9.9.9.9` (WHITELISTED, skor tetap), `149.112.112.112` (0.0 + NO_VENDOR_OPINION, **tidak hijau**), `208.67.222.222` (N/A, INSUFFICIENT_DATA). Semua harus berbadge SIMULASI di strip dan di baris riwayat.
3. **Input ditolak:** `10.10.50.10`, `127.0.0.1`, `2001:db8::1`, `abc` → pesan backend + kode reason di bawah kolom pencarian; panel tengah dan riwayat tidak berubah.
4. **Viewer:** login sebagai viewer → tidak ada kolom pencarian dan tombol Cek ulang; riwayat dan detail tetap terbaca; "Salin hasil" tetap ada.
5. **Cek ulang** atas IP yang sama membuat baris baru di riwayat paling atas.
6. **Klik riwayat** menampilkan detail tanpa membuat pengecekan baru (riwayat tidak bertambah).
7. **"Muat lagi":** buat lebih dari 20 pengecekan (mock tidak memakai kuota), pastikan tombol memuat halaman berikutnya tanpa baris ganda dan hilang saat semuanya dimuat.
8. **Salin hasil lewat `dev:lan`** (`npm run dev:lan`, buka `http://<IP-laptop>:5173` dari perangkat lain): tombol harus menampilkan teks terpilih di `<textarea>`; di `localhost` harus langsung "Tersalin".
9. **Tautan pivot:** klik "AbuseIPDB" dan "VirusTotal" di rel kanan; laporkan bila ada yang 404. **Sudah dijalankan developer: lulus.**
10. **Keyboard:** Tab ke daftar tab bukti, panah kiri/kanan dan Home/End berpindah tab; fokus terlihat.
11. **Screenshot** 1280×720, 1024×768, dan < 1024px dari workbench berisi satu hasil, untuk kritik desain (Keputusan 13h).
12. **Gulir**: pada 1280×720 dengan riwayat panjang dan hasil berisi tab terbuka, gulir halaman ke bawah. Judul "Riwayat" dan "Keputusan" harus tetap terlihat di bawah top bar (tidak tertutup), juga saat muncul pesan galat di kolom pencarian atau top bar membungkus ke dua baris (lebar sempit).

## Known gaps baru (Tahap 2)

1. ~~Langkah 9 (klik tautan pivot) belum dilakukan~~ **sudah dijalankan developer: lulus.** Seluruh langkah 1-12 lulus.
2. **Format URL pivot tidak bersumber dari dokumentasi resmi** (keputusan 4), meski klik developer membuktikan keduanya berfungsi hari ini. Rawan berubah tanpa pemberitahuan.
3. **Tidak ada uji peramban otomatis** (Playwright dilarang, Keputusan 13h): handler klik/submit, fokus, dan penyalinan nyata hanya tercakup lewat store, render markup, dan uji kontrak.
4. **"Muat lagi" dan penyaring bekerja pada yang sudah dimuat**; tidak ada pencarian penuh karena backend tanpa parameter filter (gap 2 rencana).
5. **Riwayat mock dan live bercampur** (gap 19 TASK-02); dibedakan hanya oleh tag SIMULASI.
6. **Detail dari baris riwayat ditampilkan dulu lalu disegarkan** lewat `GET /checks/{id}`; bila GET gagal, data baris tetap tampil bersama pesan galat.
7. **Bar 0-100 `abuseConfidenceScore` tidak dibuat** (keputusan 3).
8. **Panel samping tidak setinggi area utama di desktop** (polish Tahap 4; sama dengan gap 7 Tahap 1).
9. **Berkas kontrak backend adalah potret**: bila adapter mock atau skema berubah, buat ulang dengan skrip (keputusan 14); uji kontrak yang akan gagal lebih dulu.
10. ~~Perilaku guliran rel belum diuji di peramban~~ **sudah diuji di Chromium** (langkah 12); tinggal diuji di Firefox dan layar sungguhan.
11. **Tombol "Cek ulang" nonaktif saat memeriksa**, sehingga fokus keyboard pada tombol itu hilang setelah pengecekan selesai (kolom pencarian sudah ditangani dengan `readOnly`).
12. **Sampel kontrak tidak mencakup gateway cache/kuota** (keputusan 14): bentuk `from_cache: true` dan `expires_at` berisi hanya diuji lewat fixture tulis tangan.
13. **Top bar membungkus di layar sempit.** Pada 1024px menjadi dua baris (133px, sekitar 17% tinggi layar) dan pada 800×390 memakan sekitar 34% tinggi layar dan tetap `sticky`. Usul Tahap 4: `sticky` hanya di ≥ 1024px dan/atau meringkas badge.
14. **Chip label patah di tengah kata** di rel riwayat pada 1024px ("PERLU_PEMERIKSAA / N") karena lebar rel 232px; tag SIMULASI juga membungkus dua baris. Usul Tahap 4: titik patah setelah garis bawah (`<wbr>`) atau chip lebih kecil di rel.
15. **Tata letak bergeser saat pesan galat pencarian muncul/hilang** (top bar 83→114px pada 1280, 133→143px pada 1024). Usul Tahap 4: sediakan ruang tetap untuk pesan atau tampilkan sebagai lapisan di bawah kolom.
16. **Uji peramban hanya di Chromium (Brave 156 headless)**: Firefox dan Safari belum; font sistem headless belum tentu sama dengan perangkat tim; konteks tidak aman pada langkah 8 disimulasikan, bukan lewat `dev:lan` sungguhan.
17. **112 baris `audit_logs` oleh `agen_uji` dan akun nonaktif `agen_uji` tetap ada** di database dev (audit bersifat permanen; akun tidak dihapus). Hapus akunnya bila tidak diinginkan.

## Tahap 3 — Pelaksanaan

Dikerjakan di branch `feat/task-03-tahap-3-kirim-misp-kiriman`. Tidak ada perubahan backend (hanya skrip sampel kontrak di `frontend/src/testing`). Mengikuti "Keputusan desain" yang disetujui; tidak ada komponen visual baru di luar sistem yang ada (chip netral, chip kegagalan, tombol, kolom isian).

**Yang dibangun** (`frontend/src`):
- `api/iocs.ts` (`listIocs`, `submitIoc`), `api/guards.ts` (`isIocOut`, `isIocPage` ketat; status di luar empat nilai backend ditolak).
- `lib/misp.ts` (fungsi murni): `iocStatusView`, `findSubmissionForCheck`, `findSameIpElsewhere`, `confirmText`, `countChars`, `parseTags`, `validateSubmission`, `applyHead`/`appendPage`/`upsertSubmission`. `lib/can.ts`: `mispDeniedText`.
- `workbench/mispStore.ts` + `useMisp.ts`: daftar kiriman (100 terbaru), kirim, 409, kegagalan 501/502, paginasi.
- Komponen: `MispPanel` (status kiriman + form + konfirmasi inline), `MispView` (tabel Kiriman MISP), `ExpandableText`, `IocStatusChip` di `Badges`; `DecisionRail` menerima slot `misp`; `Shell` memuat store, menyegarkan daftar saat masuk tampilan Kiriman MISP, dan membuka check dari tabel.
- Sampel kontrak `backend-ioc-samples.json` dari `MockMispClient`, `LiveMispClient`, `_failure_message`, dan skema `IocOut`/`IocPage` backend (mode `ioc` di `gen_backend_samples.py`).

### Keputusan dan penyimpangan dari rencana

1. **Satu store khusus MISP** (`createMispStore`), terpisah dari store riwayat, dibuat di `Shell` sehingga bertahan saat berpindah tampilan. Daftar yang sama dipakai untuk status di rel keputusan dan tabel Kiriman MISP. Dimuat `limit=100` di awal, disegarkan setelah setiap kirim, setelah 409, dan saat masuk tampilan Kiriman MISP.
2. **Status "mengirim" per check** (`sendingIds`), bukan satu bendera global: berpindah check saat kirim berjalan tidak membuat check lain tampak "Mengirim…", dan jawaban yang datang belakangan tetap masuk ke check yang benar. Penjaga klik ganda ada di store, bukan hanya di tombol (backend tetap mencegah duplikat per `check_id`).
3. **Bila `GET /iocs` gagal dimuat, form TIDAK ditampilkan** (pesan merah + "Coba lagi"). Alasan: tanpa daftar kiriman, konfirmasi "IP ini sudah pernah dikirim" terlewat diam-diam. Tidak tertulis di rencana; diputuskan agen.
4. **Kiriman `failed` pada check lain tidak memicu konfirmasi; `pending` memicu.** Alasan: kiriman gagal tidak pernah sampai ke MISP, jadi kalimat "sudah pernah dikirim" akan salah. `pending` dihitung karena bisa saja sedang terkirim. Bila ada beberapa, yang terbaru dipakai. Ini tafsiran atas Keputusan 14, bukan perubahan teksnya. Teks konfirmasi memakai kode status backend persis seperti rencana, mis. `(mock_sent)`.
5. **Validasi form mengikuti perilaku backend**: alasan dipangkas dulu lalu dihitung per code point (`Array.from`), bukan `String.length` (lima emoji = 5 karakter di Pydantic, 10 di JS); entri tag kosong ("a,,b", koma di ujung) dibuang agar tidak ditolak `min_length=1`; batas 10-2000 untuk alasan, 20 tag, 64 karakter per tag. Pesan inline muncul setelah klik pertama, tombol tetap aktif, fokus pindah ke kolom bermasalah.
6. **409 bukan galat**: daftar dimuat ulang dan kiriman yang ada ditampilkan. Bila kiriman itu tidak ada di 100 terbaru, muncul keterangan netral (bukan merah) berisi `detail` backend dan nomor kiriman.
7. **Kirim ulang dari `failed` mengirim isian form saat ini** (backend menimpa `reason` dan `tags` pada baris yang sama). Form terisi dari kiriman gagal itu; setelah 501/502 isian yang diketik tetap ada (komponen tidak di-mount ulang). Tombol berlabel "Kirim ulang".
8. **Konfirmasi inline**: saat panel muncul kolom isian dikunci (`readOnly`) dan fokus dipindahkan ke panel; "Batal" mengembalikan fokus ke tombol kirim. Tombol di panel selebar rel agar tidak patah di rel 232px.
9. **Semua peran melihat status kiriman** sebuah check (termasuk viewer, read-only); form hanya untuk yang berhak (`mispDeniedText`: analyst tanpa izin = "Kirim ke MISP butuh izin dari admin."; viewer = "Akun ini hanya dapat melihat; tidak dapat mengirim ke MISP."). `failed` tampil juga untuk viewer tetapi tanpa form kirim ulang.
10. **Butir [NANTI] "klik baris buka check di Workbench" dikerjakan** (tombol teks "Buka check #N" di kolom IP): kecil dan memakai `store.select`.
11. **Tabel**: tujuh kolom (Waktu, IP, Status, Event UUID, Pengirim, Alasan, Keterangan), `min-w-[56rem]` dalam area gulir horizontal yang bisa difokus (kolom utama hanya sekitar 530px pada 1024px). Alasan dipotong 120 karakter dengan tombol teks "Tampilkan semua"; tag sebagai chip teks; `pending` menampilkan "Bila tertahan lama, hubungi admin."; tombol "Segarkan".
12. **`isIocOut` ketat dipindah ke `api/guards.ts`** dan dipakai juga oleh `parseIocError`. Akibat: 501/502 dengan badan yang tidak lengkap kini diurai sebagai galat server, bukan "kiriman gagal" (sebelumnya penjaga longgar hanya memeriksa empat field).
13. **Total daftar tidak pernah turun karena penyegaran** (`max` dengan nilai sebelumnya), supaya jawaban lama tidak menyusutkan "n dari total".
14. **`Button` menerima `ref`** (`ComponentPropsWithRef<'button'>`, React 19) untuk pemulihan fokus.
15. **Status kiriman dan chip**: `mock_sent` = chip netral "Terkirim (mock)"; `sent` = chip netral dengan centang "Terkirim ke MISP"; `pending` = chip netral "Sedang diproses (pending)"; `failed` = `FailureChip` (bingkai merah + ✕ + "Gagal") dengan `error_message`. Tanpa hijau dan tanpa kuning.

### Bukti uji otomatis

| Lapisan | Isi | Hasil |
|---|---|---|
| `lib/misp.test.ts` (26) | pemetaan status, pencocokan per `check_id`/per IP (check yang sama tidak memicu, `failed` dilewati, `pending` dihitung), teks konfirmasi tanpa "duplikat", hitung code point, tag kosong, batas alasan/tag, merge daftar | lulus |
| `workbench/mispStore.test.ts` (29) | muat awal, 201/200, klik ganda, status per check, 409 (ada/tidak di daftar), 501/502, 422 (dua bentuk, tanpa menyalin `input`), 403, 404, jaringan, 401, 2xx salah bentuk, paginasi + overlap | lulus |
| `components/misp.render.test.tsx` (34) | slot MISP vs larangan simulasi, memuat/gagal memuat, form, teks izin, konfirmasi inline, galat inline, `mock_sent`/`sent`/`pending`/`failed`, escape HTML, tabel | lulus |
| `api/guards.test.ts` | `isIocOut`/`isIocPage` | lulus |
| `testing/contract.test.tsx` | sampel IoC dari kode backend sungguhan: penjaga, 501/502/409, tampilan, tabel, store | lulus |

**Uji mutasi** (baseline hijau lebih dulu; 41 mutasi dengan pemulihan otomatis): **40 tewas, 1 selamat**. Yang selamat: kabel `deniedText={mispDeniedText(user)}` di `Shell` (komponen berstatus tidak bisa dirender statis di lingkungan Node tanpa jsdom; Keputusan 6). Ditutup oleh langkah manual (d) dan (e) di bawah.

### "Cek selesai" Tahap 3 — langkah untuk developer

Keadaan DB dev (dibaca agen, hanya-baca): ada tiga check non-simulasi (id 1 `8.8.8.8` dan id 2 `1.1.1.1`, keduanya `TIDAK_TERSEDIA` buatan TASK-01/02 tanpa flag simulasi; id 3 `118.25.6.39` `COMPLETE`) dan **satu kiriman**: check #3 sudah `mock_sent` (oleh `admin`, 31 Okt). Backend hanya menolak check `INPUT_DITOLAK` atau `SUMBER_SIMULASI`, jadi check #1 dan #2 **bisa dikirim** dan belum punya kiriman. Check #3 tidak bisa dipakai untuk "kirim pertama kali"; ia cocok untuk uji "status sudah ada" dan sebagai dasar uji konfirmasi IP yang sama.

**Catatan kompromi:** mengirim check #1 atau #2 menghabiskannya selamanya (`UNIQUE(check_id)`), dan keduanya check tanpa data sumber (`TIDAK_TERSEDIA`). Itu pilihan murah untuk DB dev; bila ingin data yang bermakna, pakai check live baru (langkah b).

Agen **belum** menjalankan apa pun di peramban untuk Tahap 3 (butuh akun sementara, peramban, dan, untuk (a)/(b), mode live yang memakai kuota). Langkah:

a. **Kirim pertama kali (tanpa kuota, mode mock cukup).** Login analyst ber-`can_send_misp`, pilih check #1 atau #2 dari riwayat (keduanya tidak berbadge SIMULASI). Form MISP muncul; isi alasan ≥ 10 karakter, tag `tlp:amber, ioc`, kirim → "Terkirim (mock)" + `MOCK-…` + waktu + pengirim. Klik tombol dua kali cepat: hanya satu baris di tampilan Kiriman MISP.
b. **Konfirmasi IP yang sama (butuh `SOURCES_MODE=live`, memakai kuota satu pasang bila cache sudah kedaluwarsa).** Setel `SOURCES_MODE=live` (README "Mengaktifkan mode live"), buat ulang kontainer `api`, lalu "Cek ulang" atas `118.25.6.39` → check baru (live) → "Kirim ke MISP" → panel inline "IP ini sudah pernah dikirim lewat check #3 (mock_sent). Kirim lagi sebagai catatan baru?" muncul **sebelum** terkirim. "Batal" mengembalikan form; "Kirim lagi sebagai catatan baru" menambah satu baris di Kiriman MISP. Kembalikan ke `mock` sesudahnya. (Di mode mock "Cek ulang" membuat check bersimulasi tanpa tombol kirim, jadi konfirmasi tidak bisa dicapai.)
c. **Check simulasi** (mode mock, mis. `1.1.1.1`): tidak ada form, tampil "Hasil simulasi tidak boleh dikirim ke MISP." Paksa lewat Swagger `POST /iocs/misp` dengan `check_id` itu → 422.
d. **Alasan 5 karakter**: pesan "Alasan minimal 10 karakter (sekarang 5)." di bawah kolom, fokus pindah ke kolom, tidak terkirim (tab Network tidak memuat `POST /iocs/misp`). **Viewer**: tidak ada form; check #3 menampilkan "Terkirim (mock)" (read-only). **Analyst tanpa izin**: teks "butuh izin dari admin", tanpa form.
e. **Tampilan Kiriman MISP** (semua peran): tabel menampilkan kiriman #1 (check #3) dengan IP monospace, `MOCK-…`, pengirim, alasan; "Buka check #3" membuka check itu di Workbench. Pada 1024px tabel bisa digulir horizontal.
f. **Keyboard**: pada konfirmasi inline, fokus pindah ke panel lalu Tab ke "Kirim lagi sebagai catatan baru" dan "Batal"; setelah "Batal" fokus kembali ke tombol kirim.
g. **Jalur gagal dan kirim ulang tanpa duplikat (tanpa kuota).** Pakai check #1 atau #2 yang belum dikirim (yang tidak dipakai di langkah a). Setel `MISP_MODE=live` di `.env` dan buat ulang kontainer `api` (lencana top bar menjadi "MISP: live"). Kirim → backend menjawab 501: chip berbingkai merah ✕ "Gagal" + `error_message`, tombol berubah "Kirim ulang", isian form **tetap ada**. Ubah isian lalu kirim lagi → tetap gagal, isian tetap. Kembalikan `MISP_MODE=mock`, buat ulang kontainer, tekan "Kirim ulang" → 200, "Terkirim (mock)" pada **baris yang sama**; tampilan Kiriman MISP hanya punya satu baris untuk check itu. Ini bukti aturan CLAUDE.md "retry tidak menggandakan data" secara end-to-end.
h. **Yang hanya teruji otomatis**: `pending` (kiriman tertahan; tidak bisa dibuat lewat UI) dan 502 dari MISP asli.

### Hasil uji manual developer (4 Nov 2026, Chromium, mode mock, login `analyst_misp`)

Dilaporkan developer dengan dua screenshot; belum semua langkah dijalankan.

| Langkah | Hasil |
|---|---|
| (a) kirim pertama kali | **Lulus**: check #1 (`8.8.8.8`) dan #2 (`1.1.1.1`) terkirim → "Terkirim (mock)" + `MOCK-…` + pengirim + waktu WIB + alasan + tag di rel kanan. Check #3 (sudah `mock_sent` dari 31 Okt) menampilkan status tanpa form |
| (d) alasan < 10 karakter | **Lulus** (dilaporkan: pembatasan 10 karakter bekerja). Pesan persis, perpindahan fokus, dan "tidak ada POST di tab Network" belum dirinci |
| (e) tampilan Kiriman MISP | **Lulus sebagian**: tabel memuat tiga kiriman (IP mono, `MOCK-…`, pengirim, alasan, tag, "Buka check #N"). Gulir horizontal di 1024px, tombol "Buka check", dan "Segarkan" belum dilaporkan |
| (b) konfirmasi IP yang sama (live) | Diuji agen dengan `SOURCES_MODE=live` sungguhan: **lulus** (lihat di bawah) |
| (c) check simulasi + 422 Swagger | **Lulus** (dilaporkan: 422 sesuai yang diminta) |
| (d) viewer dan analyst tanpa izin | **Lulus** (dilaporkan: tidak ada form MISP untuk keduanya) |
| (f) fokus keyboard konfirmasi | Diuji agen di peramban (lihat di bawah): **lulus** |
| (g) 501 `failed` + kirim ulang tanpa duplikat | Dilaporkan developer: "tidak ada yang terkirim, gagal". Diuji ulang agen dengan `MISP_MODE=live` sungguhan: **lulus** (lihat di bawah) |
| klik ganda cepat pada tombol kirim | Diuji agen di peramban: **lulus** |

### Uji peramban oleh agen (4 Nov 2026, Brave 156 headless, `http://localhost:5173`, backend sungguhan, mode mock)

Izin developer: Brave headless sekali pakai dengan akun analyst sementara (`agen_uji`, `can_send_misp` dinyalakan sementara) dan penulisan lalu penghapusan data uji. Karena check mock selalu bersimulasi, agen menyisipkan **empat baris `ip_checks` sintetis non-simulasi** (IP `20.20.20.201` dua kali, `.202`, `.203`, hasil sumber disalin dari check #3) langsung ke DB; semuanya dihapus sesudahnya. `fetch` di halaman dibungkus untuk menghitung `POST /iocs/misp` (hanya metode dan URL, tanpa header). Hasil:

| Skenario | Hasil |
|---|---|
| Klik ganda nyata (dua pasang `mousePressed`/`mouseReleased` beruntun tanpa jeda, `clickCount` 1 dan 2) | tepat **1** POST; rail "Terkirim (mock)" |
| `requestSubmit()` dua kali dalam satu tick (melewati tombol nonaktif, hanya penjaga di store) | tepat **1** POST |
| IP yang sama dikirim lewat check lain | panel inline "IP ini sudah pernah dikirim lewat check #99 (mock_sent). Kirim lagi sebagai catatan baru?" muncul, **belum ada POST**, tanpa kata "duplikat" |
| Fokus keyboard | fokus pindah ke panel; Tab → "Kirim lagi sebagai catatan baru" → "Batal"; Enter pada "Batal": fokus kembali ke "Kirim ke MISP", panel hilang, isian alasan tetap, tanpa POST; kolom alasan terkunci saat konfirmasi |
| Konfirmasi lalu "Kirim lagi sebagai catatan baru" | tepat 1 POST tambahan, check menjadi "Terkirim (mock)" |
| Tabel Kiriman MISP | memuat kiriman dari semua check uji (dua baris untuk IP yang sama) |

Skenario belum tercakup: tombol "Buka check #N" dan "Segarkan" (dilihat tampil, tidak diklik), 501 `failed` (butuh `MISP_MODE=live`), gulir halaman dengan banyak kiriman, Firefox/Safari. Satu kegagalan awal adalah kesalahan skrip uji (pemilih `form` pertama ternyata form pencarian; Enter lewat CDP tanpa `text` tidak memicu klik), bukan galat aplikasi.

Pembersihan: 4 kiriman dan 4 check uji dihapus (sisa satu kiriman: #1 milik check #3, `admin`); akun `agen_uji` dinonaktifkan dan `can_send_misp` dikembalikan `false`. Catatan `audit_logs` oleh `agen_uji` tetap ada (permanen). Peramban uji dan berkas sementara (password acak, profil) dihapus.

### Uji mode live oleh agen (4 Nov 2026, Brave headless, backend sungguhan)

Izin developer: kuota boleh terpakai. Satu IP publik (`9.9.9.9`), jadi **satu panggilan VirusTotal dan satu AbuseIPDB** (keduanya HTTP 200 menurut `source_calls`); "Cek ulang" berikutnya memakai cache (badge "Cache" di rel, tanpa panggilan baru). `.env` diubah hanya pada dua baris `SOURCES_MODE` dan `MISP_MODE` (isi `.env` lain tidak dibaca) dan **dikembalikan ke `mock`** di akhir; kontainer `api` dibuat ulang dan `/health` menjawab `misp_mode: mock`. Akun sementara `agen_uji` seperti sebelumnya.

| Fase | Hasil |
|---|---|
| `SOURCES_MODE=live`, `MISP_MODE=live`: cek `9.9.9.9` lewat kolom pencarian | COMPLETE 2/2, skor 1.8, RENDAH, **tanpa badge SIMULASI**; lencana top bar "MISP: live"; form MISP tersedia |
| Kirim | backend 501: tepat 1 POST; chip berbingkai merah ✕ "Gagal" + `MISP_MODE=live belum diimplementasikan; gunakan MISP_MODE=mock`; tombol menjadi "Kirim ulang"; alasan dan tag **tetap terisi**; tidak ada kata "Terkirim" |
| Ubah alasan, "Kirim ulang" (masih live) | POST ke-2, tetap Gagal, isian hasil ubahan tetap; tampilan Kiriman MISP: 1 baris berstatus Gagal + pesan |
| `MISP_MODE=mock`, muat ulang halaman, login ulang, pilih check itu | status Gagal tampil dari server; form terisi alasan terakhir (yang diubah) dan tag dari server |
| "Kirim ulang" | 1 POST; **baris yang sama** menjadi "Terkirim (mock)" + `MOCK-…`; Kiriman MISP tetap **1 baris** (tidak digandakan) |
| "Cek ulang" `9.9.9.9` | check baru dari cache (live, bukan simulasi, badge Cache), form MISP baru |
| "Kirim ke MISP" | konfirmasi inline "IP ini sudah pernah dikirim lewat check #102 (mock_sent). Kirim lagi sebagai catatan baru?", **belum ada POST** sebelum dikonfirmasi |
| "Kirim lagi sebagai catatan baru" | 1 POST, "Terkirim (mock)"; Kiriman MISP: 2 baris untuk `9.9.9.9` |

Pembersihan: 2 kiriman dan 2 check uji dihapus (sisa kiriman: #1 milik check #3); `agen_uji` dinonaktifkan (`can_send_misp` kembali `false`); peramban, password acak, dan profil dihapus. Catatan `audit_logs` dan baris `source_cache`/`source_calls` untuk `9.9.9.9` tetap ada (permanen / data live sah). Satu kesalahan prosedur: satu perintah gabungan terhenti di tengah (pola `pgrep` mengenai shell sendiri), tanpa efek pada `.env`, DB, atau peramban; langkah diulang satu per satu.

## Known gaps baru (Tahap 3)

1. **Draf form hilang saat berpindah check** (state form per check, tidak disimpan; tambahan atas gap 14 rencana yang menyangkut sesi habis).
2. **Pencocokan status memakai kiriman yang sudah dimuat** (100 terbaru + halaman tambahan yang dimuat user). 409 untuk kiriman yang lebih tua ditangani dengan keterangan netral, tanpa detail kiriman (tidak ada `GET /iocs/{id}`).
3. **`pending` tertahan hanya teruji otomatis** (tidak bisa dibuat lewat UI); 502 dari MISP asli juga belum teruji karena klien live belum ada. Jalur 501 `failed` dan kirim ulang **sudah diuji lewat UI** dengan `MISP_MODE=live` (bagian di atas).
4. **Kabel izin di `Shell` tidak teruji otomatis** (satu mutan selamat): hanya tercakup uji manual (d). Penegakan sebenarnya tetap 403 backend (bukti KM-8 di Tahap 4).
5. **Tabel Kiriman MISP menampilkan semua baris yang dimuat tanpa penyaring** (backend tanpa filter); untuk tim 4 orang cukup.
6. **Konfirmasi IP yang sama mengandalkan string IP persis sama** (`check.ip === item.ip`); backend sudah menormalkan IPv4, jadi cukup.
7. **Fokus keyboard hilang setelah kirim**: tombol kirim `disabled={sending}` sehingga fokus jatuh ke `<body>` begitu pengiriman selesai (pola sama dengan gap 11 Tahap 2: "Cek ulang"). Form dikunci dengan `readOnly` saat konfirmasi, tetapi tombol kirim belum. Perbaikan nanti: `aria-disabled` atau pemulihan fokus eksplisit.
8. ~~Komponen MISP belum pernah dijalankan di peramban~~ **sudah diuji di Chromium** (bagian di atas): klik ganda, konfirmasi, fokus, isian form setelah 501, kirim ulang. Belum: Firefox/Safari.
9. **Chip status di tabel Kiriman MISP patah dua baris** ("Terkirim" / "(mock)") pada lebar layar developer, karena kolom Status sempit; kolom "Keterangan" kosong untuk baris sukses. Polish Tahap 4: `whitespace-nowrap` pada chip di tabel.
10. **Tabel Kiriman MISP perlu gulir horizontal di 1280px** (kolom utama sekitar 650px, tabel `min-w-[56rem]`): kolom Alasan dan Keterangan tersembunyi di sisi kanan sampai digulir, padahal Alasan penting untuk analis. Polish Tahap 4: kolom lebih ramping (UUID dipotong atau Waktu/IP digabung) atau tata letak kartu per baris.

### Keputusan agen yang meminta persetujuan developer

1. **Kiriman `failed` pada check lain tidak memicu konfirmasi** (keputusan 4). Pembacaan polos Keputusan 14 "(<status>)" mencakup `failed` sehingga analis melihat "(failed)". Mengembalikannya = satu baris di `findSameIpElsewhere` plus membalik satu uji.
2. **Form disembunyikan bila `GET /iocs` gagal** (keputusan 3), bukan ditampilkan dengan peringatan.

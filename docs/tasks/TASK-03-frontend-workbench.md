# TASK-03 — Frontend Workbench Investigasi IP

> Prompt ke Claude Code: **"/kerjakan-tahap TASK-03 0"** (atau: "Baca CLAUDE.md dan docs/tasks/TASK-03-frontend-workbench.md.
> Kerjakan Tahap 0 saja, jalankan Cek selesai, lalu berhenti dan laporkan.")
> Ulangi untuk Tahap 1, 2, dst. Satu tahap = satu PR kecil (`Refs #<issue>` di PR tahap, `Closes #<issue>` di PR Tahap 4).

Issue induk: **#28**. Branch: `feat/task-03-tahap-<n>-<ringkas>`.
Dasar aturan: **`riset-reputasi-ip-revisi-1.1.pdf`** hlm. 1 (tujuan v1), Bab 4 (label, N/A), §6 (alur & kontrak API),
§7 (MISP); **Output Web Fundamental 2** (wajib frontend React/Vue/Svelte); **Panduan Proyek SOC** KM-8 (RBAC + uji negatif);
`TASK-02-progress.md` gap 17, 18, 19, 24. Referensi visual sekunder: `Referensi_Design_Frontend_Tools_TI_-_Revisi_Workbench.md`
(tidak di-commit), **dengan 12 koreksi** di bagian "Koreksi atas dokumen referensi" di bawah.
Di luar lingkup: perubahan backend, Shodan/enrichment, force refresh, filter server-side, deploy ke soc-ir (nginx), CI/CD,
kelola user lewat UI (pakai Swagger), dashboard/metrik KM-7 (itu tugas SIEM, bukan tool TI).

## Jenis antarmuka: workbench, BUKAN dashboard

Tool ini meja kerja analis untuk **satu IP per investigasi**: input IP → baca bukti per sumber → putuskan → kirim ke MISP
(manual) atau salin hasil. Tidak ada halaman overview, kartu KPI, grafik tren, peta, atau feed. Setiap elemen di layar
harus menjawab salah satu: (1) IP apa? (2) apa bukti tiap sumber? (3) apa keputusan/aksi analis? Selain itu, buang.

## Keputusan yang dipakai task ini (dikonfirmasi developer, 2 Nov 2026)

1. **Stack:** Vite + React + TypeScript (template `react-ts`), **Tailwind CSS v4** lewat plugin `@tailwindcss/vite`.
   **Tanpa** fork template (shadcn-admin dll.) dan **tanpa** library UI/komponen; tab, tabel, badge dibuat sendiri dengan
   Tailwind. Alasan: dependency sedikit = attack surface & alert Dependabot kecil (repo public), waktu 2 hari.
2. **Dependency runtime hanya:** `react`, `react-dom`, `tailwindcss`, `@tailwindcss/vite` (+ bawaan template).
   **Tidak** menambah router, axios, react-query, zustand, chart, atau icon pack. HTTP pakai `fetch`; navigasi pakai state
   (2 tampilan: Workbench dan Kiriman MISP). Menambah dependency lain = tanya developer dulu.
3. **Token JWT disimpan di memori** (state/context React), **tidak** di `localStorage`/`sessionStorage`/cookie buatan JS.
   Konsekuensi yang diterima: refresh halaman = login ulang. Dasar: OWASP WSTG "Testing Browser Storage" (storage browser
   bisa dibaca JS saat XSS).
4. **Node di laptop host**, bukan kontainer. Versi minimum **Node 22.12+** (Vitest butuh Node ≥ 22.12; Vite butuh
   20.19+/22.12+). Cek di Tahap 0.
5. **Koneksi ke API lewat Vite `server.proxy`**: `/api` → `http://127.0.0.1:8000`. Backend **tidak** diubah (tidak menambah
   CORS). Proxy hanya berlaku di dev server; reverse proxy produksi masuk task deploy.
6. **Test: Vitest minimal** untuk fungsi murni (format skor, pemetaan status/label, parsing error). Tanpa testing-library.
7. **Label diambil dari field `indication` respons backend**, tidak dihitung ulang di frontend (backend menentukan label
   dari nilai sebelum pembulatan: 74,96 tampil `75.0` tetapi `TINGGI`).
8. **RBAC di UI hanya tampilan.** Sembunyikan aksi yang tidak berhak, tetapi kontrol sebenarnya 403 dari backend; UI tetap
   harus menampilkan 403 dengan rapi (bukan crash) bila terjadi.
9. **Layout 3 panel** (rel kiri riwayat, panel tengah bukti, rel kanan keputusan & aksi) + satu tampilan kecil **Kiriman
   MISP**. Di layar < 1024px, panel ditumpuk: bukti → keputusan → riwayat.
10. **Tema gelap slate** (bukan hitam pekat), satu warna aksen biru untuk elemen interaktif, warna verdict hanya untuk label.
    Wajib lolos cek kontras di proyektor (Tahap 4).
11. **Prioritas: fungsi jalan dulu, rapi belakangan** (developer, 2 Nov). Urutan wajib sebelum tim menguji: Tahap 0 → 1 → 2
    → 3. Di setiap tahap, butir bertanda **[NANTI]** boleh ditunda ke Tahap 4 bila waktu mepet; catat di progress.
    Yang **tidak boleh** ditunda karena menyangkut kebenaran data: aturan tampilan 1, 2, 4, 5, 7.
12. **Akses uji tim lewat LAN dari laptop developer** (sesi uji, bukan layanan tetap): `npm run dev:lan` (Vite `--host`)
    di laptop developer; anggota tim membuka `http://<IP-laptop>:5173` dari jaringan yang sama. API tetap terikat ke
    `127.0.0.1:8000` dan hanya terjangkau lewat proxy `/api` (Swagger `/docs` **tidak** ikut terbuka ke LAN).
    Aturan sesi ada di README bagian "Uji bersama tim" (Tahap 0). Akses tetap untuk tim nanti lewat deploy ke soc-ir + VPN
    (task deploy, di luar TASK-03).
13. **Desain visual memakai skill `impeccable`** (skill lokal developer; PRODUCT.md di root repo hasil `/impeccable init`).
    Brief-nya adalah dokumen ini: Keputusan, Koreksi, dan Aturan tampilan MENANG atas saran skill. Batasan tambahan:
    a. Tanpa dependency baru dan tanpa CDN saat runtime (font, ikon, CSS). Font hanya system font stack ATAU file `.woff2`
       berlisensi SIL OFL yang di-bundle di `frontend/src/assets/fonts/` beserta file lisensinya. Alasan: aplikasi dibuka
       analis lewat jaringan lab/VPN; request ke CDN pihak ketiga bisa gagal dan membocorkan IP analis.
    b. Monospace untuk IP dan `misp_event_uuid` adalah syarat fungsional, bukan pilihan gaya.
    c. Warna verdict hanya untuk label indikasi; `RENDAH` bukan hijau. Satu warna aksen untuk elemen interaktif.
    d. Tidak ada hero/landing, KPI, grafik, atau animasi dekoratif. Motion hanya sebagai respons aksi user
       (buka/tutup/konfirmasi) dan wajib menghormati `prefers-reduced-motion`.
    e. "Keberanian" desain dihabiskan di SATU tempat: strip ringkasan (skor/N/A + label + cakupan). Sisanya tenang.
    f. Kontras minimal WCAG AA, fokus keyboard terlihat, terbaca di 1280×720 dan 1024×768 (proyektor).
    g. Proses: di awal Tahap 1, sebelum menulis kode UI, tulis rencana desain (4–6 warna hex bernama, tipografi + perannya,
       layout ASCII, prinsip) di `TASK-03-progress.md` bagian "Keputusan desain", lalu BERHENTI dan tunggu persetujuan
       developer. Tahap 2–4 mengikuti rencana itu; perubahan = tanya dulu. `DESIGN.md` ditulis lewat impeccable setelah
       rencana disetujui.
    h. Self-critique pakai screenshot: jangan menambah Playwright/alat baru; minta developer mengirim screenshot.

Hasil grilling rencana (developer, 2 Nov 2026):

14. **Kirim MISP atas IP yang sudah pernah dikirim lewat check lain.** Backend mencegah duplikat per `check_id`, bukan per
    IP, sedangkan "Cek ulang" membuat check baru. Frontend mencocokkan `GET /iocs` juga per `ip`; bila ada, konfirmasi
    dengan teks "IP ini sudah pernah dikirim lewat check #N (<status>). Kirim lagi sebagai catatan baru?" Jangan memakai
    kata "duplikat": check baru atas IP yang sama adalah operasi baru, bukan retry (riset §7: lookup ulang bukan sighting
    otomatis). Issue terpisah untuk keputusan tim (dedup per IP vs update event): **#29**.
15. **401 dan sesi.** Handler 401 global **tidak berlaku** untuk `POST /auth/login` (salah password tetap "Username atau
    password salah"). Top bar menampilkan jam berakhir sesi **absolut** ("sesi berakhir 14:33 WIB", bukan hitung mundur
    karena jam laptop anggota tim bisa berbeda), dibaca dari `exp` JWT dengan decode **base64url** (`-`→`+`, `_`→`/`,
    tambah padding). Draf alasan MISP yang hilang saat sesi habis diterima sebagai known gap.
16. **Alur MISP tidak teruji di mode mock** (semua hasil mock ber-flag `SUMBER_SIMULASI`, tombol kirim tidak muncul).
    Sebelum sesi uji, developer membuat 1–2 check **live** dengan sadar (masing-masing memakai kuota 1 VirusTotal +
    1 AbuseIPDB). Langkah ini ditulis di README "Uji bersama tim" dan di Cek selesai Tahap 3.
17. **Status `pending`** tampil kuning "Sedang diproses (pending)", tanpa tombol kirim (kirim ulang atas `pending` selalu
    409). Saat ditemukan pada pemuatan ulang, tambah teks "bila tertahan lama, hubungi admin".
18. **Kasus tepi data.** Riwayat digabung dengan dedup per `id` dan "Muat lagi" disembunyikan memakai `total`.
    `ERROR` `RATE_LIMIT` menampilkan `retry_after_seconds` ("coba lagi ±N detik"). Check lama TASK-01 (hanya
    `source`/`status`/`reason`) tampil status saja, field lain "tidak tersedia". `GET /health` 503 → badge merah
    "API: DB error", bukan crash dan bukan diam.
19. **IP klien di audit log** (`request.client.host`) selalu IP gateway Docker bila lewat Vite proxy. Bukti KM-8 tetap sah
    (berbasis username). Diterima; `xfwd` proxy **tidak** diaktifkan. Catatan task deploy: nginx + `--forwarded-allow-ips`.
20. **Format waktu** memotong string (tanpa `new Date()`): `02 Nov 2026 14:03:07 WIB`, **hanya** bila string berakhiran
    `+07:00`; string lain tampil mentah. `evidence_summary.lastReportedAt` AbuseIPDB adalah string UTC mentah (`+00:00`)
    dan **tidak** dilabeli WIB; tab AbuseIPDB menampilkan `source_time` (sudah WIB dari backend) sebagai waktu laporan
    terakhir. ISO asli tampil di tab Raw JSON dan tooltip.
21. **Konfirmasi MISP inline** (tanpa `window.confirm`): klik "Kirim ke MISP" mengganti tombol dengan panel teks
    Keputusan 14 + tombol "Kirim lagi sebagai catatan baru" dan "Batal".
22. **Jam sesi** memakai `Intl.DateTimeFormat('id-ID', { timeZone: 'Asia/Jakarta', hour: '2-digit', minute: '2-digit' })`
    dari `exp`; ini satu-satunya konversi waktu di frontend. Frontend **tidak** logout sendiri saat jam lokal melewati
    `exp`; logout hanya karena 401 dari backend.
23. **Field bukti.** Key VirusTotal yang tidak ada di respons tampil "—" (bukan 0); rasio vendor dihitung dari key yang
    ada dengan catatan "(sebagian kategori tidak ada di respons sumber)". Key `simulasi` di `evidence_summary` tidak
    dirender sebagai field. `SourceResult.flags` (mis. `NO_VENDOR_OPINION`) tampil sebagai chip di baris sumber (tab
    Ringkasan) dan di tab sumbernya, selain chip flag tingkat check di rel kanan.
24. **Alur kerja repo.** Issue induk "[FITUR] Frontend workbench investigasi IP" → PR docs `docs/task-03-rencana`
    (`Refs #28`) berisi dokumen ini + `PRODUCT.md` → issue terpisah #29 "Keputusan dedup kiriman MISP: per IP atau
    update event".
25. **`npm audit`** dijalankan penuh **dan** dengan `--omit=dev`. Untuk paket `vite`, advisory **severity apa pun**
    (termasuk moderate/low) memblokir sesi LAN sampai di-upgrade: advisory `server.fs` Vite (mis. GHSA-x574-m823-4x7w,
    CVE-2025-32395) dinilai moderate dan hanya berlaku saat dev server dibuka dengan `--host`, persis mode `dev:lan`.
    Paket lain: high/critical di dependency runtime → tahap berhenti dan lapor; sisanya dicatat. Tanpa `--force`.
26. **Uji negatif akses file lewat dev server** (Cek selesai Tahap 0), dijalankan dari **perangkat lain lewat IP LAN**:
    `/@fs/<path-absolut-repo>/secrets/<nama-file>`, `/@fs/<path-absolut-repo>/.env`, serta varian
    `…?raw??` dan `…?import&raw??`. Semua harus 403 (atau tidak mengembalikan isi file). Pakai
    `curl -s -o /dev/null -w '%{http_code}'`. Konfigurasi `server.fs` bawaan tidak diubah kecuali uji ini gagal.
27. **Bila ada varian `/@fs` yang tidak 403:** simpan body ke file sementara di perangkat penguji, bandingkan `sha256sum`
    dengan `sha256sum secrets/<nama-file>` di laptop. Sama = gagal (bocor); beda = lolos dengan catatan. Hapus file
    sementara; jangan pernah `cat` body atau isi file, dan jangan menempelkannya ke chat.
28. **Tambahan `CLAUDE.md`** (dikerjakan di Tahap 0, bukan di PR docs): di "Aturan keamanan", (a) advisory `vite` severity
    apa pun = jangan jalankan `dev:lan` sampai di-upgrade; (b) tidak ada `VITE_*` berisi rahasia dan
    `server.allowedHosts: true` dilarang.

## Koreksi atas dokumen referensi (wajib diikuti; dokumen riset + backend menang)

| # | Referensi | Yang benar untuk v1 |
|---|---|---|
| 1 | Shodan InternetDB = enrichment MVP | **Tidak ada** di v1 (riset §2: tahap lanjut; backend tidak punya adapter). Tidak ada tab Enrichment |
| 2 | Label Clean/Suspicious/…, rendah = hijau | Label backend `RENDAH`/`PERLU_PEMERIKSAAN`/`TINGGI`/`SANGAT_TINGGI`; rendah **bukan hijau** (lihat tabel label) |
| 3 | Semua data kosong = "No Record" | Tampilkan status asli per sumber (6 status) + penjelasan; `NO_RECORD` ≠ `ERROR` ≠ `SKIPPED` ≠ `INSUFFICIENT_DATA` |
| 4 | Search "IP / domain / hash" | Hanya **satu IPv4 publik**; placeholder & teks bantuan menyebut itu |
| 5 | Status sumber (OK/rate-limited) di top bar | Tidak ada endpoint-nya. Ganti badge **"MISP: mock/live"** dari `GET /api/v1/health` |
| 6 | Skeleton per kartu, sumber cepat tampil duluan | `POST /checks` sinkron, satu respons → **satu** loading state + teks "bisa sampai belasan detik" |
| 7 | Tombol refresh cache + retry per sumber | Tidak ada force refresh (gap 18). Satu tombol **"Cek ulang"** = `POST /checks` lagi (sumber OK dari cache, `ERROR` dipanggil ulang karena error tidak di-cache) |
| 8 | Kartu berisi ISP, ASN, negara, kategori, daftar vendor | Hanya field yang ada di `evidence_summary` (lihat Tahap 2). Selebihnya lewat **link pivot** ke situs sumber |
| 9 | Filter IP/label di riwayat | `GET /checks` tanpa filter → filter **client-side** pada halaman yang sudah dimuat; beri tahu itu bukan pencarian penuh |
| 10 | "Sudah di-submit" → tombol nonaktif | Status submission dari `GET /iocs` (cocokkan `check_id`). `failed` → tombol **"Kirim ulang"**; `mock_sent` ditulis **"Terkirim (mock)"** |
| 11 | Context flag RIOT | Pakai flag backend `WHITELISTED` (RIOT = GreyNoise, v2) |
| 12 | "Framework belum ditentukan" | Sudah: React + TypeScript (CLAUDE.md) |

## Kontrak API yang dipakai (sudah ada, jangan diubah)

Semua di prefix `/api/v1`. Respons waktu sudah **ISO 8601 WIB (+07:00)**: tampilkan apa adanya, jangan konversi zona.

| Endpoint | Siapa | Catatan penting untuk frontend |
|---|---|---|
| `POST /auth/login` | semua | **`application/x-www-form-urlencoded`** (`username`, `password`) via `URLSearchParams`, BUKAN JSON. 401 → pesan umum "Username atau password salah" |
| `GET /auth/me` | semua | `role` (`admin`/`analyst`/`viewer`), `can_send_misp`, `is_active` |
| `GET /health` | publik | `status`, `db`, `misp_mode` (`mock`/`live`), `time` |
| `POST /checks` `{ip}` | admin, analyst | 201 `CheckOut`. 422 **dua bentuk**: `{assessment_status:"INPUT_DITOLAK", reason_code, message}` ATAU standar FastAPI `{detail:[...]}`. Input ditolak **tidak** tersimpan di riwayat |
| `GET /checks?limit&offset` | semua | `limit` 1–100 (default 20). Urut terbaru |
| `GET /checks/{id}` | semua | 404 bila tidak ada |
| `POST /iocs/misp` `{check_id, reason, tags}` | admin, analyst + `can_send_misp` | `reason` 10–2000 karakter; `tags` maks 20, tiap tag 1–64. 201 baru; **200** kirim ulang dari `failed`; **409** `{detail, submission_id}` duplikat; **422** alasan pendek / `INPUT_DITOLAK` / `SUMBER_SIMULASI`; **501/502** body `IocOut` berstatus `failed` |
| `GET /iocs?limit&offset` | semua | `status`: `pending`/`mock_sent`/`sent`/`failed`, `misp_event_uuid`, `error_message` |

Semua endpoint selain `/health` & login butuh header `Authorization: Bearer <token>`. 401 dari endpoint **selain
`POST /auth/login`** → hapus token dari memori, kembali ke login dengan pesan "Sesi berakhir, login lagi" (JWT berlaku
30 menit; Keputusan 15). 401 dari login = "Username atau password salah".

## Aturan tampilan (kriteria selesai, bukan preferensi)

**Label indikasi** (dari `indication`; rentang mengikuti riset Bab 4, hanya untuk keterangan):

| `indication` | Rentang | Teks tampil | Warna |
|---|---|---|---|
| `RENDAH` | 0 – <25 | "Indikasi rendah · tetap baca bukti" | abu/biru netral (**bukan hijau**) |
| `PERLU_PEMERIKSAAN` | 25 – <50 | "Perlu pemeriksaan" | kuning |
| `TINGGI` | 50 – <75 | "Indikasi tinggi · dahulukan pemeriksaan" | oranye |
| `SANGAT_TINGGI` | 75 – 100 | "Indikasi sangat tinggi · periksa segera, tanpa auto-block" | merah |
| `null` | — | **"N/A"** + `assessment_status` (`DATA_TERBATAS`/`TIDAK_TERSEDIA`) + cakupan | abu-abu |

**Status per sumber** (tampilkan kode asli + penjelasan):
`OK_SIGNAL` "ada sinyal buruk" · `OK_NO_SIGNAL` "tidak ada sinyal buruk pada data ini (bukan jaminan aman)" ·
`NO_RECORD` "sumber tidak punya catatan untuk IP ini" · `INSUFFICIENT_DATA` "data sumber tidak cukup untuk dinilai" ·
`ERROR` "sumber gagal: <reason>" · `SKIPPED` "dilewati: <reason>".
`reason` yang mungkin: `AUTH`, `RATE_LIMIT`, `TIMEOUT`, `UPSTREAM`, `INVALID_RESPONSE`, `INTERNAL_ERROR`,
`ADAPTER_NOT_IMPLEMENTED`, `QUOTA_INTERNAL` (beri teks Indonesia singkat untuk tiap kode; kode asli tetap terlihat).

**Flag** (chip berpenjelasan, urutan sesuai respons): `HASIL_BERBEDA` "kedua sumber tidak sepakat (selisih ≥ 50), baca
bukti keduanya" · `NO_VENDOR_OPINION` "vendor VirusTotal tidak memberi opini" · `WHITELISTED` "AbuseIPDB menandai
whitelist; skor tidak dipotong, butuh review analis" · `SUMBER_SIMULASI` (lihat aturan 4).

1. **null tidak pernah tampil sebagai 0, "Clean", atau "aman".** `risk_score: null` → "N/A". `normalized_score: null` → "—".
2. **Skor bukan probabilitas.** Tidak ada tanda `%` pada skor gabungan. Footer: "Skor = label indikasi untuk triase, bukan
   peluang IP jahat."
3. **Coverage & kesegaran di dekat skor:** `coverage` (x/2), `checked_at`, dan per sumber `retrieved_at`,
   `from_cache` (badge "Cache" / "Ambil baru"), `expires_at`, `source_time` + `source_time_type` (`last_report` →
   "laporan terakhir", `last_analysis` → "analisis terakhir"; null → "tidak tersedia").
4. **`SUMBER_SIMULASI` mencolok** di strip ringkasan dan di setiap baris riwayat (kuning bergaris/berbingkai tebal +
   teks "SIMULASI · bukan data nyata"). Tombol kirim MISP untuk check ini **tidak ditampilkan**; ganti teks "Hasil simulasi
   tidak boleh dikirim ke MISP".
5. **Kegagalan tidak pernah tampil sebagai sukses.** `failed`/501/502 → merah dengan `error_message`. `mock_sent` →
   "Terkirim (mock)" + `misp_event_uuid` (berawalan `MOCK-`), bukan "terkirim ke MISP".
6. **Identifier pakai font monospace** (IP, `misp_event_uuid`).
7. **Data pihak ketiga dirender sebagai teks** (React escaping biasa). **Dilarang** `dangerouslySetInnerHTML`.
8. **Label = teks + warna**, tidak pernah warna saja.
9. Tidak ada tombol/teks "Auto-block", tidak ada angka "confidence", tidak ada grafik.

## Peta layar

```
┌ TOP BAR: SOC16 TI │ [ IPv4 publik, mis. 118.25.6.39 ] [Cek IP] │ Workbench · Kiriman MISP │ MISP: mock │ user · role │ Keluar ┐
├ REL KIRI (riwayat) ─┬ PANEL TENGAH (bukti 1 IP) ─────────────────┬ REL KANAN (keputusan & aksi, sticky) ┤
│ GET /checks         │ Strip: IP · status · badge simulasi        │ Cakupan x/2 + sumber yang tidak menjawab│
│ baris: IP, label,   │        skor/N/A · label · cakupan · waktu │ Kesegaran: checked_at, cache            │
│ skor/N/A, waktu,    │ Tab: Ringkasan | AbuseIPDB | VirusTotal |  │ Flag (chip berpenjelasan)               │
│ badge simulasi      │      Raw JSON                              │ Status MISP + form/tombol kirim         │
│ filter teks IP      │ Ringkasan: 2 baris per sumber + peringatan │ Copy hasil · Cek ulang                  │
│ "Muat lagi"         │   HASIL_BERBEDA bila ada                   │ Pivot ↗ AbuseIPDB · VirusTotal          │
└─────────────────────┴────────────────────────────────────────────┴─────────────────────────────────────────┘
  FOOTER: Sumber: AbuseIPDB, VirusTotal · scoring_version · Skor = label indikasi, bukan probabilitas
```

Viewer: tidak melihat form Cek IP, tombol Cek ulang, dan form MISP; melihat riwayat, detail, dan Kiriman MISP.
Analyst tanpa `can_send_misp`: tidak melihat form MISP (teks "Kirim ke MISP butuh izin dari admin").

---

## Tahap 0 — Scaffold `frontend/` + Tailwind + proxy + gerbang kualitas

**Kerjakan:**
1. Cek `node --version` ≥ 22.12. Kalau kurang, **berhenti** dan beri developer perintah upgrade (CachyOS) tanpa menjalankannya.
2. `npm create vite@latest frontend -- --template react-ts` dari root repo. Cek versi terbaru di dokumentasi resmi; kunci
   lewat `package-lock.json` (di-commit).
3. Tailwind v4: `npm install tailwindcss @tailwindcss/vite`, plugin di `vite.config.ts`, `@import "tailwindcss";` di CSS utama.
   Hapus aset demo template (logo, counter, CSS bawaan).
4. `vite.config.ts` `server.proxy`: `'/api'` → `{ target: 'http://127.0.0.1:8000', changeOrigin: true }` (tanpa rewrite;
   prefix `/api/v1` tetap). Default dev server tetap `localhost` (`npm run dev`).
   Tambah script **`"dev:lan": "vite --host"`** untuk sesi uji tim (Keputusan 12). **Jangan** mengisi
   `server.allowedHosts: true` (docs Vite: membuka celah DNS rebinding); akses lewat alamat IP sudah diterima secara bawaan.
5. Vitest: `npm install -D vitest`, script `"test": "vitest run"`. Satu test contoh yang lulus.
6. `.gitignore`: tambahkan `frontend/dist/` (`node_modules/` sudah ada). Pastikan tidak ada file `.env*` di `frontend/`.
   Aturan: **tidak ada variabel `VITE_*` berisi rahasia** — semua `VITE_*` ikut ter-bundle ke browser.
7. README bagian "Frontend (dev)": prasyarat Node, `npm ci`, `npm run dev`, backend harus sudah `docker compose up`.
   `CLAUDE.md`: ubah baris frontend "BELUM dimulai" → "TASK-03", tambah perintah gerbang frontend (di bawah), dan dua
   aturan keamanan dari Keputusan 28.
8. README bagian **"Uji bersama tim (LAN)"**, berisi aturan sesi:
   - Pakai jaringan yang hanya berisi tim (mis. hotspot HP developer ber-password), **bukan** Wi-Fi kampus terbuka:
     koneksi dev server masih HTTP biasa, jadi password login lewat jaringan tanpa enkripsi TLS.
   - Jalankan `docker compose up -d` lalu `cd frontend; npm run dev:lan`; bagikan `http://<IP-laptop>:5173`.
     Cari IP laptop dengan `ip -4 addr`. Kalau firewall laptop aktif, buka port 5173 **hanya selama sesi**.
   - Matikan (`Ctrl+C`) setelah sesi selesai. Laptop jangan sleep selama sesi.
   - Akun: 4 akun hasil `scripts.seed_users` (admin, analyst_misp, analyst, viewer), satu per anggota sesuai peran.
     Password dibagikan langsung/lewat Bitwarden, **tidak** ditempel di grup chat atau di repo.
   - Default `SOURCES_MODE=mock` (badge SIMULASI). Mode live memakai **kuota bersama** (VirusTotal 4/menit, 500/hari);
     beri tahu tim sebelum menyalakannya.
   - Alur kirim MISP hanya bisa dicoba pada check **live** (hasil mock tidak boleh dikirim). Sebelum sesi, developer
     membuat 1–2 check live dengan sadar (masing-masing memakai kuota 1 VirusTotal + 1 AbuseIPDB), lalu kembali ke mock.
     (Keputusan 16)

**Gerbang kualitas frontend** (dijalankan di setiap tahap, selain gerbang backend dari skill):
```fish
cd frontend
npm ci
npm run lint        # bila template menyediakan; kalau tidak ada, catat di progress
npm run build       # tsc -b + vite build, harus tanpa error
npm test
npm audit --omit=dev   # catat hasilnya; jangan --force
npm audit              # penuh; kebijakan blokir di bawah
cd ..
```

Kebijakan hasil `npm audit` (Keputusan 25): advisory pada paket `vite` dengan **severity apa pun** → jangan jalankan
`dev:lan` sampai di-upgrade (upgrade biasa, tanpa `--force`). High/critical di dependency runtime → tahap berhenti dan
dilaporkan ke developer. Temuan lain dicatat di progress.

**Cek selesai:** gerbang hijau; `docker compose up -d` lalu `cd frontend; npm run dev`, buka `http://localhost:5173/api/v1/health`
di browser → JSON health dari backend (bukti proxy jalan, tanpa CORS). `git status` tidak memuat `node_modules/`, `dist/`, `.env`.
Uji LAN (developer): `npm run dev:lan`, buka `http://<IP-laptop>:5173/api/v1/health` dari HP/laptop lain di jaringan yang
sama → JSON health; `http://<IP-laptop>:8000/docs` dari perangkat lain **harus gagal** (API tidak terbuka ke LAN).
Uji akses file (Keputusan 26–27), dari perangkat lain lewat IP LAN: `http://<IP-laptop>:5173/@fs/<path-absolut-repo>/secrets/<nama-file>`,
`…/@fs/<path-absolut-repo>/.env`, dan varian `?raw??` serta `?import&raw??` → semuanya 403 (atau tanpa isi file), dicek dengan
`curl -s -o /dev/null -w '%{http_code}'`. Bila ada yang bukan 403, bandingkan `sha256sum` seperti Keputusan 27; isi file tidak pernah
dicetak. `dev:lan` hanya dijalankan bila `npm audit` penuh tidak memuat advisory `vite` (Keputusan 25).

---

## Tahap 1 — API client, tipe, login, shell layout

**Kerjakan:**
0. **Rencana desain dulu, kode UI belakangan (Keputusan 13g).** `PRODUCT.md` sudah ada. Jalankan impeccable dengan dokumen
   ini sebagai brief, tulis "Keputusan desain" di `TASK-03-progress.md` (4–6 warna hex bernama, tipografi + perannya,
   layout ASCII, prinsip), lalu **berhenti dan tunggu persetujuan developer**. Baru setelah disetujui, tulis `DESIGN.md`
   lewat impeccable dan lanjut ke butir 1. Tahap 2–4 mengikuti rencana itu; perubahan = tanya dulu.
1. `src/api/types.ts`: tipe TS **ditulis tangan** sesuai skema backend (`CheckOut`, `SourceResult`, `CheckRejected`,
   `CheckPage`, `IocOut`, `IocPage`, `IocDuplicate`, `UserOut`, `HealthResponse`, union status/label/flag/reason).
   Sumber kebenaran: `backend/app/schemas/*.py` dan Swagger `/docs`.
2. `src/api/client.ts`: wrapper `fetch` → hasil terstruktur `{ok:true,data}` / `{ok:false,status,kind,body}`; header
   Bearer dari memori; 401 dari endpoint **selain `POST /auth/login`** → panggil handler logout global (Keputusan 15).
   **Jangan** `console.log` token, header, atau body login.
3. `src/lib/errors.ts`: `parseCheckError()` membedakan 422 `INPUT_DITOLAK` vs 422 standar FastAPI; `parseIocError()` untuk
   404/409/422/501/502. Test Vitest untuk keduanya.
4. Auth context: login (form-urlencoded) → simpan token di state → `GET /auth/me` → simpan user. Logout = hapus state.
   Halaman login: dua input + tombol, pesan error umum (tidak membedakan user tidak ada vs password salah).
   `src/lib/session.ts` (+ test Vitest): baca `exp` dari payload JWT dengan decode **base64url** (ganti `-_` ke `+/`, tambah
   padding) dan format jam berakhir dengan `Intl.DateTimeFormat('id-ID', { timeZone: 'Asia/Jakarta', … })` (Keputusan 22).
   Tidak ada logout proaktif dari jam lokal; payload tidak pernah dicetak ke console.
5. Shell: top bar (judul, nav Workbench/Kiriman MISP, badge `MISP: <misp_mode>` dari `/health`, username + badge role,
   "sesi berakhir HH.mm WIB", tombol Keluar), area konten 3 panel kosong dengan teks placeholder, footer. `/health` 503
   (`db: error`) → badge merah "API: DB error" (Keputusan 18).
6. Helper `can(user)`: `canCheck` (admin/analyst), `canSendMisp` (admin, atau analyst dengan `can_send_misp`).

**Cek selesai:** gerbang hijau. Rencana desain (butir 0) sudah disetujui developer sebelum kode UI ditulis. Manual: login
3 role (admin, analyst, viewer) → badge role benar; password salah → "Username atau password salah" (bukan "Sesi berakhir");
tunggu/ubah token jadi tidak valid → kembali ke login dengan "Sesi berakhir, login lagi". Jam berakhir sesi tampil absolut
WIB. Refresh halaman → kembali ke login (konsekuensi Keputusan 3).

---

## Tahap 2 — Workbench: cek IP, bukti, riwayat

**Kerjakan:**
1. **Search bar** (top bar, autofocus, Enter = submit): validasi ringan di browser hanya untuk "kosong"; validasi IP
   sebenarnya oleh backend. 422 `INPUT_DITOLAK` → pesan `message` + `reason_code` di bawah search, panel tengah tidak berubah.
   Loading: satu state, tombol jadi "Memeriksa…", teks "bisa sampai belasan detik".
2. `src/lib/format.ts` (+ test Vitest): `formatScore(null)` → "N/A" (bukan "0"); `formatScore(3.8)` → "3.8";
   teks & kelas warna per `indication` (null → N/A abu-abu); teks per status sumber, reason, flag; teks `source_time_type`.
   `formatTime(iso)` (+ test Vitest): potong string menjadi `02 Nov 2026 14:03:07 WIB` **hanya** bila berakhiran `+07:00`;
   string lain (mis. `+00:00`) tampil mentah, tanpa `new Date()` (Keputusan 20). Test wajib mencakup kasus `+00:00`.
3. **Panel tengah:** strip ringkasan (IP monospace, `assessment_status`, badge simulasi, skor/N/A besar, label, cakupan,
   `checked_at`, `checked_by`). Tab:
   - **Ringkasan:** satu baris per sumber (nama, status + penjelasan, `normalized_score` atau "—", badge cache, chip
     `SourceResult.flags`) + peringatan `HASIL_BERBEDA` bila ada. `ERROR` `RATE_LIMIT` dengan `retry_after_seconds` →
     "coba lagi ±N detik".
   - **AbuseIPDB:** `abuseConfidenceScore` (angka; bar 0–100 **[NANTI]**), `totalReports`, `numDistinctUsers`,
     waktu laporan terakhir dari **`source_time`** (bukan `evidence_summary.lastReportedAt`, yang UTC mentah),
     `isWhitelisted` (null → "tidak diketahui"); plus `retrieved_at`, `from_cache`, `expires_at`, `http_status`, `duration_ms`.
   - **VirusTotal:** `malicious`, `suspicious`, `harmless`, `undetected`, `timeout` (key yang tidak ada di respons → "—",
     bukan 0); rasio "`malicious + suspicious` / `malicious + suspicious + harmless + undetected`" vendor dari key yang
     ada, dengan catatan "(sebagian kategori tidak ada di respons sumber)" bila ada yang hilang (rasio bukan
     probabilitas); waktu analisis terakhir; field cache seperti di atas; chip `SourceResult.flags`.
   - **Raw JSON [NANTI]:** `CheckOut` apa adanya (`JSON.stringify(…, null, 2)` dalam `<pre>`, teks biasa).
   Key `simulasi` di `evidence_summary` tidak dirender sebagai field (sudah ada badge `SUMBER_SIMULASI`; Keputusan 23).
   Kalau `evidence_summary` kosong (status non-OK, atau check lama TASK-01 yang hanya punya `source`/`status`/`reason`),
   tampilkan status + penjelasan saja, field cache/waktu "tidak tersedia", jangan field kosong berderet.
4. **Rel kiri:** `GET /checks?limit=20`, tombol "Muat lagi" (offset) yang digabung dengan **dedup per `id`** (check baru
   menggeser offset) dan disembunyikan bila semua sudah dimuat (pakai `total`); filter teks IP client-side **[NANTI]**
   (tulis "menyaring yang sudah dimuat"). Baris: IP, label/N/A, skor, waktu, badge simulasi. Klik → muat
   `GET /checks/{id}` di panel tengah **tanpa** cek ulang. Check baru otomatis masuk paling atas.
5. **Rel kanan (sticky):** cakupan + nama sumber yang tidak menjawab; kesegaran; chip flag; tombol **Cek ulang** (hanya
   `canCheck`); **Copy hasil [NANTI]** (teks ringkas: IP, waktu, status, skor/N/A + label, cakupan, flag, status per sumber,
   `scoring_version`, kalimat "skor = label indikasi, bukan probabilitas"; kalau Clipboard API gagal, tampilkan teks di
   `<textarea>` readonly); **pivot [NANTI]** `https://www.abuseipdb.com/check/<ip>` dan halaman IP VirusTotal (cek format URL
   resmi saat mengerjakan), `target="_blank" rel="noopener noreferrer"`. Slot status MISP diisi di Tahap 3.
6. State kosong awal: search terfokus + riwayat terakhir; panel tengah berisi satu kalimat petunjuk (bukan layar sambutan).

**Cek selesai:** gerbang hijau. Manual di mode mock, **setiap baris tabel IP demo TASK-02** dicek dan di-screenshot:
`1.1.1.1` (SANGAT_TINGGI), `1.0.0.1` (HASIL_BERBEDA), `8.8.8.8` (N/A, DATA_TERBATAS 1/2, ERROR TIMEOUT),
`8.8.4.4` (N/A, TIDAK_TERSEDIA 0/2), `9.9.9.9` (WHITELISTED, skor tetap), `149.112.112.112` (0,0 + NO_VENDOR_OPINION,
**tidak hijau**), `208.67.222.222` (N/A, INSUFFICIENT_DATA). Input ditolak: `10.10.50.10`, `127.0.0.1`, `2001:db8::1`,
`abc` → pesan backend, tidak masuk riwayat. Semua hasil mock menampilkan badge SIMULASI. Login viewer → search tidak ada.
Tampilan mengikuti "Keputusan desain" yang disetujui (Keputusan 13g).

---

## Tahap 3 — Kirim ke MISP + tampilan Kiriman MISP

**Kerjakan:**
1. Status submission per check: muat `GET /iocs?limit=100` (dan setelah setiap kirim), cocokkan `check_id` **dan** `ip`.
   Batas: hanya 100 kiriman terbaru yang dicocokkan → catat sebagai known gap (cukup untuk tim 4 orang).
2. Rel kanan, bila `canSendMisp` dan check **bukan** simulasi:
   - Belum ada submission untuk `check_id` ini → form: `textarea` alasan (hitung karakter, minimal 10, maks 2000; tombol
     tetap aktif dan beri pesan inline bila kurang), input tag dipisah koma (maks 20, tiap tag ≤ 64), tombol
     **Kirim ke MISP**. Teks kecil: "Pengiriman manual. Tidak memblokir IP."
   - Belum ada submission untuk `check_id` ini **tetapi** IP yang sama sudah pernah dikirim lewat check lain → klik
     "Kirim ke MISP" membuka panel konfirmasi **inline** (bukan `window.confirm`): "IP ini sudah pernah dikirim lewat
     check #N (<status>). Kirim lagi sebagai catatan baru?" + tombol "Kirim lagi sebagai catatan baru" / "Batal"
     (Keputusan 14, 21). Jangan memakai kata "duplikat".
   - Saat mengirim: tombol "Mengirim…" dan **tidak bisa diklik dua kali** (backend juga mencegah duplikat per `check_id`).
   - 201/200 `mock_sent` → "Terkirim (mock)" + `misp_event_uuid` + waktu + pengirim. `sent` → "Terkirim ke MISP".
   - `pending` → kuning "Sedang diproses (pending)", tanpa tombol kirim; bila ditemukan saat memuat ulang, tambah
     "bila tertahan lama, hubungi admin" (Keputusan 17).
   - 409 → muat ulang `/iocs`, tampilkan submission yang sudah ada (bukan error merah).
   - 422 → pesan `detail` backend di dekat form. 501/502 → merah, `error_message`, tombol **Kirim ulang** (form alasan
     tetap terisi).
   - 403 → "Akun ini tidak berhak mengirim ke MISP" (seharusnya tidak terjadi karena tombol tersembunyi; tetap ditangani).
3. Check simulasi → teks pengganti (aturan tampilan 4). Viewer/analyst tanpa izin → teks izin, tanpa form.
4. **Tampilan Kiriman MISP:** tabel polos `GET /iocs` (paginasi limit/offset): waktu, IP (monospace), status (teks + warna;
   `failed` merah), `misp_event_uuid`, pengirim, alasan (dipotong, klik untuk lengkap), `error_message`. **[NANTI]** Klik baris → buka
   check terkait di Workbench.
5. Test Vitest: pemetaan status submission → teks/warna (`mock_sent` tidak pernah "Terkirim ke MISP"; `failed` merah;
   `pending` kuning tanpa tombol kirim) dan pencocokan submission per `check_id` vs per `ip` (teks konfirmasi tidak
   memuat kata "duplikat").

**Cek selesai:** gerbang hijau. Manual: (a) analyst dengan izin kirim **check live yang dibuat sengaja sebelum sesi**
(Keputusan 16; mis. 1–2 IP dengan `SOURCES_MODE=live`) → "Terkirim (mock)"; klik lagi → status yang sama, tidak dobel
(cek tabel Kiriman MISP). "Cek ulang" atas IP yang sama lalu kirim → panel konfirmasi inline muncul sebelum terkirim. (b) check simulasi →
tidak ada tombol; uji paksa lewat Swagger → 422 terlihat. (c) alasan 5 karakter → pesan inline, tidak terkirim.
(d) viewer → tidak ada form.

---

## Tahap 4 — Bukti demo, uji akses negatif, polish, README

**Kerjakan:**
1. **Uji akses negatif KM-8 (bukti):** login viewer di UI → screenshot (search & form MISP tidak ada). Lalu buktikan
   penegakan backend: dengan token viewer, `POST /api/v1/checks` lewat Swagger/devtools → **403**. Simpan screenshot +
   potongan log/audit di folder bukti **di luar repo**. Ulangi untuk analyst tanpa `can_send_misp` → `POST /iocs/misp` 403.
2. Cek tampilan di 1280×720 dan 1024×768 (resolusi umum proyektor) + kontras teks (zoom 125%) + fokus keyboard terlihat +
   `prefers-reduced-motion` dihormati. Perbaiki yang tidak terbaca. Uji layar < 1024px (panel bertumpuk). Bukti berupa
   screenshot dari developer (Keputusan 13h); jangan menambah Playwright/alat baru. Cek tab Network: tidak ada request
   ke luar origin (tanpa CDN).
3. Jalankan checklist "Aturan tampilan" satu per satu, centang di progress.
4. README: screenshot workbench, cara login, peta peran → aksi, batasan v1 (lihat Known gaps).
5. `docs/tasks/TASK-03-progress.md` lengkap; PR `Closes #<issue>`.

**Cek selesai:** gerbang hijau; checklist aturan tampilan semua ✅; bukti uji negatif tersimpan.

## Definition of Done TASK-03

- [ ] Login → workbench → cek IP → baca bukti → kirim ke MISP / copy hasil **tanpa pindah halaman**
- [ ] Tidak ada tempat null tampil sebagai 0 / "Clean" / hijau; skor tidak pernah bertanda `%`
- [ ] Label dari `indication` backend; status, reason, dan flag tampil dengan kode asli + penjelasan
- [ ] Badge `SUMBER_SIMULASI` di strip dan riwayat; hasil simulasi tidak punya tombol MISP
- [ ] `failed`/501/502 merah; `mock_sent` = "Terkirim (mock)"; klik ganda tidak menggandakan
- [ ] Viewer & analyst tanpa izin tidak melihat aksi terlarang; uji negatif 403 backend terdokumentasi (KM-8)
- [ ] Token hanya di memori; tidak ada token/password di console, log, URL, atau storage browser
- [ ] Tidak ada dashboard/KPI/grafik/peta; tidak ada Shodan; tidak ada `dangerouslySetInnerHTML`
- [ ] Gerbang frontend + backend hijau; `npm audit` (penuh dan `--omit=dev`) tercatat, tanpa advisory `vite` terbuka
- [ ] Tanpa request CDN/pihak ketiga saat runtime (cek tab Network); font system stack atau `.woff2` SIL OFL lokal
- [ ] "Keputusan desain" (`TASK-03-progress.md`) disetujui developer dan diikuti; `DESIGN.md` ada
- [ ] Uji `/@fs` dari perangkat lain lewat LAN (Keputusan 26) tercatat di progress

## Known gaps (diketahui sejak awal)

1. **Tanpa force refresh** (warisan gap 18 TASK-02): "Cek ulang" tetap memakai cache sumber yang masih berlaku.
2. **Filter riwayat hanya client-side** (backend tanpa parameter filter) dan riwayat mock/live bercampur (gap 19).
3. **Status submission dicocokkan dari 100 kiriman terbaru** saja, termasuk pencocokan per IP (Keputusan 14).
4. **Refresh = login ulang** (token di memori). Perbaikan nanti: cookie httpOnly dari backend.
5. **Tipe TS ditulis tangan**, bisa melenceng dari skema backend; nanti bisa generate dari OpenAPI.
6. **Proxy hanya dev server.** Produksi di soc-ir butuh reverse proxy (mis. nginx) + header keamanan (CSP, dll.) → task deploy.
7. **Clipboard API** butuh secure context (localhost aman; soc-ir lewat http biasa mungkin tidak) → fallback textarea.
8. **Field kartu terbatas** pada `evidence_summary` (tanpa ISP/ASN/negara/kategori/daftar vendor) sampai backend diperluas.
9. **Loading tidak per sumber** karena `POST /checks` sinkron; satu cek live bisa >10 detik (gap 17 & 24 TASK-02).
10. **Sesi uji LAN memakai dev server Vite + HTTP biasa** (tanpa TLS, bukan untuk produksi), dan bergantung pada laptop
    developer menyala. Diterima hanya untuk sesi uji di jaringan tim; akses permanen lewat soc-ir + VPN (task deploy).
    Login backend belum punya pembatas percobaan; itu salah satu alasan sesi tidak dibuka di Wi-Fi kampus.
11. **IP klien di audit log = IP gateway Docker** untuk semua request lewat proxy Vite (`request.client.host`). Bukti KM-8
    tetap sah (berbasis username). Task deploy: nginx + `--forwarded-allow-ips` (Keputusan 19).
12. **Submission `pending` yang tertahan tidak bisa dipulihkan dari UI** (kirim ulang atas `pending` selalu 409; hanya
    `failed` yang bisa di-retry). Pemulihan butuh admin/backend (Keputusan 17).
13. **IP yang sama bisa dikirim lagi ke MISP lewat check baru** (backend dedup per `check_id`, bukan per IP). UI hanya
    meminta konfirmasi. Keputusan tim (dedup per IP vs update event) ada di issue #29 (Keputusan 14).
14. **Draf alasan MISP hilang bila sesi (30 menit) habis** sebelum dikirim; frontend tidak menyimpan draf ke storage
    (Keputusan 3, 15).

## Rujukan dokumentasi resmi (cek ulang bila ragu, jangan menebak)

- Vite (Node 20.19+/22.12+, template `react-ts`): https://vite.dev/guide/
- Vite `server.proxy`, `server.host` (`--host`), `server.allowedHosts` (IP diterima bawaan; `true` = rawan DNS rebinding):
  https://vite.dev/config/server-options
- Tailwind CSS v4 + Vite: https://tailwindcss.com/docs/installation
- Vitest (Vite ≥ 6.4, Node ≥ 22.12): https://vitest.dev/guide/
- OWASP WSTG — Testing Browser Storage: https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/11-Client-side_Testing/12-Testing_Browser_Storage

---
name: SOC16 TI
description: Meja kerja analis untuk memeriksa reputasi satu IP. Gelap, tenang, dan jujur soal ketidakpastian.
colors:
  tanah: "#0e141b"
  panel: "#151d27"
  garis: "#64768a"
  teks: "#e6ebf1"
  teks-redup: "#9fadbd"
  aksen: "#5aa2ff"
  aksen-ink: "#06101c"
  rendah: "#d3dce6"
  rendah-bg: "#2a3644"
  perlu: "#f5d547"
  perlu-bg: "#2b2610"
  tinggi: "#ffa347"
  tinggi-bg: "#33200c"
  sangat: "#ff8a80"
  sangat-bg: "#3d1517"
  perlu-strip: "#e8c21a"
  perlu-ink: "#1a1500"
  tinggi-strip: "#f08a24"
  tinggi-ink: "#1a0f02"
  sangat-strip: "#c4262e"
  sangat-ink: "#ffffff"
  na: "#b4c0ce"
  simulasi: "#e9d5ff"
  simulasi-bg: "#2a1a40"
  simulasi-garis: "#c084fc"
  gagal: "#ff8a80"
typography:
  brand:
    fontFamily: "system-ui, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
    fontSize: "1.2rem"
    fontWeight: 600
    lineHeight: 1.35
  headline:
    fontFamily: "system-ui, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
    fontSize: "1.44rem"
    fontWeight: 600
    lineHeight: 1.25
  body:
    fontFamily: "system-ui, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  dense:
    fontFamily: "system-ui, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.45
  caption:
    fontFamily: "system-ui, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.4
  score:
    fontFamily: "system-ui, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
    fontSize: "4rem"
    fontWeight: 700
    lineHeight: 1
  identifier:
    fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.45
rounded:
  md: "6px"
  lg: "8px"
spacing:
  unit: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.aksen}"
    textColor: "{colors.aksen-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-secondary:
    textColor: "{colors.teks}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  chip:
    textColor: "{colors.teks}"
    typography: "{typography.dense}"
    rounded: "{rounded.md}"
    padding: "2px 8px"
  chip-failure:
    textColor: "{colors.gagal}"
    typography: "{typography.dense}"
    rounded: "{rounded.md}"
    padding: "2px 8px"
  input:
    backgroundColor: "{colors.tanah}"
    textColor: "{colors.teks}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  top-bar:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.teks}"
    height: "56px"
---

# Design System: SOC16 TI

## Overview

**Creative North Star: "Meja Kerja Analis di Ruang Redup"**

Antarmuka ini adalah meja kerja, bukan dasbor: satu IP per investigasi, dibaca beberapa menit oleh analis di lab atau di depan proyektor, dengan lampu diredupkan. Karena itu dunianya gelap slate (bukan hitam pekat), tenang, dan padat secukupnya. Layout, navigasi, dan kontrol sengaja standar; yang khas hanya palet, tipografi sistem, dan satu tempat berani (strip ringkasan skor).

Prinsip yang menentukan hampir semua keputusan visual: ketidakpastian tidak boleh disamarkan. Data kosong, gagal, terbatas, dan simulasi harus terlihat berbeda dari kondisi normal, dan warna tidak pernah menjadi satu-satunya pembeda: setiap status membawa teks, dan bentuknya berbeda bila warnanya sama.

Dokumen ini hanya mencatat apa yang sudah terbangun: Tahap 1 (login dan shell) dan Tahap 2 (pencarian IP, riwayat, strip ringkasan, tab bukti, rel keputusan). Bagian yang belum dibangun (kirim ke MISP dan tampilan Kiriman MISP, Tahap 3) ditandai dan bersumber dari "Keputusan desain" di `docs/tasks/TASK-03-progress.md`. Bila bertentangan dengan `docs/tasks/TASK-03-frontend-workbench.md`, dokumen TASK-03 yang menang.

**Key Characteristics:**
- Gelap slate dengan dua lapis netral (Tanah untuk area kerja, Panel untuk rel dan top bar).
- Satu aksen biru, hanya untuk elemen interaktif.
- Tidak ada hijau di seluruh antarmuka, termasuk untuk "sukses".
- Font sistem; monospace hanya untuk identifier dan data.
- Datar: kedalaman dari lapisan warna dan garis, bukan bayangan.

## Colors

Dua netral slate, satu aksen biru, dan satu set warna semantik yang diwajibkan oleh Aturan tampilan. Palet tidak pernah dipakai dekoratif.

### Primary
- **Biru Aksen** (#5aa2ff): tombol utama, tab/navigasi aktif, tautan, dan cincin fokus. Kontras 6,51:1 pada Panel. Teks di atas tombol aksen memakai **Tinta Aksen** (#06101c, 7,32:1).

### Neutral
- **Tanah** (#0e141b): latar halaman dan area bukti; juga latar kolom isian.
- **Panel** (#151d27): top bar, rel kiri/kanan, footer, kartu login.
- **Garis** (#64768a): batas kontrol (input, tombol sekunder, chip), 3,64:1 pada Panel dan 3,97:1 pada Tanah. Pembatas dekoratif memakai warna yang sama pada 35% opasitas.
- **Teks** (#e6ebf1): teks utama (14,16:1 pada Panel).
- **Teks Redup** (#9fadbd): label sekunder, keterangan, jam sesi (7,43:1 pada Panel).

### Semantik (didefinisikan di `src/index.css`)
- **Label verdict** (hanya untuk label indikasi): `rendah` #d3dce6 pada #2a3644 (abu-slate, bukan hijau); `perlu` #f5d547 pada #2b2610 (kuning); `tinggi` #ffa347 pada #33200c (oranye); `sangat` #ff8a80 pada #3d1517 (merah). Semua ≥ 6,98:1. Chip memakai pasangan ini. **Isi solid blok skor** di strip memakai pasangan lain: `perlu` #1a1500 pada #e8c21a (10,57:1), `tinggi` #1a0f02 pada #f08a24 (7,52:1), `sangat` #ffffff pada #c4262e (5,73:1); `rendah` tetap abu-slate #d3dce6 pada #2a3644 berbatas Garis.
- **N/A** (#b4c0ce): untuk skor `null`; selalu dengan batas putus-putus, tanpa isi warna.
- **Simulasi** (ungu, non-verdict): teks #e9d5ff pada #2a1a40, garis #c084fc. Jarak dari Biru Aksen ΔE76 ≈ 40; karena ungu dan biru mudah tertukar bagi penderita buta warna, bingkai tebal bergaris diagonal dan teks "SIMULASI · bukan data nyata" wajib menyertainya.
- **Gagal** (#ff8a80): status kegagalan (`failed`, 501/502, sumber `ERROR`). Pengecualian tertulis atas aturan "warna verdict hanya untuk label": bentuknya chip berbingkai tanpa isi + ikon ✕ + teks "Gagal", berbeda dari `sangat` yang chip terisi.

### Named Rules
**The One Blue Rule.** Biru Aksen hanya untuk elemen yang bisa diklik atau sedang difokus. Tidak pernah dipakai untuk status, dekorasi, atau label.

**The No Green Rule.** Tidak ada hijau di mana pun. Hijau dibaca "aman", dan tool ini tidak boleh menyatakan sebuah IP aman. Keberhasilan (mis. "Terkirim (mock)") memakai chip netral berbatas Garis. Ukurannya konkret: tidak ada token warna dengan hue 75–170° dan saturasi ≥ 15% (dijaga `frontend/design.test.ts`). `RENDAH` tidak melanggar aturan ini: ia abu-slate (teks #d3dce6, latar #2a3644; hue 212°, saturasi 24–28%), sekeluarga dengan Tanah, Panel, dan Garis. Label "rendah" berarti indikasinya rendah, bukan IP-nya aman, jadi ia tidak boleh dibuat lebih hijau, lebih terang, atau lebih "menenangkan" dari netral lain.

**The Verdict-Only Rule.** Kuning, oranye, dan merah label verdict tidak boleh dipakai untuk hal lain. Simulasi dan `pending` sengaja tidak memakai kuning.

## Typography

**UI Font:** font sistem (`system-ui`, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif)
**Mono Font:** `ui-monospace`, 'SF Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace

**Character:** Satu keluarga sans untuk semua (judul, label, tombol, data), tanpa display font. Terlihat sedikit berbeda antar perangkat; itu harga dari tanpa unduhan dan tanpa CDN (Keputusan 13a).

### Hierarchy
- **Score** (700, 4rem, 1): angka skor / "N/A" di strip ringkasan, satu-satunya teks besar.
- **Headline** (600, 1.44rem, 1.25): judul halaman (login, Kiriman MISP).
- **Brand/Title** (600, 1.2rem, 1.35): nama aplikasi di top bar dan judul panel.
- **Body** (400, 1rem, 1.5): teks utama, isian, tombol.
- **Dense** (400, 0.875rem, 1.45): chip, label formulir, baris data.
- **Caption** (400, 0.75rem, 1.4): footer dan kode di samping penjelasan. Tidak ada teks di bawah 12px.
- **Identifier** (mono, 0.875rem): IP, `misp_event_uuid`, kode status/flag/reason, `http_status`, Raw JSON.

### Named Rules
**The Mono-For-Data Rule.** Monospace hanya untuk identifier dan data yang harus disalin atau dibandingkan persis; tidak untuk "kesan teknis".

**The Tabular Numbers Rule.** Skor, cakupan, dan waktu memakai angka tabular (`tabular-nums`) agar tidak bergeser.

## Layout

Tiga panel pada ≥ 1024px: rel kiri (riwayat), tengah (bukti, fluid), rel kanan (keputusan, sticky di bawah top bar 56px). Lebar rel 272/304px pada ≥ 1280px dan 232/264px pada 1024–1279px. Di bawah 1024px panel ditumpuk bukti → keputusan → riwayat lewat CSS `order`. Urutan DOM mengikuti urutan visual desktop agar urutan Tab sama dengan urutan baca; di layar sempit Tab lebih dulu melewati riwayat (diterima, layar sempit = sentuh). Satuan spasi 4px; padding panel 16px.

Top bar `sticky` (pembungkusnya yang menempel), membungkus ke baris kedua bila sempit. Rel kiri/kanan menempel tepat di bawahnya dan berhenti di atas footer, memakai tinggi top bar dan footer yang **diukur** (`ResizeObserver` menulis `--topbar-h` dan `--footer-h`; cadangan 5rem dan 2.5rem), bukan angka keras, karena tinggi keduanya berubah oleh kolom pencarian, pesan galat, dan pembungkusan baris. Tanpa mengurangkan footer, rel yang terdorong footer di dasar halaman menyelip di bawah top bar. Halaman login: satu kartu 384px di tengah, bukan hero.

## Elevation & Depth

Datar. Kedalaman dari dua lapis netral (Tanah di bawah, Panel di atasnya) dan garis 1px; tidak ada bayangan, blur, atau efek kaca.

### Named Rules
**The Flat-By-Default Rule.** Permukaan datar saat diam. Perubahan keadaan ditandai warna, garis, atau cincin fokus, bukan bayangan.

## Shapes

Sudut membulat sedang: 6px (`rounded-md`) untuk tombol, input, chip, dan kotak pesan; 8px (`rounded-lg`) untuk kartu login. Batas 1px berwarna Garis untuk kontrol; batas kegagalan 1px berwarna Gagal. Tidak ada `border-left` tebal berwarna, tidak ada bentuk geometris dekoratif.

## Components

### Buttons
- **Shape:** sudut 6px, padding 8px × 16px, teks Body bobot 500.
- **Primary:** isi Biru Aksen, teks Tinta Aksen. Hover `brightness(1.1)`, aktif `brightness(0.95)`, nonaktif opasitas 60% dan kursor `not-allowed`.
- **Secondary:** tanpa isi, batas Garis, teks Teks. Hover berlatar Panel.
- **Fokus:** cincin 2px Biru Aksen dengan offset 2px (`:focus-visible`), berlaku untuk semua kontrol.

### Chips
- **Netral:** batas Garis, tanpa isi, teks Teks (Dense). Dipakai untuk role, "MISP: mock/live", dan keberhasilan kirim.
- **Kegagalan:** batas dan teks Gagal, tanpa isi, ikon ✕ gambar sendiri (SVG 2px) di depan teks. Dipakai untuk "API: DB error", "API: tidak terjangkau", dan galat login.

### Inputs / Fields
- **Style:** isi Tanah, batas Garis, sudut 6px, padding 8px × 12px, teks Teks; placeholder Teks Redup.
- **Focus:** cincin Biru Aksen yang sama seperti kontrol lain; caret berwarna aksen.
- **Disabled:** opasitas 60%.

### Navigation
- Tab bergaris bawah di top bar: aktif = teks Teks + garis bawah 2px Biru Aksen; tidak aktif = Teks Redup, hover Teks. `aria-current="page"` pada yang aktif. Transisi warna 150 ms.

### Strip Ringkasan
Satu-satunya area berwarna solid dan bertipografi besar. Baris pertama: IP (mono, Headline), kode `assessment_status` (mono), dan tag simulasi bila ada. Lalu blok skor 4rem berwarna verdict (min-lebar 8rem, sudut 8px), di sampingnya label indikasi + penjelasan, "Cakupan x/2", dan pengukur cakupan: satu sel bernama per sumber. Sel yang menjawab terisi Teks (teks Tanah); sel yang tidak menjawab putus-putus, memuat kode status dan `reason`. Skor `null` menampilkan "N/A" berbatas putus-putus tanpa isi warna, disertai kalimat penyebabnya. Hasil simulasi seluruh strip dibingkai tebal 4px ungu bergaris diagonal (`.simulasi-frame`, 45°, 6px/6px).

### Chips lanjutan
- **Label indikasi:** chip terisi tinta lembut + teks berwarna verdict; null = N/A putus-putus.
- **Tag simulasi:** bingkai bergaris diagonal membungkus kotak #2a1a40 berteks "SIMULASI · bukan data nyata" (Caption). Muncul di strip dan di setiap baris riwayat.
- **Flag:** chip netral berbatas Garis berisi kode monospace; penjelasannya di bawah atau di samping sebagai teks biasa.
- **Cache:** chip netral "Cache" / "Ambil baru", hanya bila sumber punya `retrieved_at`.

### Tabs
Pola WAI-ARIA: `role="tablist"`, tab aktif bergaris bawah 2px Biru Aksen, tab lain Teks Redup; roving `tabindex`, panah kiri/kanan dan Home/End berpindah dan mengaktifkan. Panel dapat difokus.

### Riwayat
Daftar tombol selebar rel: baris pertama IP (mono) dan skor/N/A (tabular), baris kedua chip label, baris ketiga waktu WIB (Caption), lalu tag simulasi. Baris terpilih berbatas Biru Aksen. Penyaring IP di atas daftar bertuliskan "Menyaring yang sudah dimuat"; "Muat lagi" hanya muncul bila yang dimuat kurang dari total.

### Kiriman MISP (rel keputusan)
Bagian "MISP" di rel kanan berurutan: status kiriman check ini (chip, `MOCK-…` mono, pengirim, waktu WIB, alasan, tag) → form (kolom Alasan dengan penghitung `n/2000 karakter, minimal 10`, kolom Tag mono, tombol primer selebar rel, catatan "Pengiriman manual. Tidak memblokir IP.") → galat/keterangan. Status memakai chip yang sudah ada: netral untuk `pending`, `mock_sent`, `sent` (dengan ✓ hanya untuk `sent`); `failed` = chip kegagalan (bingkai Gagal + ✕). Konfirmasi IP yang sama adalah kotak berbatas Garis berlatar Tanah di dalam form, dengan dua tombol selebar rel; tanpa jendela modal. Galat kirim = kotak berbingkai Gagal bergaris ✕ (`role="alert"`); keterangan netral (409 di luar daftar) = teks Redup.

### Tabel Kiriman MISP
Tabel polos di area utama: kepala Panel dengan Semibold, baris dipisah garis tipis, tujuh kolom, dalam area gulir horizontal berbingkai tipis yang dapat difokus. Teks selalu Caption/Dense (≥ 12px). Alasan panjang dipotong dengan tombol teks bergaris bawah berwarna aksen.

### Peringatan HASIL_BERBEDA
Kotak berbatas Teks tanpa warna verdict (kuning dipakai label), berisi kalimat penjelasan flag.

## Do's and Don'ts

### Do:
- **Do** menaruh teks pada setiap status; warna hanya pelengkap.
- **Do** membedakan bentuk bila dua status berbagi warna (`sangat` terisi vs `gagal` berbingkai).
- **Do** memakai font monospace untuk IP dan `misp_event_uuid`.
- **Do** memakai gerakan hanya sebagai respons aksi user, 150–200 ms, dan mematikannya di bawah `prefers-reduced-motion`.
- **Do** menjaga teks ≥ 12px dan kontras ≥ 4.5:1 untuk teks, ≥ 3:1 untuk batas kontrol.

### Don't:
- **Don't** memakai hijau, termasuk untuk "sukses" atau `RENDAH`.
- **Don't** memakai warna verdict (kuning, oranye, merah) untuk hal selain label indikasi, kecuali pengecualian Gagal yang tertulis.
- **Don't** menampilkan `null` sebagai 0, "Clean", atau "aman"; tampilkan "N/A".
- **Don't** menaruh tanda `%` pada skor gabungan; skor adalah label indikasi, bukan peluang.
- **Don't** memakai bayangan, kaca, gradien teks, atau animasi dekoratif.
- **Don't** memuat font, ikon, atau CSS dari CDN, dan jangan menambah icon pack.
- **Don't** memakai Biru Aksen untuk apa pun yang tidak bisa diklik.

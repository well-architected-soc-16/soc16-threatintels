# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Utama: empat anggota tim SOC 16 (PBL "Well Architected SOC 16", RKS-316) yang berperan sebagai analis. Situasinya:
satu alamat IP muncul dari alert atau insiden (SIEM) di lab SOC, dan analis perlu memutuskan apakah IP itu perlu
diperiksa lebih lanjut dan dicatat sebagai IoC. Peran: admin (developer tool), analyst dengan izin kirim MISP,
analyst biasa, viewer read-only.
Sekunder: dosen/penilai PBL yang melihat demo di proyektor dan memeriksa bukti (mis. uji akses negatif KM-8).

## Product Purpose
Threat Intelligence & IP Reputation Aggregator: memeriksa reputasi satu IPv4 publik dari AbuseIPDB dan VirusTotal,
menampilkan bukti per sumber beserta skor gabungan dan label indikasi untuk triase, lalu (secara manual, oleh user
berwenang, dengan alasan) mengirim IP sebagai IoC ke MISP. Berhasil bila analis bisa membaca bukti dan mengambil
keputusan dalam satu layar tanpa salah membaca data yang kosong, gagal, atau simulasi sebagai "aman".

## Positioning
Satu tempat yang menggabungkan dua sumber tanpa menyembunyikan ketidakpastian: bukti per sumber lebih penting daripada
angka; N/A tidak pernah menjadi 0; skor adalah label triase, bukan probabilitas; hasil simulasi selalu terlihat sebagai
simulasi; analis yang memutuskan (kirim MISP manual, tanpa auto-block); setiap aksi tercatat (audit) dan dibatasi RBAC
yang ditegakkan backend.

## Operating Context
- Workbench, bukan dashboard: satu IP per investigasi (input IP → bukti per sumber → keputusan → kirim MISP/salin hasil).
- Dipakai di jaringan lab/VPN; saat ini lewat laptop developer (dev server di LAN tim), nanti di VM soc-ir.
- Demo dan uji di proyektor (1280×720, 1024×768).
- Kuota sumber dipakai bersama satu API key (VirusTotal 4/menit & 500/hari, AbuseIPDB 1.000/hari); satu cek live bisa
  lebih dari 10 detik.
- Mode mock (`SUMBER_SIMULASI`) adalah default saat pengembangan dan demo; MISP masih mode mock.

## Capabilities and Constraints
- Input v1 hanya satu IPv4 publik; privat/loopback/reserved/IPv6 ditolak tanpa request keluar.
- Istilah tetap (kode backend, tampil apa adanya di samping penjelasan Indonesia): `assessment_status`
  (`COMPLETE`, `DATA_TERBATAS`, `TIDAK_TERSEDIA`, `INPUT_DITOLAK`), status sumber (`OK_SIGNAL`, `OK_NO_SIGNAL`,
  `NO_RECORD`, `INSUFFICIENT_DATA`, `ERROR`, `SKIPPED`), label `indication` (`RENDAH`, `PERLU_PEMERIKSAAN`, `TINGGI`,
  `SANGAT_TINGGI`), flag (`HASIL_BERBEDA`, `NO_VENDOR_OPINION`, `WHITELISTED`, `SUMBER_SIMULASI`).
- Label dari backend, tidak dihitung ulang di frontend; bobot/ambang/TTL tidak diubah tanpa keputusan tim.
- Tidak ada auto-block, Shodan/enrichment, force refresh, atau kelola user lewat UI pada v1.
- Token hanya di memori; tidak ada request ke CDN/pihak ketiga saat runtime; tidak ada `dangerouslySetInnerHTML`.

## Brand Commitments
- Nama: "SOC16 TI".
- Bahasa UI: Indonesia; kode backend tetap terlihat apa adanya.
- Suara: lugas dan jujur tentang batas data ("bukan jaminan aman", "bukan probabilitas", "SIMULASI · bukan data nyata").

## Evidence on Hand
- Dokumen riset tim `riset-reputasi-ip-revisi-1.1.pdf` (tidak di-commit) sebagai dasar aturan skor/label/status.
- Bukti uji API nyata 29–31 Okt 2026 (TASK-02); tabel IP demo mode mock di `docs/tasks/TASK-02-sumber-reputasi-skor.md`.
- Tidak ada pengguna eksternal, testimoni, atau metrik pemakaian; jangan dibuat-buat.

## Product Principles
1. Bukti dulu, angka kemudian: setiap skor bisa ditelusuri ke bukti per sumber.
2. Ketidakpastian tidak pernah disamarkan: kosong, gagal, terbatas, dan simulasi selalu tampil sebagai apa adanya.
3. Manusia yang memutuskan: tool memberi indikasi triase, bukan verdict otomatis atau aksi blokir.
4. Hanya yang menjawab "IP apa, bukti apa, aksi apa" yang layak ada di layar.
5. Hak akses ditegakkan backend; UI hanya mencerminkannya.

## Accessibility & Inclusion
Kontras minimal WCAG AA, fokus keyboard terlihat, label = teks + warna (tidak pernah warna saja), menghormati
`prefers-reduced-motion`, terbaca di proyektor 1280×720 dan 1024×768.

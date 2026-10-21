# SOC 316 Threat Intelligence Tools

*Threat Intelligence & IP Reputation Aggregator** untuk proyek **Well Architected SOC 16**, Project Based Learning (PBL) Semester 3, Program Studi D4 Rekayasa Keamanan Siber, Politeknik Negeri Batam.

Aplikasi ini dirancang untuk membantu analis SOC memeriksa reputasi alamat IP, menggabungkan informasi dari sumber threat intelligence eksternal, dan menyediakan konteks tambahan saat menganalisis alert atau insiden.

> **Status:** tahap perancangan dan penyiapan repository. Aplikasi belum tersedia untuk dijalankan. Fitur di bawah merupakan target pengembangan, bukan kemampuan yang sudah berfungsi.

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
| Pemeriksaan reputasi IP | Pengguna memasukkan alamat IP dan memperoleh informasi reputasinya | Direncanakan |
| Agregasi sumber eksternal | Hasil dari sumber yang dipilih disajikan dalam format yang konsisten | Direncanakan |
| Penyajian hasil | Hasil menampilkan sumber, waktu pemeriksaan, dan konteks reputasi yang tersedia | Direncanakan |
| REST API | Pemeriksaan dapat diakses melalui endpoint yang terdokumentasi | Direncanakan |
| Dokumentasi Swagger | Endpoint, parameter, respons, dan kesalahan dapat diperiksa dan diuji | Direncanakan |
| Frontend web | Pengguna dapat melakukan pemeriksaan melalui browser | Direncanakan |
| Integrasi MISP | Indikator hasil analisis dapat dikirim ke MISP | Direncanakan |

Sumber data, cara menggabungkan hasil, perhitungan skor, dan rincian endpoint belum ditetapkan. Perbedaan penilaian antar-sumber perlu tetap terlihat agar hasil dapat ditelusuri.

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
| Backend | REST API; bahasa dan framework akan dipilih berdasarkan kebutuhan | Belum ditetapkan |
| Dokumentasi API | Swagger/OpenAPI | Target luaran |
| Frontend | React, Vue, atau Svelte sesuai pilihan dalam RPP | Pilihan framework belum ditetapkan |
| Sumber reputasi | Layanan atau feed TI eksternal | Penyedia dan ketentuan akses belum ditetapkan |
| Integrasi indikator | MISP | Target integrasi |
| Penyimpanan data | Disesuaikan dengan kebutuhan aplikasi | Belum ditetapkan |
| CI/CD | GitHub Actions dengan pemeriksaan keamanan dan build | Belum dibuat |
| Deployment | Kontainer dengan pola tarik pada host tujuan, mengikuti arah RPP | Belum diimplementasikan |

Pilihan teknologi beserta versinya akan didokumentasikan setelah dievaluasi dan disepakati. Instruksi instalasi akan ditambahkan setelah kerangka aplikasi tersedia.

## Memulai

Saat ini repository digunakan untuk menyiapkan dokumentasi dan rancangan aplikasi. Untuk mengambil salinan repository privat, gunakan akun GitHub yang memiliki akses:

```bash
gh repo clone well-architected-soc-16/soc16-threatintels
cd soc16-threatintels
git status
```

Jika repository sudah di-clone, gunakan folder lokal yang sudah ada. Belum ada perintah instalasi dependensi atau menjalankan aplikasi pada tahap ini.

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

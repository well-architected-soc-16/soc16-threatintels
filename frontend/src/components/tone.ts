import type { Tone } from '../lib/format'

// Nama kelas ditulis utuh (bukan disusun dari potongan) agar terdeteksi Tailwind.
// Warna verdict hanya untuk label indikasi (Keputusan 10); RENDAH abu-slate, bukan hijau; null = N/A putus-putus.

// Chip untuk daftar/riwayat: isi tinta lembut + teks berwarna.
export const CHIP_TONE: Record<Tone, string> = {
  rendah: 'bg-rendah-bg text-rendah',
  perlu: 'bg-perlu-bg text-perlu',
  tinggi: 'bg-tinggi-bg text-tinggi',
  sangat: 'bg-sangat-bg text-sangat',
  na: 'border border-dashed border-na text-na',
}

// Blok skor di strip ringkasan: satu-satunya area berwarna solid.
export const STRIP_TONE: Record<Tone, string> = {
  rendah: 'bg-rendah-bg text-rendah border border-garis',
  perlu: 'bg-perlu-strip text-perlu-ink',
  tinggi: 'bg-tinggi-strip text-tinggi-ink',
  sangat: 'bg-sangat-strip text-sangat-ink',
  na: 'border-2 border-dashed border-na text-na',
}

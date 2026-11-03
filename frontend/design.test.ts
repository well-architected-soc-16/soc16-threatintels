import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

// Menjaga aturan desain yang bisa diukur dari token di src/index.css (DESIGN.md: The No Green Rule).
// Dibaca dengan fs (bukan `import ... ?raw`): Vitest mengosongkan isi file CSS yang diimpor, sehingga uji ini
// akan selalu gagal tanpa makna. Letaknya di akar frontend/ agar memakai tipe Node (seperti vite.config.test.ts).
const css = readFileSync(new URL('./src/index.css', import.meta.url), 'utf-8')

interface Hsl {
  name: string
  hex: string
  hue: number // derajat, 0-360
  sat: number // 0-1
}

function toHsl(name: string, hex: string): Hsl {
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const light = (max + min) / 2
  const delta = max - min
  if (delta === 0) return { name, hex, hue: 0, sat: 0 }
  const sat = delta / (1 - Math.abs(2 * light - 1))
  let hue: number
  if (max === r) hue = ((g - b) / delta) % 6
  else if (max === g) hue = (b - r) / delta + 2
  else hue = (r - g) / delta + 4
  return { name, hex, hue: (hue * 60 + 360) % 360, sat }
}

const declared = [...css.matchAll(/--color-([a-z-]+):\s*([^;]+);/g)]
const palette = declared
  .map(([, name, value]) => ({ name, value: value.trim() }))
  .filter(({ value }) => /^#[0-9a-fA-F]{6}$/.test(value))
  .map(({ name, value }) => toHsl(name, value.slice(1)))

const GREEN_HUE = { from: 75, to: 170 }
const MIN_SATURATION_FOR_HUE = 0.15 // abu hampir tanpa warna tidak dihitung "hijau"

const byName = (name: string) => {
  const found = palette.find((color) => color.name === name)
  if (!found) throw new Error(`token --color-${name} tidak ditemukan`)
  return found
}

describe('palet di src/index.css', () => {
  it('semua token warna terbaca sebagai hex 6 digit (bila format lain ditambahkan, uji ini harus diperbarui)', () => {
    expect(declared.length).toBeGreaterThanOrEqual(20)
    expect(palette).toHaveLength(declared.length)
  })

  it('The No Green Rule: tidak ada warna dalam rentang hijau (hue 75-170°)', () => {
    const green = palette.filter(
      (color) =>
        color.hue >= GREEN_HUE.from &&
        color.hue <= GREEN_HUE.to &&
        color.sat >= MIN_SATURATION_FOR_HUE,
    )
    expect(green.map((color) => `${color.name} ${color.hex}`)).toEqual([])
  })

  it('RENDAH abu-slate: sekeluarga dengan netral biru-abu, saturasi rendah, bukan hijau', () => {
    for (const name of ['rendah', 'rendah-bg']) {
      const color = byName(name)
      expect(color.hue).toBeGreaterThanOrEqual(190)
      expect(color.hue).toBeLessThanOrEqual(240)
      expect(color.sat).toBeLessThanOrEqual(0.35)
    }
  })

  it('warna verdict lain tetap kuning, oranye, dan merah (bukan hijau, bukan biru aksen)', () => {
    const perlu = byName('perlu')
    const tinggi = byName('tinggi')
    const sangat = byName('sangat')
    expect(perlu.hue).toBeGreaterThanOrEqual(40)
    expect(perlu.hue).toBeLessThan(GREEN_HUE.from)
    expect(tinggi.hue).toBeGreaterThanOrEqual(15)
    expect(tinggi.hue).toBeLessThan(45)
    expect(sangat.hue < 15 || sangat.hue > 345).toBe(true)
  })

  it('simulasi (ungu) cukup jauh dari biru aksen: selisih hue minimal 40°', () => {
    const gap = Math.abs(byName('simulasi-garis').hue - byName('aksen').hue)
    expect(Math.min(gap, 360 - gap)).toBeGreaterThanOrEqual(40)
  })
})

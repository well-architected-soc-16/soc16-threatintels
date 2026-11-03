import { describe, expect, it } from 'vitest'
import { DEMO_CHECKS, LEGACY_CHECK } from '../testing/fixtures'
import { isCheckOut, isCheckPage } from './guards'

describe('isCheckOut', () => {
  it('menerima check normal, semua IP demo, dan check lama TASK-01', () => {
    for (const check of Object.values(DEMO_CHECKS)) expect(isCheckOut(check)).toBe(true)
    expect(isCheckOut(LEGACY_CHECK)).toBe(true)
  })

  it('risk_score dan indication boleh null (N/A)', () => {
    expect(isCheckOut({ ...DEMO_CHECKS['8.8.8.8'], risk_score: null, indication: null })).toBe(true)
  })

  it.each([
    ['null', null],
    ['array', []],
    ['teks', 'x'],
    ['objek halaman riwayat', { items: [], total: 0, limit: 20, offset: 0 }],
    ['objek kosong', {}],
  ])('menolak %s', (_name, value) => {
    expect(isCheckOut(value)).toBe(false)
  })

  it('menolak bila sources/flags bukan array atau berisi elemen rusak', () => {
    const ok = DEMO_CHECKS['1.1.1.1']
    expect(isCheckOut({ ...ok, sources: null })).toBe(false)
    expect(isCheckOut({ ...ok, sources: 'x' })).toBe(false)
    expect(isCheckOut({ ...ok, flags: 'SUMBER_SIMULASI' })).toBe(false)
    expect(isCheckOut({ ...ok, flags: [1] })).toBe(false)
    expect(isCheckOut({ ...ok, sources: [null] })).toBe(false)
    expect(isCheckOut({ ...ok, sources: [{ ...ok.sources[0], evidence_summary: 'x' }] })).toBe(false)
    expect(isCheckOut({ ...ok, sources: [{ ...ok.sources[0], flags: null }] })).toBe(false)
  })

  it('menolak tipe field yang salah', () => {
    const ok = DEMO_CHECKS['1.1.1.1']
    expect(isCheckOut({ ...ok, id: '1' })).toBe(false)
    expect(isCheckOut({ ...ok, risk_score: '77' })).toBe(false)
    expect(isCheckOut({ ...ok, ip: 1 })).toBe(false)
    expect(isCheckOut({ ...ok, checked_at: null })).toBe(false)
  })
})

describe('isCheckPage', () => {
  it('menerima halaman valid dan halaman kosong', () => {
    expect(isCheckPage({ items: Object.values(DEMO_CHECKS), total: 7, limit: 20, offset: 0 })).toBe(true)
    expect(isCheckPage({ items: [], total: 0, limit: 20, offset: 0 })).toBe(true)
  })

  it('menolak bila satu item rusak, items bukan array, atau total bukan angka', () => {
    expect(isCheckPage({ items: [DEMO_CHECKS['1.1.1.1'], {}], total: 2 })).toBe(false)
    expect(isCheckPage({ items: null, total: 0 })).toBe(false)
    expect(isCheckPage({ items: [], total: '0' })).toBe(false)
    expect(isCheckPage({ items: [], total: Number.NaN })).toBe(false)
    expect(isCheckPage(DEMO_CHECKS['1.1.1.1'])).toBe(false)
  })
})

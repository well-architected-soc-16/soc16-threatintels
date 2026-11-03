import { describe, expect, it } from 'vitest'
import { DEMO_CHECKS, LEGACY_CHECK } from '../testing/fixtures'
import { makeIoc } from '../testing/fixtures'
import { isCheckOut, isCheckPage, isIocOut, isIocPage } from './guards'

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

describe('isIocOut / isIocPage', () => {
  it('menerima keempat status backend', () => {
    for (const status of ['pending', 'mock_sent', 'sent', 'failed'] as const) {
      expect(isIocOut(makeIoc({ id: 1, status }))).toBe(true)
    }
  })

  it('misp_event_uuid dan error_message boleh null', () => {
    expect(isIocOut(makeIoc({ id: 1, misp_event_uuid: null, error_message: null }))).toBe(true)
  })

  it('menolak status di luar empat nilai (tidak boleh lolos dan tampak sukses)', () => {
    expect(isIocOut({ ...makeIoc({ id: 1 }), status: 'delivered' })).toBe(false)
    expect(isIocOut({ ...makeIoc({ id: 1 }), status: 'SENT' })).toBe(false)
  })

  it.each([
    ['null', null],
    ['array', []],
    ['objek kosong', {}],
    ['halaman', { items: [], total: 0, limit: 100, offset: 0 }],
    ['tanpa reason', { ...makeIoc({ id: 1 }), reason: undefined }],
    ['tags bukan array teks', { ...makeIoc({ id: 1 }), tags: [1] }],
    ['uuid angka', { ...makeIoc({ id: 1 }), misp_event_uuid: 5 }],
    ['tanpa submitted_at', { ...makeIoc({ id: 1 }), submitted_at: undefined }],
    ['badan duplikat 409', { detail: 'x', submission_id: 8 }],
  ])('menolak %s', (_name, value) => {
    expect(isIocOut(value)).toBe(false)
  })

  it('halaman: menerima yang valid, menolak total tak hingga atau item rusak', () => {
    expect(isIocPage({ items: [makeIoc({ id: 1 })], total: 1, limit: 100, offset: 0 })).toBe(true)
    expect(isIocPage({ items: [], total: Infinity, limit: 100, offset: 0 })).toBe(false)
    expect(isIocPage({ items: [{ id: 1 }], total: 1, limit: 100, offset: 0 })).toBe(false)
    expect(isIocPage({ items: 'x', total: 0 })).toBe(false)
  })
})

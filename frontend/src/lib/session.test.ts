import { describe, expect, it } from 'vitest'
import { decodeJwtPayload, formatSessionEnd, getTokenExp } from './session'

// Membuat token uji hanya dengan API web (btoa/TextEncoder); tanda tangan tidak relevan untuk decode.
function b64url(text: string): string {
  const bytes = new TextEncoder().encode(text)
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function tokenWith(payload: unknown): string {
  return `${b64url('{"alg":"HS256","typ":"JWT"}')}.${b64url(JSON.stringify(payload))}.sig`
}

describe('decodeJwtPayload / getTokenExp', () => {
  it('membaca exp dari payload', () => {
    expect(getTokenExp(tokenWith({ sub: 'admin', exp: 1793000000 }))).toBe(
      1793000000,
    )
  })

  it.each([
    ['sisa 0 (mod 4)', 'a'.repeat(9)],
    ['sisa 2 (mod 4)', 'a'.repeat(10)],
    ['sisa 3 (mod 4)', 'a'.repeat(11)],
  ])('payload dengan panjang base64url %s tetap terbaca', (_name, filler) => {
    const payload = { sub: filler, exp: 1793000123 }
    const token = tokenWith(payload)
    const body = token.split('.')[1]
    // Memastikan skenario padding benar-benar teruji, bukan asumsi.
    expect(body.length % 4).not.toBe(1)
    expect(getTokenExp(token)).toBe(1793000123)
  })

  it('menangani karakter - dan _ milik base64url', () => {
    // Byte yang menghasilkan '+' dan '/' pada base64 biasa: payload berisi karakter non-ASCII
    // dan nilai yang membuat encoder menghasilkan '-' dan '_'.
    const payload = { sub: '???>>>~~~', exp: 1793000999, x: 'ÿþý' }
    const token = tokenWith(payload)
    const body = token.split('.')[1]
    expect(/[-_]/.test(body)).toBe(true)
    expect(getTokenExp(token)).toBe(1793000999)
  })

  it('membaca UTF-8 dengan benar', () => {
    const decoded = decodeJwtPayload(tokenWith({ sub: 'Zoë', exp: 1 }))
    expect(decoded?.sub).toBe('Zoë')
  })

  it.each([
    ['tanpa exp', { sub: 'a' }],
    ['exp berupa teks', { sub: 'a', exp: '1793000000' }],
    ['exp null', { sub: 'a', exp: null }],
  ])('mengembalikan null bila %s', (_name, payload) => {
    expect(getTokenExp(tokenWith(payload))).toBeNull()
  })

  it('mengembalikan null untuk exp tak hingga (JSON mentah, bukan JSON.stringify)', () => {
    // JSON.stringify(Infinity) menghasilkan null, jadi payload ditulis sebagai teks mentah.
    const token = `${b64url('{"alg":"HS256"}')}.${b64url('{"sub":"a","exp":1e999}')}.sig`
    expect(decodeJwtPayload(token)?.exp).toBe(Infinity)
    expect(getTokenExp(token)).toBeNull()
  })

  it.each([
    ['kosong', ''],
    ['bukan JWT', 'bukan-token'],
    ['dua bagian', 'aaa.bbb'],
    ['payload bukan base64', 'aaa.@@@@.ccc'],
    ['payload bukan JSON', `aaa.${b64url('bukan json')}.ccc`],
    ['payload array JSON', `aaa.${b64url('[1,2]')}.ccc`],
  ])('tidak melempar galat untuk token %s', (_name, token) => {
    expect(() => getTokenExp(token)).not.toThrow()
    expect(getTokenExp(token)).toBeNull()
  })
})

describe('formatSessionEnd', () => {
  it('mengubah epoch UTC ke jam WIB dengan titik dua', () => {
    // 2026-11-02T07:33:00Z = 14:33 WIB
    expect(formatSessionEnd(Date.UTC(2026, 10, 2, 7, 33, 0) / 1000)).toBe('14:33')
  })

  it('memakai zona Asia/Jakarta, bukan zona mesin', () => {
    // 2026-11-02T17:05:00Z = 00:05 WIB hari berikutnya (bukan "24:05")
    expect(formatSessionEnd(Date.UTC(2026, 10, 2, 17, 5, 0) / 1000)).toBe('00:05')
  })

  it('mengisi nol di depan jam dan menit', () => {
    // 2026-11-02T00:07:00Z = 07:07 WIB
    expect(formatSessionEnd(Date.UTC(2026, 10, 2, 0, 7, 0) / 1000)).toBe('07:07')
  })
})

import { describe, expect, it } from 'vitest'
import { makeCheck, makeIoc } from '../testing/fixtures'
import {
  appendPage,
  applyHead,
  confirmText,
  countChars,
  findSameIpElsewhere,
  findSubmissionForCheck,
  iocStatusView,
  parseTags,
  upsertSubmission,
  validateSubmission,
} from './misp'

const ids = (list: { id: number }[]) => list.map((item) => item.id)

describe('iocStatusView', () => {
  it('mock_sent tidak pernah berlabel "Terkirim ke MISP"', () => {
    const view = iocStatusView('mock_sent')
    expect(view.label).toBe('Terkirim (mock)')
    expect(view.label).not.toContain('MISP')
    expect(view.confirmed).toBe(false)
  })

  it('sent = "Terkirim ke MISP" dengan centang', () => {
    expect(iocStatusView('sent')).toMatchObject({ label: 'Terkirim ke MISP', confirmed: true, tone: 'netral' })
  })

  it('pending netral (bukan kuning), tanpa kirim ulang', () => {
    expect(iocStatusView('pending')).toMatchObject({
      label: 'Sedang diproses (pending)',
      tone: 'netral',
      retryable: false,
    })
  })

  it('failed bernada gagal dan satu-satunya yang boleh dikirim ulang', () => {
    expect(iocStatusView('failed')).toMatchObject({ label: 'Gagal', tone: 'gagal', retryable: true })
    for (const status of ['pending', 'mock_sent', 'sent'] as const) {
      expect(iocStatusView(status).retryable).toBe(false)
    }
  })

  it('hanya failed yang bernada gagal; tidak ada status yang memakai nada sukses/verdict', () => {
    const tones = (['pending', 'mock_sent', 'sent', 'failed'] as const).map((s) => iocStatusView(s).tone)
    expect(new Set(tones)).toEqual(new Set(['netral', 'gagal']))
  })
})

describe('pencocokan submission', () => {
  const items = [
    makeIoc({ id: 9, check_id: 30, ip: '118.25.6.39', status: 'mock_sent' }),
    makeIoc({ id: 8, check_id: 20, ip: '118.25.6.39', status: 'failed' }),
    makeIoc({ id: 7, check_id: 10, ip: '118.25.6.39', status: 'sent' }),
    makeIoc({ id: 6, check_id: 5, ip: '1.2.3.4', status: 'mock_sent' }),
  ]

  it('per check_id', () => {
    expect(findSubmissionForCheck(items, 20)?.id).toBe(8)
    expect(findSubmissionForCheck(items, 999)).toBeNull()
  })

  it('per IP lewat check LAIN: yang terbaru dipilih', () => {
    const check = makeCheck({ id: 40, ip: '118.25.6.39' })
    expect(findSameIpElsewhere(items, check)?.check_id).toBe(30)
  })

  it('check yang sama tidak pernah memicu konfirmasi', () => {
    const check = makeCheck({ id: 30, ip: '118.25.6.39' })
    // check 30 sendiri dilewati; yang tersisa hanya check 10 ('sent') dan 20 ('failed' dilewati)
    expect(findSameIpElsewhere(items, check)?.check_id).toBe(10)
    const only = [makeIoc({ id: 1, check_id: 30, ip: '118.25.6.39' })]
    expect(findSameIpElsewhere(only, check)).toBeNull()
  })

  it('kiriman failed atas IP yang sama tidak dihitung "sudah pernah dikirim"', () => {
    const failedOnly = [makeIoc({ id: 1, check_id: 20, ip: '9.9.9.9', status: 'failed' })]
    expect(findSameIpElsewhere(failedOnly, makeCheck({ id: 21, ip: '9.9.9.9' }))).toBeNull()
  })

  it('pending atas IP yang sama dihitung (bisa saja sedang terkirim)', () => {
    const pending = [makeIoc({ id: 1, check_id: 20, ip: '9.9.9.9', status: 'pending' })]
    expect(findSameIpElsewhere(pending, makeCheck({ id: 21, ip: '9.9.9.9' }))?.status).toBe('pending')
  })

  it('IP lain tidak cocok', () => {
    expect(findSameIpElsewhere(items, makeCheck({ id: 50, ip: '8.8.8.8' }))).toBeNull()
  })
})

describe('confirmText', () => {
  it('memuat nomor check dan status, tanpa kata "duplikat"', () => {
    for (const status of ['pending', 'mock_sent', 'sent'] as const) {
      const text = confirmText({ check_id: 12, status })
      expect(text).toBe(
        `IP ini sudah pernah dikirim lewat check #12 (${status}). Kirim lagi sebagai catatan baru?`,
      )
      expect(text.toLowerCase()).not.toContain('duplikat')
      expect(text.toLowerCase()).not.toContain('duplicate')
    }
  })
})

describe('countChars', () => {
  it('menghitung code point seperti Pydantic, bukan unit UTF-16', () => {
    expect('😀😀😀😀😀'.length).toBe(10)
    expect(countChars('😀😀😀😀😀')).toBe(5)
    expect(countChars('abc')).toBe(3)
  })
})

describe('parseTags', () => {
  it('memisah koma, memangkas, dan membuang entri kosong', () => {
    expect(parseTags('a, b ,,c,')).toEqual(['a', 'b', 'c'])
    expect(parseTags(' , ,, ')).toEqual([])
    expect(parseTags('')).toEqual([])
  })
})

describe('validateSubmission', () => {
  const ok = 'alasan sepuluh huruf'

  it('menerima alasan sah dan mengirim hasil pangkas', () => {
    expect(validateSubmission(`  ${ok}  `, 'tlp:amber, ioc')).toEqual({
      ok: true,
      reason: ok,
      tags: ['tlp:amber', 'ioc'],
    })
  })

  it('5 karakter ditolak dengan pesan inline', () => {
    const result = validateSubmission('abcde', '')
    expect(result).toEqual({
      ok: false,
      reasonError: 'Alasan minimal 10 karakter (sekarang 5).',
      tagsError: null,
    })
  })

  it('spasi tidak dihitung: 9 huruf dikelilingi spasi tetap ditolak', () => {
    expect(validateSubmission('   123456789   ', '').ok).toBe(false)
    expect(validateSubmission('1234567890', '').ok).toBe(true)
  })

  it('lima emoji = 5 karakter (ditolak), sepuluh emoji = 10 (diterima)', () => {
    expect(validateSubmission('😀😀😀😀😀', '').ok).toBe(false)
    expect(validateSubmission('😀'.repeat(10), '').ok).toBe(true)
  })

  it('batas atas 2000 karakter', () => {
    expect(validateSubmission('a'.repeat(2000), '').ok).toBe(true)
    const over = validateSubmission('a'.repeat(2001), '')
    expect(over).toMatchObject({ ok: false, reasonError: 'Alasan maksimal 2000 karakter (sekarang 2001).' })
  })

  it('tag: maksimal 20, tiap tag maksimal 64 karakter', () => {
    const twenty = Array.from({ length: 20 }, (_, i) => `t${i}`).join(',')
    expect(validateSubmission(ok, twenty).ok).toBe(true)
    expect(validateSubmission(ok, `${twenty},t20`)).toMatchObject({
      ok: false,
      tagsError: 'Maksimal 20 tag (sekarang 21).',
    })
    expect(validateSubmission(ok, 'a'.repeat(64)).ok).toBe(true)
    const tooLong = validateSubmission(ok, 'a'.repeat(65))
    expect(tooLong).toMatchObject({ ok: false })
    expect(tooLong.ok === false && tooLong.tagsError).toContain('lebih dari 64 karakter')
  })

  it('tag kosong hasil koma ganda tidak ikut terkirim', () => {
    const result = validateSubmission(ok, 'a,,b,')
    expect(result.ok && result.tags).toEqual(['a', 'b'])
  })

  it('kedua galat dilaporkan bersamaan', () => {
    const result = validateSubmission('x', 'a'.repeat(65))
    expect(result.ok).toBe(false)
    expect(!result.ok && result.reasonError).not.toBeNull()
    expect(!result.ok && result.tagsError).not.toBeNull()
  })
})

describe('daftar submission di memori', () => {
  it('applyHead memperbarui baris yang dikenal (status berubah) dan menaruh yang baru di atas', () => {
    const existing = [makeIoc({ id: 2, status: 'failed' }), makeIoc({ id: 1 })]
    const incoming = [makeIoc({ id: 3 }), makeIoc({ id: 2, status: 'mock_sent' })]
    const merged = applyHead(existing, incoming)
    expect(ids(merged)).toEqual([3, 2, 1])
    expect(merged[1].status).toBe('mock_sent')
  })

  it('applyHead tidak menghapus baris lama yang tidak ada di halaman terdepan', () => {
    const existing = [makeIoc({ id: 150 })]
    expect(ids(applyHead(existing, [makeIoc({ id: 151 })]))).toEqual([151, 150])
  })

  it('appendPage menambah di belakang dengan dedup per id', () => {
    const merged = appendPage([makeIoc({ id: 3 }), makeIoc({ id: 2 })], [makeIoc({ id: 2 }), makeIoc({ id: 1 })])
    expect(ids(merged)).toEqual([3, 2, 1])
  })

  it('upsertSubmission mengganti baris yang sama atau menaruh di paling atas', () => {
    const list = [makeIoc({ id: 2, status: 'failed' }), makeIoc({ id: 1 })]
    expect(upsertSubmission(list, makeIoc({ id: 2, status: 'mock_sent' })).map((i) => i.status)).toEqual([
      'mock_sent',
      'mock_sent',
    ])
    expect(ids(upsertSubmission(list, makeIoc({ id: 5 })))).toEqual([5, 2, 1])
  })
})

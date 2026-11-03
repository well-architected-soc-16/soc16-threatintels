import { describe, expect, it } from 'vitest'
import type { ApiFailure } from '../api/client'
import { parseCheckError, parseIocError, validationMessage } from './errors'

const http = (status: number, body: unknown): ApiFailure => ({
  ok: false,
  status,
  kind: 'http',
  body,
})

const iocOut = {
  id: 7,
  check_id: 3,
  ip: '1.1.1.1',
  reason: 'alasan cukup panjang',
  tags: [],
  status: 'failed',
  misp_event_uuid: null,
  error_message: 'Gagal mengirim ke MISP (ConnectError)',
  submitted_by: 'analyst_misp',
  submitted_at: '2026-11-02T14:00:00+07:00',
}

describe('parseCheckError', () => {
  it('422 INPUT_DITOLAK: membawa pesan dan reason_code backend', () => {
    const error = parseCheckError(
      http(422, {
        assessment_status: 'INPUT_DITOLAK',
        risk_score: null,
        reason_code: 'PRIVATE',
        message: 'Alamat privat/internal tidak diperiksa',
      }),
    )
    expect(error).toEqual({
      kind: 'input_ditolak',
      message: 'Alamat privat/internal tidak diperiksa',
      reasonCode: 'PRIVATE',
    })
  })

  it('422 standar FastAPI: dibedakan dari INPUT_DITOLAK', () => {
    const error = parseCheckError(
      http(422, {
        detail: [{ type: 'missing', loc: ['body', 'ip'], msg: 'Field required' }],
      }),
    )
    expect(error.kind).toBe('validation')
  })

  it('401, 403, 5xx, dan jaringan', () => {
    expect(parseCheckError(http(401, { detail: 'x' })).kind).toBe('unauthorized')
    expect(parseCheckError(http(403, { detail: 'Akses ditolak' }))).toEqual({
      kind: 'forbidden',
      message: 'Akses ditolak',
    })
    expect(parseCheckError(http(500, null)).kind).toBe('server')
    expect(
      parseCheckError({ ok: false, status: 0, kind: 'network', body: null }).kind,
    ).toBe('network')
  })

  it('respons 200 bukan JSON (kind invalid) dianggap galat server', () => {
    expect(
      parseCheckError({ ok: false, status: 200, kind: 'invalid', body: null }).kind,
    ).toBe('server')
  })
})

describe('backend tidak terjangkau (proxy Vite menjawab 502 tanpa badan)', () => {
  it('parseCheckError dan parseIocError memetakan ke network, bukan server', () => {
    expect(parseCheckError(http(502, null)).kind).toBe('network')
    expect(parseCheckError(http(504, null)).kind).toBe('network')
    expect(parseIocError(http(502, null)).kind).toBe('network')
  })

  it('502 DENGAN badan IocOut tetap kegagalan MISP, bukan tidak terjangkau', () => {
    expect(parseIocError(http(502, iocOut)).kind).toBe('failed')
  })

  it('500 tanpa badan tetap galat server', () => {
    expect(parseCheckError(http(500, null)).kind).toBe('server')
    expect(parseIocError(http(500, null)).kind).toBe('server')
  })
})

describe('parseIocError', () => {
  it('404 membawa detail backend', () => {
    expect(parseIocError(http(404, { detail: 'Cek tidak ditemukan' }))).toEqual({
      kind: 'not_found',
      message: 'Cek tidak ditemukan',
    })
  })

  it('409 duplikat membawa id submission', () => {
    expect(
      parseIocError(
        http(409, { detail: 'Check ini sudah pernah dikirim ke MISP', submission_id: 12 }),
      ),
    ).toEqual({
      kind: 'duplicate',
      message: 'Check ini sudah pernah dikirim ke MISP',
      submissionId: 12,
    })
  })

  it('422 detail teks (INPUT_DITOLAK / SUMBER_SIMULASI) berbeda dari validasi', () => {
    expect(
      parseIocError(
        http(422, {
          detail:
            'Cek ini berisi hasil simulasi (SUMBER_SIMULASI) dan tidak boleh dikirim ke MISP',
        }),
      ).kind,
    ).toBe('rejected')
  })

  it('422 validasi (alasan terlalu pendek) berbentuk daftar', () => {
    const error = parseIocError(
      http(422, {
        detail: [
          {
            type: 'string_too_short',
            loc: ['body', 'reason'],
            msg: 'String should have at least 10 characters',
            input: 'pendek',
            ctx: { min_length: 10 },
          },
        ],
      }),
    )
    expect(error).toEqual({
      kind: 'validation',
      message: 'Input tidak valid: reason.',
    })
  })

  it('501 dan 502 membawa IocOut berstatus failed', () => {
    for (const status of [501, 502]) {
      const error = parseIocError(http(status, iocOut))
      expect(error.kind).toBe('failed')
      if (error.kind === 'failed') {
        expect(error.httpStatus).toBe(status)
        expect(error.submission.status).toBe('failed')
        expect(error.submission.error_message).toContain('Gagal')
      }
    }
  })

  it('500 tanpa badan IocOut dianggap galat server', () => {
    expect(parseIocError(http(500, null)).kind).toBe('server')
  })

  it('403 memakai pesan tetap dan 401 menandai sesi', () => {
    expect(parseIocError(http(403, { detail: 'Akses ditolak' }))).toEqual({
      kind: 'forbidden',
      message: 'Akun ini tidak berhak mengirim ke MISP',
    })
    expect(parseIocError(http(401, null)).kind).toBe('unauthorized')
  })
})

describe('validationMessage', () => {
  it('tidak pernah menyalin field input atau ctx (bisa memantulkan password)', () => {
    const message = validationMessage({
      detail: [
        {
          type: 'missing',
          loc: ['body', 'password'],
          msg: 'Field required',
          input: { username: 'admin', password: 'RAHASIA-JANGAN-TAMPIL' },
          ctx: { nilai: 'RAHASIA-JANGAN-TAMPIL' },
        },
      ],
    })
    expect(message).toBe('Input tidak valid: password.')
    expect(message).not.toContain('RAHASIA')
  })

  it('bentuk tak dikenal menghasilkan pesan umum', () => {
    expect(validationMessage(null)).toBe('Input tidak valid.')
    expect(validationMessage({ detail: 'teks' })).toBe('Input tidak valid.')
    expect(validationMessage({ detail: [] })).toBe('Input tidak valid.')
  })
})

import { describe, expect, it } from 'vitest'
import { canCheck, canSendMisp } from './can'

const user = (
  role: 'admin' | 'analyst' | 'viewer',
  can_send_misp: boolean,
  is_active = true,
) => ({ role, can_send_misp, is_active })

describe('canCheck', () => {
  it('admin dan analyst boleh membuat pengecekan', () => {
    expect(canCheck(user('admin', false))).toBe(true)
    expect(canCheck(user('analyst', false))).toBe(true)
  })

  it('viewer, tanpa user, dan akun nonaktif tidak boleh', () => {
    expect(canCheck(user('viewer', false))).toBe(false)
    expect(canCheck(user('viewer', true))).toBe(false)
    expect(canCheck(null)).toBe(false)
    expect(canCheck(user('admin', true, false))).toBe(false)
  })
})

describe('canSendMisp', () => {
  it('admin boleh walau can_send_misp=false', () => {
    expect(canSendMisp(user('admin', false))).toBe(true)
  })

  it('analyst hanya bila can_send_misp=true', () => {
    expect(canSendMisp(user('analyst', true))).toBe(true)
    expect(canSendMisp(user('analyst', false))).toBe(false)
  })

  it('viewer tidak pernah boleh, termasuk bila can_send_misp=true', () => {
    expect(canSendMisp(user('viewer', true))).toBe(false)
    expect(canSendMisp(user('viewer', false))).toBe(false)
  })

  it('tanpa user atau akun nonaktif tidak boleh', () => {
    expect(canSendMisp(null)).toBe(false)
    expect(canSendMisp(user('analyst', true, false))).toBe(false)
  })
})

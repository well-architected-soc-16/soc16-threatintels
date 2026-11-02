import { describe, expect, it } from 'vitest'
import config from './vite.config.ts'

describe('konfigurasi dev server', () => {
  it('meneruskan /api ke backend lokal tanpa rewrite', () => {
    const proxy = config.server?.proxy ?? {}
    expect(proxy['/api']).toEqual({
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
    })
  })

  it('tidak membuka host ke LAN secara bawaan (hanya lewat dev:lan)', () => {
    expect(config.server?.host).toBeUndefined()
  })

  it('tidak mengisi allowedHosts: true (celah DNS rebinding)', () => {
    expect(config.server?.allowedHosts).not.toBe(true)
  })
})

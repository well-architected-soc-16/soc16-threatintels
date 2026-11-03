import { describe, expect, it } from 'vitest'
import { makeCheck } from '../testing/fixtures'
import { filterHistory, hasMore, mergeHistory, prependCheck } from './history'

const c = (id: number, ip = `10.0.0.${id}`) => makeCheck({ id, ip })
const ids = (list: { id: number }[]) => list.map((x) => x.id)

describe('mergeHistory', () => {
  it('menambah di belakang dan membuang duplikat per id (offset bergeser)', () => {
    const existing = [c(5), c(4), c(3)]
    const incoming = [c(3), c(2), c(1)] // baris 3 bergeser masuk lagi karena ada check baru
    expect(ids(mergeHistory(existing, incoming))).toEqual([5, 4, 3, 2, 1])
  })

  it('duplikat di dalam incoming sendiri juga dibuang', () => {
    expect(ids(mergeHistory([], [c(2), c(2), c(1)]))).toEqual([2, 1])
  })

  it('tidak mengubah masukan', () => {
    const existing = Object.freeze([c(2)]) as readonly ReturnType<typeof c>[]
    const incoming = Object.freeze([c(1)]) as readonly ReturnType<typeof c>[]
    expect(() => mergeHistory(existing, incoming)).not.toThrow()
    expect(existing).toHaveLength(1)
  })
})

describe('prependCheck', () => {
  it('check baru masuk paling atas', () => {
    expect(ids(prependCheck([c(2), c(1)], c(3)))).toEqual([3, 2, 1])
  })

  it('dedup per id, bukan per IP: cek ulang IP yang sama membuat baris baru', () => {
    const history = [c(2, '8.8.8.8'), c(1, '8.8.8.8')]
    const result = prependCheck(history, c(3, '8.8.8.8'))
    expect(ids(result)).toEqual([3, 2, 1])
    expect(result.filter((x) => x.ip === '8.8.8.8')).toHaveLength(3)
  })

  it('id yang sama tidak menggandakan baris', () => {
    expect(ids(prependCheck([c(2), c(1)], c(1)))).toEqual([1, 2])
  })
})

describe('filterHistory', () => {
  const history = [c(1, '1.1.1.1'), c(2, '8.8.8.8'), c(3, '208.67.222.222')]

  it('menyaring substring IP, tanpa membedakan huruf besar kecil', () => {
    expect(ids(filterHistory(history, '8.8'))).toEqual([2])
    expect(ids(filterHistory(history, '.222'))).toEqual([3])
  })

  it('kosong atau spasi saja = semua', () => {
    expect(filterHistory(history, '')).toHaveLength(3)
    expect(filterHistory(history, '   ')).toHaveLength(3)
  })

  it('spasi di sekitar kueri diabaikan; tak cocok = kosong', () => {
    expect(ids(filterHistory(history, ' 1.1 '))).toEqual([1])
    expect(filterHistory(history, 'zzz')).toEqual([])
  })
})

describe('hasMore', () => {
  it('"Muat lagi" hanya bila yang dimuat kurang dari total', () => {
    expect(hasMore(20, 57)).toBe(true)
    expect(hasMore(57, 57)).toBe(false)
    expect(hasMore(58, 57)).toBe(false)
    expect(hasMore(0, 0)).toBe(false)
    expect(hasMore(0, null)).toBe(false)
  })
})

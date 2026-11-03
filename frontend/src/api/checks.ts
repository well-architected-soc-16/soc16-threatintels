import type { ApiClient, ApiResult } from './client'
import type { CheckOut, CheckPage } from './types'

export const PAGE_SIZE = 20

export function listChecks(
  api: ApiClient,
  offset: number,
  limit: number = PAGE_SIZE,
): Promise<ApiResult<CheckPage>> {
  return api.get<CheckPage>(`/checks?limit=${limit}&offset=${offset}`)
}

export function getCheck(
  api: ApiClient,
  id: number,
): Promise<ApiResult<CheckOut>> {
  return api.get<CheckOut>(`/checks/${id}`)
}

// POST /checks sinkron: satu respons, bisa sampai belasan detik pada mode live.
export function createCheck(
  api: ApiClient,
  ip: string,
): Promise<ApiResult<CheckOut>> {
  return api.post<CheckOut>('/checks', { json: { ip } })
}

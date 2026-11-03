import type { ApiClient, ApiResult } from './client'
import type { IocOut, IocPage } from './types'

// Dipakai untuk pencocokan status per check/IP dan untuk tabel Kiriman MISP. Maksimum yang diizinkan backend.
export const IOC_PAGE_SIZE = 100

export function listIocs(
  api: ApiClient,
  offset: number,
  limit: number = IOC_PAGE_SIZE,
): Promise<ApiResult<IocPage>> {
  return api.get<IocPage>(`/iocs?limit=${limit}&offset=${offset}`)
}

export interface IocSubmitBody {
  check_id: number
  reason: string
  tags: string[]
}

// 201 baru, 200 kirim ulang dari `failed`. 409/422/501/502 datang sebagai kegagalan (lihat parseIocError).
export function submitIoc(
  api: ApiClient,
  body: IocSubmitBody,
): Promise<ApiResult<IocOut>> {
  return api.post<IocOut>('/iocs/misp', { json: body })
}

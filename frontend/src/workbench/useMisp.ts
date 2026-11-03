import { useEffect, useState, useSyncExternalStore } from 'react'
import type { ApiClient } from '../api/client'
import { createMispStore, type MispState, type MispStore } from './mispStore'

export function useMisp(api: ApiClient): [MispState, MispStore] {
  const [store] = useState(() => createMispStore(api))
  const state = useSyncExternalStore(store.subscribe, store.getState, store.getState)

  useEffect(() => {
    void store.loadInitial()
  }, [store])

  return [state, store]
}

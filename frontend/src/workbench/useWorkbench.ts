import { useEffect, useState, useSyncExternalStore } from 'react'
import type { ApiClient } from '../api/client'
import { createWorkbenchStore, type WorkbenchState, type WorkbenchStore } from './store'

export function useWorkbench(api: ApiClient): [WorkbenchState, WorkbenchStore] {
  const [store] = useState(() => createWorkbenchStore(api))
  const state = useSyncExternalStore(store.subscribe, store.getState, store.getState)

  useEffect(() => {
    void store.loadInitial()
  }, [store])

  return [state, store]
}

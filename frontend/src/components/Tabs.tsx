import { useRef, type KeyboardEvent } from 'react'
import { panelId, tabId } from './tabIds'

export interface TabDef {
  id: string
  label: string
}

interface TabsProps {
  tabs: readonly TabDef[]
  active: string
  onChange: (id: string) => void
  prefix: string
  label: string
}

// Pola WAI-ARIA tabs: roving tabindex, panah kiri/kanan, Home/End; aktivasi otomatis saat fokus berpindah.
export function Tabs({ tabs, active, onChange, prefix, label }: TabsProps) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next: number
    switch (event.key) {
      case 'ArrowRight':
        next = (index + 1) % tabs.length
        break
      case 'ArrowLeft':
        next = (index - 1 + tabs.length) % tabs.length
        break
      case 'Home':
        next = 0
        break
      case 'End':
        next = tabs.length - 1
        break
      default:
        return
    }
    event.preventDefault()
    onChange(tabs[next].id)
    refs.current[next]?.focus()
  }

  return (
    <div role="tablist" aria-label={label} className="flex flex-wrap gap-1 border-b border-garis/35">
      {tabs.map((tab, index) => {
        const selected = tab.id === active
        return (
          <button
            key={tab.id}
            ref={(element) => {
              refs.current[index] = element
            }}
            id={tabId(prefix, tab.id)}
            type="button"
            role="tab"
            aria-selected={selected}
            aria-controls={panelId(prefix, tab.id)}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            className={`-mb-px border-b-2 px-3 py-2 text-isi transition-colors duration-150 ${
              selected
                ? 'border-aksen text-teks'
                : 'border-transparent text-redup hover:text-teks'
            }`}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}

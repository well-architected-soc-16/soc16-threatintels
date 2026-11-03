import { useEffect, type RefObject } from 'react'

// Rel kiri/kanan menempel tepat di bawah top bar. Tingginya berubah (kolom pencarian, pesan galat, baris
// membungkus di layar sempit), jadi diukur dan ditulis ke variabel CSS --topbar-h, bukan angka keras.
export function useTopBarHeight(
  host: RefObject<HTMLElement | null>,
  bar: RefObject<HTMLElement | null>,
): void {
  useEffect(() => {
    const hostEl = host.current
    const barEl = bar.current
    if (!hostEl || !barEl) return
    const apply = () => hostEl.style.setProperty('--topbar-h', `${barEl.offsetHeight}px`)
    apply()
    if (typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(apply)
    observer.observe(barEl)
    return () => observer.disconnect()
  }, [host, bar])
}

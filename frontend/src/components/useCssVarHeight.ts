import { useEffect, type RefObject } from 'react'

// Rel kiri/kanan menempel di bawah top bar dan berhenti di atas footer. Kedua tinggi itu berubah (kolom pencarian,
// pesan galat, teks membungkus di layar sempit), jadi diukur dan ditulis ke variabel CSS pada elemen `host`,
// bukan angka keras. Tanpa memperhitungkan footer, rel yang terdorong footer di dasar halaman menyelip di
// bawah top bar sehingga judulnya tertutup (ditemukan lewat uji gulir di peramban).
export function useCssVarHeight(
  host: RefObject<HTMLElement | null>,
  target: RefObject<HTMLElement | null>,
  name: `--${string}`,
): void {
  useEffect(() => {
    const hostEl = host.current
    const targetEl = target.current
    if (!hostEl || !targetEl) return
    const apply = () => hostEl.style.setProperty(name, `${targetEl.offsetHeight}px`)
    apply()
    if (typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(apply)
    observer.observe(targetEl)
    return () => observer.disconnect()
  }, [host, target, name])
}

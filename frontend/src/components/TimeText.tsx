import { formatTime } from '../lib/format'

// Waktu WIB yang sudah dirapikan; string ISO aslinya tampil sebagai tooltip (Keputusan 20) dan di tab Raw JSON.
// <time>/title hanya dipakai bila formatTime benar-benar mengonversi (+07:00). String lain tampil mentah.
export function TimeText({ iso }: { iso: string | null | undefined }) {
  const text = formatTime(iso)
  if (typeof iso === 'string' && text !== iso) {
    return (
      <time dateTime={iso} title={iso}>
        {text}
      </time>
    )
  }
  return <>{text}</>
}

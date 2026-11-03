import { useEffect, useRef, useState, type RefObject } from 'react'
import type { CheckOut, IocOut } from '../api/types'
import {
  PENDING_HINT,
  REASON_MAX,
  REASON_MIN,
  confirmText,
  countChars,
  findSameIpElsewhere,
  findSubmissionForCheck,
  iocStatusView,
  validateSubmission,
} from '../lib/misp'
import type { MispState, SendIssue } from '../workbench/mispStore'
import { IocStatusChip } from './Badges'
import { Button } from './Button'
import { Chip } from './Chip'
import { ExpandableText } from './ExpandableText'
import { IconX } from './Icon'
import { TimeText } from './TimeText'

const FIELD =
  'w-full rounded-md border border-garis bg-tanah px-3 py-2 text-padat text-teks placeholder:text-redup read-only:opacity-60'

function Problem({ id, children }: { id?: string; children: string }) {
  return (
    <p id={id} className="mt-1 flex items-start gap-1.5 text-padat text-gagal">
      <IconX className="mt-0.5 size-3.5 shrink-0" />
      <span>{children}</span>
    </p>
  )
}

// ---------- Kiriman yang sudah ada ----------

export function SubmissionView({ submission }: { submission: IocOut }) {
  const view = iocStatusView(submission.status)
  return (
    <div className="space-y-1.5">
      <div role="status">
        <IocStatusChip status={submission.status} />
      </div>
      {submission.misp_event_uuid !== null && (
        <p className="text-padat">
          Event: <code className="font-mono text-kecil [overflow-wrap:anywhere]">{submission.misp_event_uuid}</code>
        </p>
      )}
      <p className="text-padat text-redup">
        Oleh <span className="text-teks">{submission.submitted_by}</span>,{' '}
        <TimeText iso={submission.submitted_at} />
      </p>
      {submission.status === 'pending' && <p className="text-padat text-redup">{PENDING_HINT}</p>}
      {view.tone === 'gagal' && submission.error_message !== null && (
        <p className="text-padat text-gagal [overflow-wrap:anywhere]">{submission.error_message}</p>
      )}
      <p className="text-padat">
        <span className="text-redup">Alasan: </span>
        <ExpandableText text={submission.reason} />
      </p>
      {submission.tags.length > 0 && (
        <p className="flex flex-wrap items-center gap-1 text-padat">
          <span className="text-redup">Tag:</span>
          {submission.tags.map((tag, index) => (
            <Chip key={`${index}-${tag}`} mono>
              {tag}
            </Chip>
          ))}
        </p>
      )}
    </div>
  )
}

// ---------- Form ----------

interface FormViewProps {
  mode: 'new' | 'retry'
  reason: string
  tagsText: string
  onReason: (value: string) => void
  onTags: (value: string) => void
  reasonError: string | null
  tagsError: string | null
  // Kiriman sebelumnya atas IP yang sama lewat check lain; memicu konfirmasi inline (Keputusan 14, 21).
  previous: IocOut | null
  confirming: boolean
  sending: boolean
  issue: SendIssue | null
  onSend: () => void
  onConfirm: () => void
  onCancel: () => void
  reasonRef?: RefObject<HTMLTextAreaElement | null>
  tagsRef?: RefObject<HTMLInputElement | null>
}

// Tampilan murni (semua keadaan lewat props) agar bisa diuji dengan render statis.
export function MispFormView({
  mode,
  reason,
  tagsText,
  onReason,
  onTags,
  reasonError,
  tagsError,
  previous,
  confirming,
  sending,
  issue,
  onSend,
  onConfirm,
  onCancel,
  reasonRef,
  tagsRef,
}: FormViewProps) {
  const locked = sending || confirming
  const showConfirm = confirming && previous !== null
  const confirmRef = useRef<HTMLDivElement>(null)
  const submitRef = useRef<HTMLButtonElement>(null)
  const wasConfirming = useRef(false)

  // Tombol yang diklik hilang saat panel konfirmasi muncul (dan sebaliknya): pindahkan fokus supaya tidak
  // jatuh ke <body> bagi pengguna keyboard dan pembaca layar.
  useEffect(() => {
    if (showConfirm) confirmRef.current?.focus()
    else if (wasConfirming.current) submitRef.current?.focus()
    wasConfirming.current = showConfirm
  }, [showConfirm])
  const length = countChars(reason.trim())
  const sendLabel = sending ? 'Mengirim…' : mode === 'retry' ? 'Kirim ulang' : 'Kirim ke MISP'

  return (
    <form
      method="post"
      noValidate
      onSubmit={(event) => {
        // Pertama: submit bawaan peramban akan menaruh isian di URL.
        event.preventDefault()
        if (!showConfirm) onSend()
      }}
      className="space-y-2.5"
    >
      <div>
        <label htmlFor="misp-reason" className="mb-1 block text-padat">
          Alasan <span className="text-redup">(wajib)</span>
        </label>
        <textarea
          id="misp-reason"
          ref={reasonRef}
          rows={4}
          value={reason}
          readOnly={locked}
          onChange={(event) => onReason(event.target.value)}
          aria-invalid={reasonError !== null}
          aria-describedby={`misp-reason-count${reasonError !== null ? ' misp-reason-error' : ''}`}
          className={FIELD}
        />
        <p id="misp-reason-count" className="mt-1 tabular-nums text-kecil text-redup">
          {length}/{REASON_MAX} karakter, minimal {REASON_MIN}
        </p>
        {reasonError !== null && <Problem id="misp-reason-error">{reasonError}</Problem>}
      </div>

      <div>
        <label htmlFor="misp-tags" className="mb-1 block text-padat">
          Tag <span className="text-redup">(opsional)</span>
        </label>
        <input
          id="misp-tags"
          ref={tagsRef}
          type="text"
          autoComplete="off"
          spellCheck={false}
          value={tagsText}
          readOnly={locked}
          onChange={(event) => onTags(event.target.value)}
          aria-invalid={tagsError !== null}
          aria-describedby={`misp-tags-note${tagsError !== null ? ' misp-tags-error' : ''}`}
          className={`${FIELD} font-mono`}
        />
        <p id="misp-tags-note" className="mt-1 text-kecil text-redup">
          Pisahkan dengan koma. Maksimal 20 tag.
        </p>
        {tagsError !== null && <Problem id="misp-tags-error">{tagsError}</Problem>}
      </div>

      {showConfirm ? (
        <div
          ref={confirmRef}
          tabIndex={-1}
          role="group"
          aria-label="Konfirmasi kirim ulang"
          className="rounded-md border border-garis bg-tanah p-3"
        >
          <p className="text-padat">{confirmText(previous)}</p>
          <div className="mt-2 flex flex-col gap-2">
            <Button onClick={onConfirm} disabled={sending} className="w-full">
              {sending ? 'Mengirim…' : 'Kirim lagi sebagai catatan baru'}
            </Button>
            <Button variant="secondary" onClick={onCancel} disabled={sending} className="w-full">
              Batal
            </Button>
          </div>
        </div>
      ) : (
        <Button ref={submitRef} type="submit" disabled={sending} className="w-full">
          {sendLabel}
        </Button>
      )}

      <p className="text-kecil text-redup">Pengiriman manual. Tidak memblokir IP.</p>

      {issue !== null &&
        (issue.kind === 'error' ? (
          <p
            role="alert"
            className="flex items-start gap-1.5 rounded-md border border-gagal px-2 py-1 text-padat text-gagal"
          >
            <IconX className="mt-0.5 size-3.5 shrink-0" />
            <span className="[overflow-wrap:anywhere]">{issue.message}</span>
          </p>
        ) : (
          <p role="status" className="text-padat text-redup">
            {issue.message}
          </p>
        ))}
    </form>
  )
}

interface MispFormProps {
  mode: 'new' | 'retry'
  initialReason: string
  initialTags: string
  previous: IocOut | null
  sending: boolean
  issue: SendIssue | null
  onSubmit: (reason: string, tags: string[]) => Promise<boolean>
  onEdit: () => void
}

function MispForm({
  mode,
  initialReason,
  initialTags,
  previous,
  sending,
  issue,
  onSubmit,
  onEdit,
}: MispFormProps) {
  const [reason, setReason] = useState(initialReason)
  const [tagsText, setTagsText] = useState(initialTags)
  const [attempted, setAttempted] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const reasonRef = useRef<HTMLTextAreaElement>(null)
  const tagsRef = useRef<HTMLInputElement>(null)

  // Pesan muncul setelah klik pertama, lalu mengikuti isian.
  const validation = validateSubmission(reason, tagsText)
  const reasonError = attempted && !validation.ok ? validation.reasonError : null
  const tagsError = attempted && !validation.ok ? validation.tagsError : null

  function send() {
    setAttempted(true)
    if (!validation.ok) {
      // Tombol tetap aktif; kolom pertama yang bermasalah menerima fokus.
      if (validation.reasonError !== null) reasonRef.current?.focus()
      else tagsRef.current?.focus()
      return
    }
    if (previous !== null && !confirming) {
      setConfirming(true)
      return
    }
    void onSubmit(validation.reason, validation.tags).finally(() => setConfirming(false))
  }

  return (
    <MispFormView
      mode={mode}
      reason={reason}
      tagsText={tagsText}
      onReason={(value) => {
        setReason(value)
        onEdit()
      }}
      onTags={(value) => {
        setTagsText(value)
        onEdit()
      }}
      reasonError={reasonError}
      tagsError={tagsError}
      previous={previous}
      confirming={confirming}
      sending={sending}
      issue={issue}
      onSend={send}
      onConfirm={send}
      onCancel={() => setConfirming(false)}
      reasonRef={reasonRef}
      tagsRef={tagsRef}
    />
  )
}

// ---------- Panel di rel keputusan ----------

interface MispPanelProps {
  check: CheckOut
  misp: Pick<MispState, 'items' | 'status' | 'error' | 'sendingIds' | 'issues'>
  // Teks pengganti form bila akun tidak boleh mengirim (null = boleh).
  deniedText: string | null
  onSubmit: (checkId: number, reason: string, tags: string[]) => Promise<boolean>
  onClearIssue: (checkId: number) => void
  onRetryLoad: () => void
}

// Urutan keputusan: (1) status kiriman termuat? (2) check ini sudah punya kiriman → tampilkan, siapa pun
// yang melihat; hanya `failed` yang boleh dikirim ulang. (3) akun tidak berhak → teks izin. (4) form.
// Check simulasi ditangani pemanggil (DecisionRail) sebelum panel ini.
export function MispPanel({ check, misp, deniedText, onSubmit, onClearIssue, onRetryLoad }: MispPanelProps) {
  if (misp.status === 'idle' || misp.status === 'loading') {
    return (
      <p role="status" className="text-redup">
        Memuat status kiriman…
      </p>
    )
  }
  if (misp.status === 'error') {
    // Form tidak ditampilkan: tanpa daftar kiriman, konfirmasi "IP sudah pernah dikirim" akan terlewat diam-diam.
    return (
      <div className="space-y-2">
        <p
          role="alert"
          className="flex items-start gap-1.5 rounded-md border border-gagal px-2 py-1 text-padat text-gagal"
        >
          <IconX className="mt-0.5 size-3.5 shrink-0" />
          <span>{misp.error ?? 'Status kiriman MISP tidak dapat dimuat.'}</span>
        </p>
        <Button variant="secondary" onClick={onRetryLoad} className="w-full">
          Coba lagi
        </Button>
      </div>
    )
  }

  const submission = findSubmissionForCheck(misp.items, check.id)
  const retryable = submission !== null && iocStatusView(submission.status).retryable
  const showForm = deniedText === null && (submission === null || retryable)
  const issue = misp.issues[check.id] ?? null

  return (
    <div className="space-y-3">
      {submission !== null && <SubmissionView submission={submission} />}
      {showForm ? (
        <MispForm
          key={check.id}
          mode={submission === null ? 'new' : 'retry'}
          initialReason={submission?.reason ?? ''}
          initialTags={submission?.tags.join(', ') ?? ''}
          previous={findSameIpElsewhere(misp.items, check)}
          sending={misp.sendingIds.includes(check.id)}
          issue={issue}
          onSubmit={(reason, tags) => onSubmit(check.id, reason, tags)}
          onEdit={() => onClearIssue(check.id)}
        />
      ) : (
        <>
          {submission === null && deniedText !== null && <p>{deniedText}</p>}
          {submission !== null && deniedText !== null && retryable && (
            <p className="text-redup">{deniedText}</p>
          )}
          {issue !== null && <p className="text-padat text-redup">{issue.message}</p>}
        </>
      )}
    </div>
  )
}

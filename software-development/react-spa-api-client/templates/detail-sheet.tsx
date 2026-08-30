/**
 * Controlled right-side detail Sheet for a record fetched by id ("360 view").
 *
 * Conventions (the load-bearing ones):
 * - Parent owns `selectedId: string | null`; the sheet derives `open` from it.
 *   No separate open boolean — nothing to drift out of sync.
 * - Fetch effect keyed on the id, with a `cancelled` guard: a fast close must
 *   not toast a stale error or write one record's data over the next one's.
 * - Radix requires an accessible title — render an sr-only SheetTitle while
 *   the profile is still loading.
 * - Header stays fixed; only the body scrolls.
 * - Status badges reuse the dashboard's existing tone vocabulary — copy the
 *   page's STATUS_TONES map, don't invent new colors.
 *
 * Adapt: swap the Profile type, the fetch call, and the section markup.
 */
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { api, errorMessage, fmtDate, fmtMoney } from '@/lib/api'
import type { MemberProfile } from '@/lib/api'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'

// Mirror the dashboard's existing status→tone map. Light backgrounds
// (amber, stone-400) need text-stone-950 for contrast.
const TONES: Record<string, string> = {
  confirmed: 'bg-green-700',
  waitlist: 'bg-amber-600 text-stone-950',
  declined: 'bg-red-700',
  pending: 'bg-stone-400 text-stone-950',
  ready: 'bg-amber-600 text-stone-950',
  delivered: 'bg-green-700',
  requested: 'bg-amber-600 text-stone-950',
  seated: 'bg-green-700',
  cancelled: 'bg-red-700',
  no_show: 'bg-stone-500 text-stone-950',
}

function ToneBadge({ status }: { status: string }) {
  return (
    <Badge className={TONES[status] ?? 'bg-stone-500 text-stone-950'}>
      {status.replace('_', ' ')}
    </Badge>
  )
}

interface Props {
  recordId: string | null // null = closed
  onClose: () => void
  onSaved?: () => void // parent list refresh after an in-sheet mutation
}

export function RecordDetailSheet({ recordId, onClose, onSaved }: Props) {
  const [profile, setProfile] = useState<MemberProfile | null>(null)

  useEffect(() => {
    if (!recordId) {
      setProfile(null)
      return
    }
    let cancelled = false
    setProfile(null)
    api.members
      .profile(recordId)
      .then(p => !cancelled && setProfile(p))
      .catch(err => !cancelled && toast.error(errorMessage(err)))
    return () => {
      cancelled = true
    }
  }, [recordId])

  const m = profile?.member

  // Derived stats come from the fetched collections — no extra endpoint.
  const lifetimeCents =
    profile?.orders.filter(o => o.paid).reduce((sum, o) => sum + o.totalCents, 0) ?? 0

  return (
    <Sheet open={!!recordId} onOpenChange={o => !o && onClose()}>
      <SheetContent side="right" className="gap-0 overflow-hidden sm:max-w-2xl">
        <SheetHeader className="border-b p-6">
          {m ? (
            <>
              <SheetTitle className="font-serif text-2xl">
                {m.name}
                {m.partnerName ? ` & ${m.partnerName}` : ''}
              </SheetTitle>
              <SheetDescription>
                Joined {fmtDate(m.joinedAt)} · lifetime {fmtMoney(lifetimeCents)}
              </SheetDescription>
            </>
          ) : (
            // Radix needs a title for a11y even before data lands.
            <SheetTitle className="sr-only">Record detail</SheetTitle>
          )}
        </SheetHeader>

        {!profile ? (
          <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
            <Spinner className="h-4 w-4" /> Loading…
          </div>
        ) : (
          <div className="flex-1 space-y-8 overflow-y-auto p-6">
            {/* One <section> per collection (orders, signups, deliveries,
                reservations…), each with:
                - a heading with a count chip
                - an italic empty state when the list is empty
                - card rows (rounded-lg border bg-card p-3, subtle
                  hover:border-primary/40) with a ToneBadge status chip
                In-sheet mutations (e.g. saving staff notes via
                api.members.update) toast on success and call onSaved?.()
                so the parent table refreshes too. */}
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}

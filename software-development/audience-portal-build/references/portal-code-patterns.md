# Portal code patterns (known-good examples)

Concrete, reusable patterns from a real member-portal build (Pampa Wine Club, React + react-router + scoped-CSS design system). Adapt names/paths to the target project.

## 1. Proof/attachment photo behind an HttpOnly session cookie

A plain `<img src>` won't send the session cookie. Fetch the blob with credentials, mint an object URL, revoke on unmount:

```tsx
function ProofModal({ delivery, onClose }: { delivery: MemberDelivery; onClose: () => void }) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    let objectUrl: string | null = null
    fetch(api.deliveries.photoUrl(delivery.id), { credentials: 'include' })
      .then(res => {
        if (!res.ok) throw new Error('Could not load the proof photo')
        return res.blob()
      })
      .then(blob => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .catch(err => { if (!cancelled) setError(errorMessage(err)) })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [delivery.id])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="pp-modal" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="box" onClick={e => e.stopPropagation()}>
        <button type="button" className="close" onClick={onClose} aria-label="Close">…</button>
        {url ? <img src={url} alt={`Proof of delivery — ${fmtMonth(delivery.month)}`} />
          : error ? <div className="loading">{error}</div>
          : <div className="loading"><div className="ring" />Loading photo</div>}
      </div>
    </div>
  )
}
```

## 2. Scoped brand stylesheet — sibling scope, identical tokens

If the app already has a scoped brand CSS (e.g. `.pampa-home`), create a sibling file scoped under a new root class that re-declares the SAME token block so the portal feels like the same product. Every rule is prefixed with the scope so nothing leaks:

```css
.pampa-portal {
  --crimson: #c8102e;
  --crimson-dark: #9c0c23;
  --char: #14100e;
  --char-2: #1d1815;
  --cream: #f7f1e8;
  --cream-dim: #c9bca9;
  --gold: #c99a4b;
  --line: rgba(247, 241, 232, 0.12);
  --serif: 'Playfair Display', Georgia, serif;
  --sans: 'Inter', system-ui, sans-serif;
  --script: 'Dancing Script', cursive;
  background: var(--char);
  color: var(--cream);
  font-family: var(--sans);
  min-height: 100vh;
  position: relative;
}
/* grain / glow, buttons, cards, badges, tabs, modal — all under .pampa-portal … */
.pampa-portal .btn { background: var(--crimson); /* …same as home .btn… */ }
```

Icon sizing/color goes in this CSS, NOT arbitrary-value Tailwind:

```css
.pampa-portal .type-tile b svg { width: 15px; height: 15px; margin-right: 7px; vertical-align: -2px; color: var(--gold); }
.pampa-portal .type-tile.couple b svg { color: var(--crimson); }
```

## 3. Audience-scoped API types + auth register

```ts
// Audience view omits other users' names, exposes raw photo path (no hasPhoto flag).
export interface MemberDelivery {
  id: string; memberId: string; month: string; bottles: number
  status: DeliveryStatus; deliveredAt: string | null; receivedBy: string | null
  proofPhotoPath: string | null; notes: string | null; createdAt: string
}
// client-side: const hasPhoto = !!d.proofPhotoPath

export type RegisterInput = {
  name: string; email: string; password: string
  type: 'single' | 'couple'; partnerName?: string; phone?: string
}

// in api.auth:
register: (data: RegisterInput) =>
  request<AuthMeResponse>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
```

Auth context `register()` auto-logs-in from the response (it returns user + member and sets the cookie):

```tsx
const register = useCallback(async (data: RegisterInput): Promise<AuthUser> => {
  const res = await api.auth.register(data)
  setUser(res.user)
  setMember(res.member)
  return res.user
}, [])
```

## 4. Audience route guard (redirects admins away)

```tsx
export function MemberRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <SessionSpinner />
  if (!user) return <Navigate to="/login" replace />
  if (user.role === 'admin') return <Navigate to="/admin" replace />
  return <>{children}</>
}
```

Login page role-based redirect (requires `login()` to return the user):

```tsx
const u = await login(email, password)
navigate(u.role === 'admin' ? '/admin' : '/portal', { replace: true })
```

## 5. Self-service actions in an existing portal (cancel, status callout, profile edit)

Patterns from adding self-cancel + pickup-ready + profile self-edit to the Pampa portal (2026-08-05). Backend endpoints already existed (`DELETE /api/events/:id/signup`, `PATCH /api/reservations/:id/cancel`, `PATCH /api/members/me`) — the work was UI wiring.

**Confirm → busyId → retry → inline error.** One busy flag per row; confirm before the destructive call; refetch on success; surface failures as a `role="alert"` banner at the top of the grid:

```tsx
function ReservationsPanel() {
  const { data, loading, error, retry } = useLoaded(() => api.reservations.list())
  const [busyId, setBusyId] = useState<string | null>(null)
  const [cancelError, setCancelError] = useState<string | null>(null)

  const cancelReservation = async (r: Reservation) => {
    if (!window.confirm(`Cancel your ${label} reservation for ${fmtDate(r.date)}?`)) return
    setBusyId(r.id); setCancelError(null)
    try { await api.reservations.cancel(r.id); retry() }
    catch (err) { setCancelError(errorMessage(err)) }
    finally { setBusyId(null) }
  }
  // …in each card, ONLY when the server would accept it:
  const cancellable = r.status === 'requested' || r.status === 'confirmed'
  {cancellable && (
    <div className="foot">
      <span className="sub">Plans changed?</span>
      <button className="btn ghost small danger" disabled={busyId === r.id}
        onClick={() => cancelReservation(r)}>
        {busyId === r.id ? <span className="spin" /> : <X className="h-3.5 w-3.5" />}
        {busyId === r.id ? 'Cancelling…' : 'Cancel reservation'}
      </button>
    </div>
  )}
}
```

The `cancellable` gate mirrors the server's rules — read the backend route to learn which statuses it accepts, then hide the button for the rest so it can never dead-end.

**Contextual status callout.** Compute from the fetched list; singular/plural-safe copy:

```tsx
const readyDeliveries = data?.filter(d => d.status === 'ready') ?? []
{readyDeliveries.length > 0 && (
  <div className="pp-ready-callout" role="status">
    <Package className="h-5 w-5" />
    <div>
      <b>Your {readyDeliveries.length === 1
        ? `${fmtMonth(readyDeliveries[0].month)} allotment is`
        : `${readyDeliveries.length} allotments are`} ready for pickup</b>
      <p>…pick it up at the restaurant.</p>
    </div>
  </div>
)}
```

**Profile tab with self-edit.** Destructure everything from one `useAuth()` call at the top (never call a helper hook inside a map callback). After the PATCH, call the auth context's `refresh()` so the header name updates too:

```tsx
const { user, member, refresh } = useAuth()
// submit:
await api.members.selfUpdate({
  name: name.trim(),
  phone: phone.trim() || null,
  partnerName: member.type === 'couple' ? partnerName.trim() || null : undefined,
})
await refresh()   // ← header + all consumers see the new values
setEditing(false); setSaved(true)
```

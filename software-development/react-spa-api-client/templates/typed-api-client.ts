/**
 * Typed API client for a session-cookie REST backend.
 * Copy, rename the resource groups, and fill in endpoints to match your routes.
 * Every request flows through `request<T>()` — the single chokepoint.
 */

const BASE = '/api'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** Human-readable message for a thrown error (ApiError or network failure). */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof Error) return err.message
  return 'Something went wrong'
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const isForm = options?.body instanceof FormData
  const res = await fetch(BASE + path, {
    credentials: 'include', // HttpOnly session cookie is the only auth — always send it
    ...options,
    // Let the browser set the multipart boundary for FormData; JSON otherwise.
    headers: isForm ? undefined : { 'Content-Type': 'application/json' },
  })
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { error?: string } | null
    throw new ApiError(res.status, body?.error || res.statusText || `Request failed (${res.status})`)
  }
  if (res.status === 204) return undefined as T // empty body — res.json() would throw
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Domain types — mirror the API's JSON responses EXACTLY.
// Derive these from the route HANDLERS, not the DB schema (handlers add joins
// like memberName and derived flags like hasPhoto/has_photo).
// ---------------------------------------------------------------------------

export interface AuthUser {
  id: string
  email: string
  name: string
  role: 'admin' | 'member'
}

// export interface Member { id: string; name: string; /* ... */ allotment: number }

// ---------------------------------------------------------------------------
// Endpoint groups
// ---------------------------------------------------------------------------

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ user: AuthUser }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
    me: () => request<{ user: AuthUser }>('/auth/me'),
  },

  // members: {
  //   list: () => request<Member[]>('/members'),
  //   create: (data: MemberCreate) =>
  //     request<Member>('/members', { method: 'POST', body: JSON.stringify(data) }),
  //   update: (id: string, data: MemberUpdate) =>
  //     request<Member>(`/members/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  // },

  // Multipart create — optional file attached; booleans as 'true'/'false' strings.
  // events: {
  //   create: (data: EventCreate) => {
  //     const fd = new FormData()
  //     fd.append('title', data.title)
  //     fd.append('date', data.date)
  //     fd.append('isSpecial', data.isSpecial ? 'true' : 'false')
  //     if (data.priceCents != null) fd.append('priceCents', String(data.priceCents))
  //     if (data.photo) fd.append('photo', data.photo)
  //     return request<ClubEvent>('/events', { method: 'POST', body: fd })
  //   },
  //   // JSON for plain field updates; switch to multipart only when a photo is attached.
  //   update: (id: string, data: EventUpdate) => {
  //     if (data.photo) {
  //       const fd = new FormData()
  //       for (const [k, v] of Object.entries(data)) {
  //         if (v == null || k === 'photo') continue
  //         fd.append(k, String(v))
  //       }
  //       fd.append('photo', data.photo)
  //       return request<ClubEvent>(`/events/${id}`, { method: 'PATCH', body: fd })
  //     }
  //     return request<ClubEvent>(`/events/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
  //   },
  //   photoUrl: (id: string) => `${BASE}/events/${id}/photo`, // <img src> — cookie rides along
  // },
}

// ---------------------------------------------------------------------------
// Shared formatters — money travels in integer cents; convert at the UI edge.
// ---------------------------------------------------------------------------

/** Cents → "$45.00" */
export const fmtMoney = (cents: number | null | undefined) =>
  `$${((cents ?? 0) / 100).toFixed(2)}`

/** Dollars form string → integer cents for the API. null when unparseable. */
export const dollarsToCents = (dollars: string): number | null => {
  const n = parseFloat(dollars)
  if (!Number.isFinite(n) || n < 0) return null
  return Math.round(n * 100)
}

/** ISO date (or date-only YYYY-MM-DD) → "Fri, Aug 1, 2026" */
export const fmtDate = (iso: string | null | undefined) =>
  iso
    ? new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : '—'

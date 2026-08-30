# Next.js Image Optimization + Same-Origin API Routes

Next.js `<Image>` from `next/image` tries to optimize all images through its built-in optimizer at `/_next/image?url=...&w=...&q=...`. The optimizer internally fetches the image URL, processes it, and serves the optimized version.

**Problem:** The image optimizer **cannot proxy dynamic API routes** (`/api/ship-image/{id}`, etc.). When `<Image>` is used with `src="/api/ship-image/{id}"`, the optimizer:

1. Gets the request at `/_next/image?url=%2Fapi%2Fship-image%2F{id}&w=2048&q=75`
2. Internally fetches the API route
3. The internal fetch returns 400 (params may not resolve, or the response format is unexpected)
4. Returns 400 to the browser → broken image

The image works on **first load from browser cache** (if the page SSR'd with the right src), but fails on **subsequent loads** when the optimizer tries to re-optimize.

## Fix: `unoptimized` prop

```tsx
<Image
  src="/api/ship-image/{id}"
  fill
  unoptimized  // ← skip the optimizer, serve raw from API
/>
```

The API already returns optimized binary data (e.g., JPEG at good quality), so there's no need for Next.js to re-compress or resize it.

## Which components are affected

Any component using `next/image` with `src` pointing to a same-origin API route:

```tsx
// ❌ Fails: goes through optimizer
<Image src="/api/ship-image/{id}" fill />

// ✅ Works: served raw
<Image src="/api/ship-image/{id}" fill unoptimized />

// ✅ Works: regular img doesn't trigger optimizer
<img src="/api/ship-image/{id}" />
```

## Pattern: use `getProxiedImageUrl()` to compute src

The `lib/utils/image-proxy.ts` helper returns `/api/ship-image/${shipId}` when a shipId exists. Components using this helper with `<Image>` must add `unoptimized`.

## Detection

Browser console shows:
```
image?url=%2Fapi%2Fship-image%2F{uuid}&w=2048&q=75:1  Failed to load resource: the server responded with a status of 400 ()
```

While direct curl to the API route returns 200:
```
curl -svo /dev/null https://example.com/api/ship-image/{uuid}
→ HTTP/2 200
```

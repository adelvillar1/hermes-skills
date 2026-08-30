# Overpass API from Node.js

Working patterns for accessing the Overpass API (OpenStreetMap data) from Node.js/TypeScript.

## Critical Headers

Overpass rejects requests without a proper `User-Agent`. Both `Content-Type` and `Accept` must also be set correctly:

```typescript
const response = await fetch('https://overpass-api.de/api/interpreter', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json',
    'User-Agent': 'YourApp/1.0 (your-contact-info)',
  },
  body: `data=${encodeURIComponent(query)}`,
});
```

Without `User-Agent`, the API returns **HTTP 406 Not Acceptable** with an HTML error page. This is the single most common integration failure.

## Query Format

The query must be sent as a `data` form parameter (not as the raw POST body):

```typescript
// ✅ Correct
body: `data=${encodeURIComponent(query)}`

// ❌ Wrong (returns 406)
body: query
```

## Example Queries

### Buildings within a bounding box
```overpass
[out:json][timeout:30];
(
  way["building"](south,west,north,east);
  relation["building"](south,west,north,east);
);
out body geom;
```

### Roads/highways within a bounding box
```overpass
[out:json][timeout:30];
(
  way["highway"](south,west,north,east);
);
out body geom;
```

## Coordinate Handling

Overpass returns `lon` (not `lng`) in geometry points. Always handle both:

```typescript
interface OsmPoint {
  lat: number;
  lon?: number;
  lng?: number;
}
// Access: pt.lon ?? pt.lng
```

## Error Handling

When the server is overloaded, it may return HTML/XML instead of JSON:

```typescript
if (!response.ok) {
  const text = await response.text();
  if (text.startsWith('<?xml') || text.startsWith('<!DOCTYPE')) {
    // Retry with delay
    await new Promise(r => setTimeout(r, 3000));
    const retry = await fetch(/* same fetch */);
    // ...
  }
}
```

## Rate Limiting

- Recommended: **2+ second delay** between sequential requests
- Overpass has no documented hard rate limit but aggressive polling may be throttled
- Use `[timeout:NN]` in the query to set server-side timeout (default: 180s, recommended: 25-30s)
- Keep bounding boxes small (~1-2km² for detailed building data)

## Bounding Box Geography

For a point-based query (e.g., port location), calculate the bounding box as:

```typescript
const ZOOM = 0.008; // ~1.8km × 1.8km at most latitudes
const south = lat - ZOOM;
const north = lat + ZOOM;
const west = lng - ZOOM;
const east = lng + ZOOM;
```

One degree of latitude ≈ 111km. Longitude width varies by cos(lat).

## Mercator Projection for 3D

When projecting OSM coordinates into 3D space for Three.js:

```typescript
const scale = 51000;
function project(lat: number, lng: number, refLat: number, refLng: number) {
  const x = (lng - refLng) * scale * Math.cos((refLat * Math.PI) / 180);
  const y = (lat - refLat) * scale;
  return new THREE.Vector2(x, y);
}
```

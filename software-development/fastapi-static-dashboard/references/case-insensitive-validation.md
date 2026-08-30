# Case-Insensitive API Parameter Validation

## Problem

Frontend select options often send uppercase values (`MLB`, `NFL`, `NBA`) but `Literal["mlb", "nfl", "nba"]` only accepts lowercase. This causes 422 errors in production after deploying the validation.

## Solution: BeforeValidator with Annotated

Create a shared parameter module at `src/api/sport_param.py`:

```python
"""Shared API parameter types for sport validation."""

from typing import Annotated
from fastapi import Query
from pydantic import BeforeValidator


def _normalize_sport(v: str | None) -> str | None:
    """Lowercase sport value and validate."""
    if v is None:
        return None
    v_lower = v.strip().lower()
    if v_lower not in ("mlb", "nfl", "nba"):
        raise ValueError(f"Invalid sport: {v!r}. Choose from: mlb, nfl, nba.")
    return v_lower


SportQuery = Annotated[
    str | None,
    Query(description="Filter by sport: mlb, nfl, nba"),
    BeforeValidator(_normalize_sport),
]


def _normalize_sport_required(v: str) -> str:
    """Lowercase required sport value and validate."""
    v_lower = v.strip().lower()
    if v_lower not in ("mlb", "nfl", "nba"):
        raise ValueError(f"Invalid sport: {v!r}. Choose from: mlb, nfl, nba.")
    return v_lower


SportPath = Annotated[
    str,
    BeforeValidator(_normalize_sport_required),
]
```

## Usage in routes

```python
# Query parameter (optional)
from src.api.sport_param import SportQuery

@router.get("", response_model=list[Team])
async def get_ratings(sport: SportQuery = None, ...):
    # sport is already lowercase or None
    ...

# Path parameter (required)
from src.api.sport_param import SportPath

@router.get("/{sport}", response_model=ScheduleResponse)
async def get_schedule(sport: SportPath, ...):
    # sport is already lowercase
    ...
```

## Why BeforeValidator instead of Literal

- `Literal["mlb", "nfl", "nba"]` rejects uppercase → 422 error
- `Literal["mlb", "nfl", "nba", "MLB", "NFL", "NBA"]` works but is ugly and requires normalizing in every endpoint
- `BeforeValidator` normalizes before validation — clean, DRY, case-insensitive

## Key pitfall

When using `BeforeValidator` with FastAPI query params, the validator runs before Pydantic type checking. If the validator raises `ValueError`, FastAPI returns 422 with a clear error message. If you use `AfterValidator` instead, the value is already `str | None` and the validator receives the raw input before type coercion.

## Frontend fix (alternative)

Instead of backend normalization, lowercase in the frontend:

```javascript
// In buildQuery()
if (state.league) params.set('sport', state.league.toLowerCase());
```

But backend normalization is more robust — it handles direct API calls, bookmarks, and third-party integrations.

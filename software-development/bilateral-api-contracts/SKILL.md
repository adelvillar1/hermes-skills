---
name: bilateral-api-contracts
description: "Build a bilateral bridge between TypeScript Zod schemas and Python Pydantic + SQLAlchemy. Covers the full pattern: shared enums, Pydantic BaseModels with Field(alias=...) for camelCase↔snake_case translation, SQLAlchemy ORM models, Alembic migrations, contract tests, and seed commands. Use when the frontend has Zod schemas and the backend needs to produce the same camelCase JSON."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [python, typescript, api-contracts, pydantic, sqlalchemy, zod, bilateral-bridge]
    related_skills: [draft-feature-plan, database-schema-contract, postgres-patterns, test-driven-development]
---

# Bilateral API Contracts

Build the **bilateral bridge** between a TypeScript frontend (Zod schemas) and a Python backend (Pydantic + SQLAlchemy). The canonical pattern from the stock-predictor project (2026-06-12).

## When to Use

- Frontend has Zod schemas defining API contract shapes
- Backend is Python (FastAPI, Flask, etc.) and needs to produce the same camelCase JSON
- You need SQLAlchemy ORM models for persistence that match the contract
- The naming plan requires camelCase JSON wire format with snake_case Python identifiers

## The Architecture (3 Layers + Tests)

```
Layer 1: Shared enums/constants     ← mirrors TS const arrays + named constants
Layer 2: Pydantic contracts          ← mirrors Zod schemas, camelCase via Field(alias=...)
Layer 3: SQLAlchemy ORM models       ← persistence, snake_case columns
Layer 4: Alembic migration           ← creates all tables
Layer 5: Seed command                ← hardcoded mock data validated through contracts
Layer 6: Contract tests              ← camelCase verification, round-trip, forbid extras
```

## Step-by-Step

### 1. Extract all Zod schemas from the TS side

Read every `*.ts` file in `src/types/`. For each Zod schema, record:
- Field names (camelCase)
- Field types and constraints (`z.number().min(0).max(1)`, `z.string().regex(...)`, etc.)
- `.refine()` / `.superRefine()` cross-field validators
- Enums (`z.enum([...])`) and named constants
- Which schemas are persisted (have backing tables) vs computed projections (Pydantic-only)

### 2. Create shared enums (`contract/enums.py`)

Mirror every TS `const` array and enum:

| TS pattern | Python equivalent |
|---|---|
| `const HORIZONS = ['1d', '5d', ...] as const` | `class Horizon(str, Enum)` (or `StrEnum` on 3.11+) |
| `const FLAT_THRESHOLD = 0.005` | `FLAT_THRESHOLD: Final[float] = 0.005` |
| `const HORIZON_DAYS: Record<Horizon, number> = {...}` | `HORIZON_DAYS: Final[dict[Horizon, int]] = {...}` |

**Naming:** TS `UPPER_SNAKE` arrays → Python `PascalCase` enum classes. Values stay identical.

### 3. Create Pydantic contracts (`contract/*.py`)

One module per domain area. Every model follows this pattern:

```python
class InstrumentContract(BaseModel):
    """Mirrors InstrumentSchema from apps/web/src/types/instrument.ts."""
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    instrument_id: str = Field(alias="instrumentId", min_length=1)
    symbol: str = Field(min_length=1, max_length=10)
    name: str = Field(min_length=1)
    kind: InstrumentKind
    exchange: str | None = Field(min_length=1, default=None)
    currency: str = Field(min_length=3, max_length=3)
    sector: str | None = Field(min_length=1, default=None)
    added_at: str = Field(alias="addedAt")
```

**Key rules:**
- `ConfigDict(populate_by_name=True, extra="forbid")` — `extra='forbid'` mirrors Zod `.strict()`
- `snake_case` Python identifiers with `Field(alias="camelCase")` for wire format
- `model_dump(by_alias=True)` produces camelCase JSON
- `model_dump()` produces snake_case (internal use)
- Import enums from `contract/enums.py`, never inline string literals
- **Graph/counterparty schemas are Pydantic-only** (no SQLAlchemy model) — they're computed projections

**Cross-field validators** (mirror Zod `.refine()`):

```python
@model_validator(mode="after")
def ohlcv_invariants(self) -> "PricePointContract":
    if not (self.low <= self.open <= self.high):
        raise ValueError("low <= open <= high invariant violated")
    if not (self.low <= self.close <= self.high):
        raise ValueError("low <= close <= high invariant violated")
    return self
```

**Field-level constraints** (mirror Zod `z.number().min().max()`):
- `confidence: float = Field(ge=0, le=1, multiple_of=0.01)`
- `version: str = Field(pattern=r"^\d+\.\d+\.\d+$")`
- `cik: str = Field(pattern=r"^\d{10}$")`

### 4. Create SQLAlchemy ORM models (`db/models/*.py`)

One module per persisted table. Key conventions:

- Tables are **plural** (`instruments`, `predictions`)
- Columns are **snake_case**, matching Python attribute names exactly
- Primary keys are prefixed IDs (`instrument_id`, not `id`)
- Foreign keys specify `ondelete` behavior:
  - Parent references: `ondelete='RESTRICT'` (can't delete parent with children)
  - Child references: `ondelete='CASCADE'` (delete children when parent deleted)
- Composite PKs use `__table_args__ = (PrimaryKeyConstraint(...), Index(...))`
- All models inherit from a shared `Base(DeclarativeBase)`

```python
class PricePoint(Base):
    __tablename__ = "price_points"
    __table_args__ = (
        PrimaryKeyConstraint("instrument_id", "timestamp"),
        Index("idx_price_points_instrument_ts", "instrument_id", "timestamp"),
    )
    instrument_id: Mapped[str] = mapped_column(
        String, ForeignKey("instruments.instrument_id", ondelete="RESTRICT"), nullable=False
    )
    # ...
```

### 5. Set up Alembic with async support

The `alembic/env.py` needs `sys.path` fix for `src.*` imports:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

Then import all models via `from src.db.models import *` (with `noqa: F401, F403`).

Use `create_async_engine` from the app's `get_settings().database_url` in `run_async_migrations()`.

### 6. Create seed command

A CLI that reads hardcoded Python literals (mirroring TS mock data), validates each through the contract model, and inserts via `session.merge()` (upsert). Default `--dry-run`, explicit `--live`.

### 7. Write contract tests

Three test files:

**`test_bilateral_contract.py`** — parametrized over all 13 contracts:
- `test_camelcase_keys`: `model_dump(by_alias=True)` keys match `^[a-z][a-zA-Z0-9]*$`
- `test_round_trip`: `Model.model_validate(Model(...).model_dump(by_alias=True))` == original
- `test_forbid_extra_fields`: adding unknown key raises error
- `test_*_violation`: cross-field validators reject invalid data

**`test_sql_bilateral.py`** — for every `Base` subclass:
- `column.name == attr_name` for every column (using `mapper.column_attrs`)
- Tables have `__tablename__`

**`test_contract_schemas.py`** — mock data validates through contracts:
- Parse each mock record through corresponding Pydantic contract
- Verify expected record counts

## Pitfalls

### Pytest fixture mutation silently contaminates tests
Tests that mutate their fixture data (dicts from module-level constants) without `copy.deepcopy()` corrupt the data for all subsequent tests. Symptoms: tests pass in isolation but fail in the full suite, with confusing error messages about unrelated fields.

**Fix:** Every test that modifies input data MUST deepcopy first:
```python
def test_relationship_self_loop(self, relationship_data: dict):
    data = copy.deepcopy(relationship_data)
    data["toInstrumentId"] = data["fromInstrumentId"]
    with pytest.raises(ValueError):
        RelationshipContract.model_validate(data)
```

### SQLAlchemy 2.0 column inspection API
`mapper.columns` returns raw `Column` objects, not `ColumnProperty`. The correct API for bilateral testing:
```python
for attr_name, col_property in mapper.column_attrs.items():
    for col in col_property.columns:
        assert col.name == attr_name
```
NOT `inspect(cls).columns` which returns a different type.

### Alembic env.py path resolution
Alembic runs from the project root, not from `src/`. Without `sys.path.insert(0, ...)`, `from src.db.models import *` fails with `ModuleNotFoundError`. The path must be `Path(__file__).resolve().parent.parent` (env.py is at `alembic/env.py`, parent.parent is the project root).

### Mock data self-loops
When writing mock relationship data by hand, it's easy to set `fromInstrumentId` and `toInstrumentId` to the same value (especially when copy-pasting). The contract validator will catch this, but the error message can be confusing when the test is also mutating fixtures.

### StrEnum vs (str, Enum)
On Python 3.11+, use `StrEnum` instead of `(str, Enum)`. Ruff's `UP042` rule catches this. If you need 3.10 compatibility, suppress the rule.

### `extra='forbid'` is mandatory
Without it, the Python API silently accepts extra fields that the TS Zod side would reject (`.strict()`). This is the #1 contract-completeness bug caught by cross-LLM review.

### HORIZON_DAYS constant is easy to miss
The TS `horizon.ts` exports both the enum AND a `HORIZON_DAYS` mapping dict. The Python side needs both in `enums.py`. Cross-LLM review caught this omission.

## Verification Checklist

```bash
# 1. Lint
cd apps/api && uv run ruff check .

# 2. Tests
uv run pytest tests/ -v  # all pass

# 3. Alembic round-trip
rm -f stock_predictor.db
uv run alembic upgrade head
uv run alembic downgrade base
uv run alembic upgrade head

# 4. Seed dry-run
uv run python -m src.cli.seed --dry-run  # validates mock data

# 5. Seed live + idempotent
uv run python -m src.cli.seed --live
uv run python -m src.cli.seed --live  # same counts, no duplicates
```

## REST Endpoint Layer (Phase 2)

After the bilateral bridge ships, the next step is wiring it to HTTP endpoints. The pattern is **Repository → Router → Contract response**:

### Repository modules (`src/repositories/`)

Namespace classes with `@staticmethod` methods. Accept `AsyncSession`, return ORM objects. Routers convert to contracts.

```python
class InstrumentRepository:
    @staticmethod
    async def list_instruments(session: AsyncSession, *, sector: str | None = None) -> list[Instrument]:
        stmt = select(Instrument)
        if sector is not None:
            stmt = stmt.where(Instrument.sector == sector)
        result = await session.execute(stmt)
        return list(result.scalars().all())
```

### Router modules (`src/routers/`)

FastAPI `APIRouter` with prefix. Response models are the Pydantic contracts. Use `Depends(get_db)` for session injection.

```python
router = APIRouter(prefix="/api/instruments", tags=["instruments"])

@router.get("/", response_model=list[InstrumentContract])
async def list_instruments(db: AsyncSession = Depends(get_db)):
    instruments = await InstrumentRepository.list_instruments(db)
    return [InstrumentContract.model_validate(i.__dict__) for i in instruments]
```

**Pitfall — B008 ruff suppression:** FastAPI's `Depends()` in default args triggers `B008`. Add `"B008"` to `pyproject.toml` `[tool.ruff.lint] ignore` list.

**Pitfall — Graph queries need 3 explicit queries:** ORM models don't have `relationship()` attributes for eager loading. Use `WHERE id IN (...)` for instruments, separate query for sources. Total 3 queries (relationships, sources, instruments) — acceptable for v1 data volumes.

### Test fixtures (`tests/conftest.py`)

Session-scoped fixture: create all tables via `Base.metadata.create_all`, seed mock data once, monkey-patch `get_session_factory` to return test session factory. Each test file uses `httpx.AsyncClient` with `ASGITransport`.

```python
@pytest_asyncio.fixture(scope="session")
async def client(_setup_db):
    import src.db.engine as engine_mod
    engine_mod.get_session_factory = lambda: _test_session_factory
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

### Enum wrapping for ORM→Contract conversion

ORM models store enum values as strings. When building contracts from ORM objects, wrap in enum constructors:

```python
kind=RelationshipKind(rel.kind)  # not rel.kind (str)
filingType=FilingType(src.filing_type) if src else FilingType.TEN_K
```

## FastAPI Response Model Serialization

When using Pydantic contracts as `response_model` in FastAPI, the response uses **Python field names** by default (snake_case). To get camelCase JSON in the API response, you need one of:

**Option A: `response_model_by_alias=True`** on the endpoint decorator (not yet supported in all FastAPI versions).

**Option B: Override `model_dump`** in the contract to always use aliases. Not recommended — breaks internal use.

**Option C (recommended): Use `json_encoders` or let FastAPI handle it.** FastAPI calls `model_dump()` internally for `response_model` validation. The JSON response will use Python names. If the frontend expects camelCase, either:
1. The frontend sends/receives snake_case for API calls (acceptable for query params)
2. Add a response serializer that calls `model_dump(by_alias=True)` before returning

For internal API endpoints (worker → API), snake_case is fine. For public endpoints consumed by the TS frontend, ensure the response is camelCase.

## Pyright False Positives with Pydantic

Pyright doesn't fully understand Pydantic v2's `populate_by_name=True`:
- Constructor calls with snake_case field names show "argument not assignable" even though they work at runtime
- `Field(alias=...)` parameters confuse Pyright's overload resolution

**Fix:** Use `# type: ignore[reportArgumentType]` on constructor calls that use Python names, or switch to `model_validate(dict)` which Pyright handles correctly.

## Related Skills

- `draft-feature-plan` — use to plan the bilateral bridge before building
- `database-schema-contract` — schema drift detection between environments
- `test-driven-development` — TDD pattern for the contract tests
- `postgres-patterns` — PostgreSQL-specific patterns for production

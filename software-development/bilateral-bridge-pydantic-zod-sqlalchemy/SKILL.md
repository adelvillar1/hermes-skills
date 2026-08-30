---
name: bilateral-bridge-pydantic-zod-sqlalchemy
description: "When a Python backend needs to mirror TypeScript Zod schemas as Pydantic BaseModels (camelCase wire format) + SQLAlchemy ORM models (snake_case DB). Covers the Field(alias=...) pattern, extra='forbid', contract tests, Alembic setup, and seed commands. Load when building API contract layers between TS frontends and Python backends."
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [pydantic, zod, sqlalchemy, api-contract, bilateral-bridge, fastapi]
    related_skills: [draft-feature-plan, database-schema-contract, postgres-patterns]
---

# Bilateral Bridge: Pydantic ↔ Zod ↔ SQLAlchemy

Build an API contract layer where TypeScript Zod schemas are the source of truth, Pydantic BaseModels mirror them for wire serialization, and SQLAlchemy models provide persistence. The JSON wire format is **camelCase**; Python identifiers are **snake_case**; SQL identifiers are **snake_case**.

## When to use

- Python backend + TypeScript frontend where both sides validate the same shapes
- You need runtime validation at the API boundary (not just compile-time TypeScript)
- The wire format is camelCase JSON but Python/SQL use snake_case
- You want contract tests that prevent schema drift between the two sides

## When NOT to use

- Single-language project (just use the native validation)
- No shared contract needed (frontend and backend evolve independently)
- GraphQL (the schema IS the contract)

## The Three-Layer Architecture

```
TS Zod Schema (source of truth)
       ↓ mirror
Pydantic BaseModel (wire format, camelCase via Field alias)
       ↓ map
SQLAlchemy ORM Model (storage, snake_case columns)
```

### Layer 1: Shared enums and constants

Create `src/contract/enums.py` with Python `str` enums mirroring TS `as const` arrays:

```python
from enum import Enum

class InstrumentKind(str, Enum):
    EQUITY = "equity"
    ETF = "etf"
    # values MUST match TS: z.enum(['equity', 'etf', ...])
```

For constants like `FLAT_THRESHOLD = 0.005` or `HORIZON_DAYS`, use `Final` types.

### Layer 2: Pydantic contracts

One module per domain area in `src/contract/`. Every model uses:

```python
from pydantic import BaseModel, ConfigDict, Field

class InstrumentContract(BaseModel):
    """Mirrors InstrumentSchema from apps/web/src/types/instrument.ts."""
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    instrument_id: str = Field(alias="instrumentId", min_length=1)
    symbol: str = Field(min_length=1, max_length=10)
    name: str = Field(min_length=1)
    kind: InstrumentKind
    exchange: str | None = None
    currency: str = Field(min_length=3, max_length=3)
    sector: str | None = None
    added_at: str = Field(alias="addedAt")
```

**Critical config:**
- `populate_by_name=True` — allows construction with either `instrument_id` (Python) or `instrumentId` (wire)
- `extra="forbid"` — mirrors Zod `.strict()`, rejects unknown fields
- `Field(alias="camelCase")` — maps Python snake_case to wire camelCase

**Serialization:**
- `model_dump(by_alias=True)` → camelCase JSON (for API responses)
- `model_dump()` → snake_case (for internal use)
- `Model.model_validate(wire_json)` → construct from camelCase wire data
- `Model.model_validate(db_row.__dict__)` → construct from snake_case DB data

**Naming convention:** Use `*Contract` suffix (not `*Schema` — that's the Zod naming; not `*Dto` — that's for wire-only transport shapes).

### Layer 3: SQLAlchemy ORM models

One module per table in `src/db/models/`. Tables are **plural**, columns are **snake_case**.

```python
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Instrument(Base):
    __tablename__ = "instruments"

    instrument_id: Mapped[str] = mapped_column(String, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    # ...
```

**Column naming:** Every column name MUST match its Python attribute name. No `Column("camelCase", ...)` — the contract test enforces this.

### Layer 4: Alembic migration

```bash
cd apps/api
uv run alembic revision --autogenerate -m "create initial schema"
uv run alembic upgrade head
uv run alembic downgrade base  # verify clean teardown
```

**Async Alembic setup:** The `env.py` needs `sys.path.insert(0, ...)` so `src.*` imports resolve. See `references/alembic-async-setup.md` for the full template.

### Layer 5: Seed command

A CLI subcommand that reads hardcoded mock data (mirroring TS mock files) and inserts via `session.merge()` (upsert):

```bash
uv run python -m src.cli.seed --dry-run   # validate + count
uv run python -m src.cli.seed --live       # insert
```

### Layer 6: Contract tests

Three test files enforce the bilateral contract:

1. **`test_bilateral_contract.py`** — every `*Contract` model:
   - `model_dump(by_alias=True)` produces only camelCase keys (`^[a-z][a-zA-Z0-9]*$`)
   - Round-trip: `Model.model_validate(Model(...).model_dump(by_alias=True))` produces equivalent instance
   - `extra='forbid'` rejects unknown fields

2. **`test_sql_bilateral.py`** — every SQLAlchemy model:
   - `column.name == attr_name` for every column (no camelCase in SQL)
   - Uses `mapper.column_attrs` to iterate columns

3. **`test_contract_schemas.py`** — mock data validates through contracts:
   - Parse each mock record through the corresponding Pydantic contract
   - Assert no validation errors

## Pitfalls

### `extra='forbid'` is mandatory

Without it, the Python API silently accepts extra fields that the TS side would reject. This is the most common bilateral-bridge bug — the contract looks correct but doesn't enforce strictness. Always add `extra="forbid"` to `model_config`.

### Pytest fixtures mutate module-level dicts

When fixtures return references to module-level dicts (like `MOCK_DATA[0]`), tests that modify the returned dict mutate the source. This causes cross-test contamination — test A adds an `unknownField`, test B fails because the field is now present.

**Fix:** Use `copy.deepcopy()` in any test that modifies fixture data:
```python
def test_forbid_extra_fields(self, data):
    import copy
    modified = copy.deepcopy(data)
    modified["unknownField"] = "should fail"
    with pytest.raises(ValidationError):
        Contract.model_validate(modified)
```

**Also fix:** tests that mutate data for invariant testing (e.g., setting `low = 999` to break OHLC). Always deepcopy before mutating.

### Field-level constraints from Zod need Pydantic equivalents

Zod's `z.number().min(0).max(1).multipleOf(0.01)` maps to Pydantic's `Field(ge=0, le=1, multiple_of=0.01)`. Don't skip these — they catch invalid data at the API boundary.

### Cross-field validators mirror Zod .refine()

Zod's `.refine()` and `.superRefine()` map to Pydantic's `@model_validator(mode="after")`:

```python
@model_validator(mode="after")
def ohlcv_invariants(self) -> "PricePointContract":
    if not (self.low <= self.open <= self.high):
        raise ValueError("low <= open <= high invariant violated")
    return self
```

### Composite primary keys need `__table_args__`

```python
class PricePoint(Base):
    __tablename__ = "price_points"
    __table_args__ = (
        PrimaryKeyConstraint("instrument_id", "timestamp"),
        Index("idx_price_points_instrument_ts", "instrument_id", "timestamp"),
    )
```

### FK `ondelete` behavior must be specified

- Parent tables (instruments, models): `ondelete='RESTRICT'` — can't delete a parent with children
- Child tables (outcomes→predictions): `ondelete='CASCADE'` — delete children when parent is deleted

### Alembic `env.py` needs sys.path fix

Alembic runs from the project root, so `from src.db.models import *` fails without:
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

### `HORIZON_DAYS` and similar mappings need Python equivalents

If the TS side has `Record<Enum, number>` mappings (like `HORIZON_DAYS`), mirror them as `Final[dict[Enum, int]]` in `enums.py`. Don't forget them — they're used in cross-field validators.

### `exactOptionalPropertyTypes: true` requires `| undefined` on optional TS params

When `exactOptionalPropertyTypes: true` is set in `tsconfig.json`, a function signature with `{ cursor?: string }` does **NOT** accept `{ cursor: string | undefined }`. This is a structural mismatch: `?` means "property may be absent", while `string | undefined` means "property is present but may be undefined". With strict optional properties, these are different types.

This bites repeatedly in the bilateral bridge when writing TS client functions that accept optional params (especially from TanStack Query `pageParam` values, which are `string | undefined`):

```typescript
// FAILS with exactOptionalPropertyTypes: true
async function getItems(
  params?: { cursor?: string },
): Promise<PaginatedResponse<Item>> { ... }

// Caller passes { cursor: pageParam } where pageParam is string | undefined
// → TS2379: Types of property 'cursor' are incompatible.
//   Type 'string | undefined' is not assignable to type 'string'.
```

**Fix:** Declare optional params with explicit `| undefined`:

```typescript
async function getItems(
  params?: { cursor?: string | undefined; limit?: number | undefined },
): Promise<PaginatedResponse<Item>> { ... }
```

This allows the property to be either absent OR explicitly `undefined`, satisfying `exactOptionalPropertyTypes`.

### Python keyword collision with wire alias names

When the camelCase wire key is a Python keyword (e.g., `none`, `class`, `import`), you cannot use it as a Pydantic field name. Use a Python-safe attribute name with `Field(alias=...)` pointing at the wire key:

```python
class VotingAuthority(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    sole: int = Field(ge=0)
    shared: int = Field(ge=0)
    # 'none' is a Python keyword — attribute is 'none_votes', wire alias is 'none'
    none_votes: int = Field(alias="none", ge=0)
```

On the TS side, `none` is not a keyword, so the Zod schema uses it directly:

```typescript
const VotingAuthoritySchema = z.object({
    sole: z.number().int().nonnegative(),
    shared: z.number().int().nonnegative(),
    none: z.number().int().nonnegative(),  // wire shape; not a Python keyword in TS
}).strict();
```

Round-trip: `{"none": 2}` deserializes into `none_votes=2` and re-serializes back to `{"none": 2}`. The wire shape is `none` on both sides; only the Python attribute differs. Use `populate_by_name=True` so the model accepts both `none_votes` (Python) and `none` (wire) on input.

**Detection:** If you're mirroring a TS schema and encounter a key that is a Python reserved word (`False`, `None`, `True`, `and`, `as`, `assert`, `async`, `await`, `break`, `class`, `continue`, `def`, `del`, `elif`, `else`, `except`, `finally`, `for`, `from`, `global`, `if`, `import`, `in`, `is`, `lambda`, `nonlocal`, `not`, `or`, `pass`, `raise`, `return`, `try`, `while`, `with`, `yield`), this pattern applies. Common in SEC/financial data: `none` (voting authority), `class` (share class), `type` (not a keyword but confusing).

### Sentinel values for UNIQUE constraint columns (SQLite + PostgreSQL)

When a column participates in a UNIQUE constraint but is semantically "optional" (e.g., `cik` in an entity-resolution audit table, `put_call` in a 13F-HR holdings table), **do NOT use `nullable=True`**. Both SQLite and PostgreSQL treat NULL as distinct in UNIQUE constraints — meaning multiple rows with NULL in the same constraint tuple do NOT conflict, so re-runs create duplicates instead of upserting.

This is the same issue as `NULLS NOT DISTINCT` (PostgreSQL 15+), but SQLite has no equivalent. For cross-engine projects (SQLite dev + PostgreSQL prod), use **sentinel default values** instead of NULL:

```python
class EntityMatch(Base):
    __tablename__ = "entity_match"
    __table_args__ = (
        # This UNIQUE constraint only works if cik and matched_instrument_id
        # are non-nullable. NULL-in-UNIQUE = distinct on both engines.
        UniqueConstraint(
            "raw_name", "cik", "matched_instrument_id", "algorithm_version",
            name="uq_entity_match_idempotency",
        ),
    )
    # Sentinel defaults: '' for cik, 'UNRESOLVED' for matched_instrument_id
    cik: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    matched_instrument_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="UNRESOLVED"
    )
```

```python
class InstitutionalHolding(Base):
    __table_args__ = (
        UniqueConstraint(
            "fund_cik", "report_period", "instrument_cusip", "put_call",
            name="uq_13f_idempotency",
        ),
    )
    # put_call is 'NONE' (sentinel) instead of NULL for a non-option holding
    put_call: Mapped[str] = mapped_column(String(4), nullable=False, default="NONE")
```

The Pydantic contract mirrors the sentinel pattern with `default=""` / `default="UNRESOLVED"`:

```python
cik: str = Field(default="")
matched_instrument_id: str = Field(alias="matchedInstrumentId", default="UNRESOLVED")
```

**Rule:** If a column is in a UNIQUE constraint tuple, it must be `NOT NULL` with a sentinel default. Reserve `nullable=True` for columns that do NOT participate in any uniqueness constraint.

### Adding UNIQUE constraints to existing tables: SQLite needs `batch_alter_table`

SQLite cannot `ALTER TABLE ... ADD CONSTRAINT`. When an Alembic migration adds a UNIQUE constraint to an existing table, it must use `batch_alter_table` with `recreate="always"`, which recreates the entire table under the hood:

```python
def upgrade() -> None:
    op.batch_alter_table(
        "relationships",
        schema=None,
        recreate="always",
        table_args=(
            sa.UniqueConstraint(
                "from_instrument_id", "to_instrument_id", "kind",
                name="uq_relationship_edge",
            ),
        ),
    )

def downgrade() -> None:
    op.batch_alter_table("relationships", schema=None)
```

PostgreSQL handles `ALTER TABLE ADD CONSTRAINT` natively, but the `batch_alter_table` approach works on both engines — use it for cross-engine migrations. The `downgrade` with `batch_alter_table` and no `table_args` removes the constraint.

**Note:** `alembic revision --autogenerate` does NOT detect missing UNIQUE constraints on existing tables — it generates an empty migration. You must write the `batch_alter_table` call manually.

### Mock data must be updated on BOTH sides when schema fields are added

When you add a new field to a Pydantic contract + Zod schema, every consumer of that type breaks until the mock data is updated. There are **three** mock-data sites in a typical bilateral-bridge project:

1. **`apps/api/src/cli/mock_data.py`** — Python dicts consumed by the seed command and `conftest.py`
2. **`apps/api/tests/conftest.py`** — ORM construction sites that must pass the new fields
3. **`apps/web/src/data/mock-instruments.ts`** (or equivalent) — TypeScript `Instrument[]` typed by `z.infer<typeof InstrumentSchema>`

If you skip any site:
- Python: `ValidationError` at import time or `conftest.py` fails to seed
- TypeScript: `tsc --noEmit` fails with `TS2739: Type ... is missing the following properties from type ...: cik, marketCap, shareClass, cusip`

**Automation tip:** When adding N fields to an existing schema, use a `sed` or `node` one-liner to bulk-insert the new fields before the `addedAt` (or equivalent last) property in every mock entry. Example for TS mock data:

```bash
sed -i '' "s/    addedAt: '/    cik: null,\n    marketCap: null,\n    shareClass: null,\n    cusip: null,\n    addedAt: '/g" src/data/mock-instruments.ts
```

**Python `None` vs JSON `null`:** When programmatically generating Python mock data (e.g., via a script that inserts JSON-shaped fields), `null` is a JSON value, not a Python keyword. Python interprets bare `null` as `NameError: name 'null' is not defined`. Use `None` in Python mock data. This bites when a script generates `"shareClass": null` (valid JSON) but the file is Python source.

### SQLAlchemy `Date`/`DateTime` columns reject string values

When ingesting parsed data (e.g., from XML/JSON APIs) into an ORM model with `Date` or `DateTime` mapped columns, SQLAlchemy does NOT auto-convert strings. The insert raises `StatementError: SQLite Date type only accepts Python date objects`. Parse strings to `date`/`datetime` objects before assignment:

```python
from datetime import date

report_period=date.fromisoformat(raw.report_period_string)  # NOT raw.report_period_string
```

This is common in parser → ORM pipelines (e.g., 13F-HR XML parsing, EDGAR filing metadata) where the parser returns strings but the ORM column is typed as `Date`.

### Pydantic `None` serializes to JSON `null` — Zod `.optional()` does NOT accept it

This is the most common bilateral-bridge validation failure. Pydantic serializes Python `None` to JSON `null`. On the Zod side, `.optional()` means "the key may be absent from the object" — it does NOT mean "the value may be null". When the backend sends `{"mc_playoff_odds": null}`, a Zod schema with `mc_playoff_odds: z.number().optional()` rejects it:

```
[{"code": "invalid_type", "expected": "number", "received": "null", "path": ["mc_playoff_odds"]}]
```

This commonly hits fields that are genuinely optional computed values: MC odds, narrative text, timestamps, rating deltas — anything that is `None` in Python when the computation hasn't run or the data is unavailable.

**Fix**: use `.nullable().optional()` for every field where the backend may send `null`:

```typescript
// WRONG — rejects null
narrative: z.string().optional(),
mc_playoff_odds: z.number().optional(),
mc_simulated_at: z.string().optional(),

// RIGHT — accepts absent (undefined) OR null
narrative: z.string().nullable().optional(),
mc_playoff_odds: z.number().nullable().optional(),
mc_simulated_at: z.string().nullable().optional(),
```

The mnemonic: `.optional()` = key may be missing. `.nullable()` = value may be null. You almost always want **both** for backend-optional fields: `.nullable().optional()`.

**Detection**: if a sync/fetch fails with no visible error on screen, always check the Zod validation message. Add a debug overlay during QA that surfaces `PARSE FAIL: ${error.message}` so you don't waste build cycles chasing stale-bundle symptoms when the real cause is a null-rejection.

### Computed projections are Pydantic-only (no SQLAlchemy model)

Some Zod schemas represent **computed projections** — shapes produced by queries that join multiple tables, not stored entities. These have Pydantic contracts but NO SQLAlchemy model.

Examples from stock-predictor:
- `GraphNode`, `GraphEdge`, `GraphNeighborhood` — produced by joining `relationships` + `instruments` + `relationship_sources`
- `CounterpartyResultRow`, `CounterpartyQuery` — inverse graph queries

The contract test still covers these (camelCase keys, round-trip, extra='forbid'). The SQLAlchemy bilateral test naturally skips them (no `Base` subclass to inspect).

**When to use this pattern:** If a shape is returned by an API endpoint but doesn't have its own table, it's a Pydantic-only contract. Don't create a dummy table just to have a SQLAlchemy model.

## References

- `references/alembic-async-setup.md` — async Alembic env.py template with sys.path fix
- `references/cursor-pagination-envelope.md` — PaginatedResponse[T] envelope contract, cursor encode/decode utility, FastAPI pagination dependency, repository pattern, and TanStack Query integration with backward-compatible hook shapes

## FastAPI integration

The contracts work directly as `response_model`:

```python
@router.get("/api/instruments", response_model=list[InstrumentContract])
async def list_instruments(db: AsyncSession = Depends(get_db)):
    instruments = await InstrumentRepository.list_instruments(db)
    return [InstrumentContract.model_validate(i.__dict__) for i in instruments]
```

FastAPI validates the response against the contract at runtime — if the repository returns data that doesn't match, the client gets a 500, not malformed JSON.

# Polars v1.40+ API Pitfalls

Common API traps when porting Pandas code to Polars 1.x.

## `pl.date_range` vs `pl.date_ranges`

### Wrong (eager, single range):
```python
pl.date_range(
    pl.col("Start Date"),
    pl.col("End Date"),
    interval="1d",
    eager=True,  # fails with column expressions
).alias("_days")
```
→ `ColumnNotFoundError: unable to find column "Start Date"`

### Correct (element-wise, per-row ranges):
```python
pl.date_ranges(
    pl.col("Start Date"),
    pl.col("End Date"),
    interval="1d",
).alias("_days")
```
`pl.date_ranges` (plural) creates one date range PER ROW. Combine with `.explode("_days")` to expand each range into individual rows.

## Expression Methods vs Module Functions

### Wrong (passing Expr to module function):
```python
pl.sum((pl.col("Allocation") > threshold).cast(pl.Int32))
```
→ `TypeError: invalid input for 'col': Expected str or DataType, got 'Expr'`

### Correct (chaining expression method):
```python
(pl.col("Allocation") > threshold).cast(pl.Int32).sum()
```

**Rule:** When you have an expression chain, use `.sum()`, `.mean()`, `.count()` as **methods on the expression**, not as `pl.sum(expr)`.

This applies to ALL aggregation methods:
- `(pl.col("x") > 1).sum()` ✓
- `pl.sum(pl.col("x") > 1)` ✗
- `pl.col("x").mean()` ✓
- `pl.mean(pl.col("x"))` ✗

## Schema-Aware `str.to_date`

### Wrong (blindly parsing already-parsed dates):
```python
pl.col("Start Date").str.to_date("%Y-%m-%d")
```
→ `SchemaError: invalid series dtype: expected String, got date`

### Correct (check dtype first):
```python
for col in [start_col, end_col]:
    if df[col].dtype in (pl.Utf8, pl.String):
        df = df.with_columns(pl.col(col).str.to_date("%Y-%m-%d", strict=False).alias(col))
```

## `group_by` Aggregation

### Wrong (Pandas-style nested agg):
```python
df.group_by("Department").agg([
    pl.len().alias("total"),
    pl.col("value").sum().alias("fte"),
])
```
Works but needs careful `.sum()` method chaining.

### Correct:
```python
df.group_by("Department").agg([
    pl.len().alias("total"),
    pl.sum("value").alias("fte"),  # module func with string arg is OK
])
```

**Rule:** `pl.sum("column_name")` works with string column names. `.sum()` as a method works on expressions. Don't mix `pl.sum(expr)` — use `expr.sum()` instead.

## Null Handling

- `fill_null(0.0)` — fills all nulls. Use after pivot or join.
- `drop_nulls(subset=[...])` — drops rows with nulls in specific columns. Critical before operations that can't handle nulls (arithmetic, date ranges).
- `is_not_null()` — for filtering. `df.filter(pl.col("x").is_not_null())`

## Date Range Expansion Memory

When using `pl.date_ranges(...).explode("_days")`, each row with N days generates N rows. For large datasets with long date ranges (e.g., 1 year = 365 rows per allocation), this can explode memory. Mitigation:
- Filter rows early with `date_cutoff`
- Only expand for weekly aggregation (then aggregate to weekly immediately)
- Use `max_weeks` parameter to limit time horizon on heatmaps

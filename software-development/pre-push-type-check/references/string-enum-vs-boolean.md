# Prisma String Enum vs Boolean Fields

## The trap

Some columns look like they should be booleans but are actually string enums in the Prisma schema:

```
cruise_line_inclusions:
  beverages: String  // "included" | "partial" | "not_included"
  gratuities: String  // same
  wifi: String         // same
  specialtyDining: String  // same
  excursions: String    // same
  butlerService: Boolean  // actual boolean
  minibarIncluded: Boolean  // actual boolean
  laundry: Boolean      // actual boolean
```

## Wrong (subagent pattern)

```tsx
const val = inclusions.beverages; // string "included"
{val === true ? '✓' : val === false ? '—' : '?'}  // always shows '?'
```

## Correct

```tsx
const isBool = typeof val === 'boolean';
isBool
  ? (val ? '✓' : '—')
  : val === 'included' ? '✓' : val === 'partial' ? '○' : '—';
```

## Scoring / counting

```tsx
// Count only full "included" values, plus boolean true
function inclusionCount(inclusions: any): number {
  return INCLUSION_COLUMNS.reduce((count, col) => {
    const val = inclusions[col.key];
    if (typeof val === 'boolean') return count + (val ? 1 : 0);
    return count + (val === 'included' ? 1 : 0);
  }, 0);
}
```

## Budget level

`cruise_line_demographics.budgetLevel` is also a `String` (text labels like "luxury", "premium"), NOT a number. Don't do arithmetic on it. Use localeCompare for sorting.

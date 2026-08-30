# Debugging AI Extraction from Booking Confirmation PDFs

Debugging poor AI extraction hit rates or missing-fields errors in booking upload flows. Applies to projects where PDF booking confirmations are run through an AI model (Haiku) for field extraction, then validated on the client and server.

## Investigation Pattern (3-phase)

### Phase 1 — See what the AI actually receives

The first question is always: what text does the PDF extractor produce? The AI only sees what `extractText()` returns, not what a human sees rendered.

```bash
python3 -c "
import pdfplumber
pdf = pdfplumber.open('<file.pdf>')
for i, page in enumerate(pdf.pages):
    t = page.extract_text()
    if t:
        print(f'--- PAGE {i+1} ---')
        print(t[:2000])
pdf.close()
"
```

If pdfplumber is unavailable, try `PyMuPDF` (`fitz`):
```bash
python3 -c "
import fitz
doc = fitz.open('<file.pdf>')
for i, page in enumerate(doc):
    print(f'--- PAGE {i+1} ---')
    print(page.get_text()[:2000])
doc.close()
"
```

**What to look for:**
- Is the text layout preserved? Multi-column PDFs often jumble text.
- Is the key booking info (booking #, traveler, dates, price, commission) present in the extracted text?
- Is there lots of noise from promotional content, sidebars, or footers that drowns out the actual booking data?
- Is the text too short (<10 chars) meaning the PDF is image-based and needs OCR?

### Phase 2 — Trace the extraction pipeline

Map the full flow end-to-end:

1. **Upload route:** `POST /api/bookings/extract/` (or similar) — file validation, text extraction, AI call, result parsing
2. **Text extractor:** typically PDF → raw text via `pdfjs-dist` or similar
3. **AI prompt:** what the system prompt asks the model to extract. Key to read — it sets the model's expectations.
4. **AI model used:** confirm which model is called (e.g., Haiku 4.5 for cost efficiency, Sonnet for accuracy)
5. **Response parser:** how the AI's JSON response is validated and normalized (numeric coercion, null handling)
6. **Supplier matcher:** the algorithm (Dice coefficient on bigrams, substring containment, etc.) and its threshold for returning a match
7. **Duplicate checker:** whether booking numbers already exist in the DB
8. **Customer matcher:** fuzzy match on traveler name vs known customers

### Phase 3 — Trace the validation

After extraction, the user reviews entries in a table and clicks "Create Bookings". Two validation layers run:

**Client-side validation** (in the upload page):
```typescript
const invalid = selectedEntries.filter(
  (e) =>
    !e.fields.booking_number ||
    !e.fields.lead_traveler_last_name ||
    !(e.supplierId || e.matchedSupplierId) ||
    e.fields.package_price === null ||
    e.fields.commission_amount === null
);
```

**Server-side validation** (in the import route, typically Zod):
```typescript
const schema = z.object({
  booking_number: z.string().min(1),
  supplier_id: z.string().min(1),
  lead_traveler_last_name: z.string().min(1),
  package_price: z.number().min(0),
  anticipated_commission: z.number().min(0),
});
```

If the client-side check fails, the error toast says "missing required fields" but does NOT highlight which row or which field — the user must hunt.

## Common Root Causes

### "Supplier match ratio is dismal"
- **Suppliers not in DB.** The algorithm can only match against registered suppliers. New marketplace platforms (Viator, TAAP, Expedia) or tour operators (Elife Limo, Insight Vacations) won't match until the user adds them. Not a matcher bug — a data completeness issue.
- **Dice coefficient threshold.** Default is 0.4 minimum for any match, 0.6 for medium, 0.9 for high. Short names or names with abbreviations ("Viator" vs "Viator, Inc.") can fall below threshold if substring containment isn't boosting them.
- **AI extracts wrong supplier name.** Some PDFs name the marketplace (Viator) rather than the actual tour operator (e.g., "Elife Limo"). The prompt may ask for "supplier/tour operator name" which is ambiguous.
### "Missing fields error despite filling"

- **Price/commission aren't in the PDF.** Some booking types (transfers, tours, activities) don't show the package price or commission explicitly — especially on marketplace aggregator pages. The AI returns null, and the user may not know the right values.
- **Non-booking PDFs.** Files like hotel contact lists, itineraries, or confirmation references aren't actual booking documents and have zero booking data.
- **Viator/aggregator PDFs are noise-heavy.** The text extraction picks up promotional rows for other tours ("Customers who also bought…") which drowns out the booking-specific info. The AI may hallucinate prices from the wrong section.
- **Batch validation blocks ALL entries.** This is the most common hidden cause. The client-side validation checks ALL selected entries and aborts the entire batch if ANY one has a missing field. The user sees "N bookings missing required fields" but the toast covers up which row caused it, and valid entries that would have created fine never get submitted. The fix is to separate valid from invalid, submit only the valid ones, and keep the invalid ones in the review table with per-field red highlighting.

### Fix pattern: partial-success batch validation with field-level highlighting

When a user selects multiple entries and clicks Create, the system should process what it can and flag what it can't:

```typescript
// 1. Validate per-entry, not as a group
const getValidationErrors = (e: ExtractionEntry): Record<string, string> | null => {
  const errors: Record<string, string> = {};
  if (!e.fields.booking_number) errors.booking_number = "Required";
  if (!e.fields.lead_traveler_last_name) errors.lead_traveler_last_name = "Required";
  if (!(e.supplierId || e.matchedSupplierId)) errors.supplier = "Required";
  if (e.fields.package_price === null) errors.package_price = "Required";
  if (e.fields.commission_amount === null) errors.commission_amount = "Required";
  return Object.keys(errors).length > 0 ? errors : null;
};

const validEntries = selectedEntries.filter(e => !getValidationErrors(e));
const invalidEntries = selectedEntries
  .filter(e => getValidationErrors(e))
  .map(e => ({ ...e, validationErrors: getValidationErrors(e)!, selected: true }));

// 2. Process valid entries; keep invalid ones for re-edit
if (validEntries.length > 0) {
  const result = await fetch("/api/bookings/import", { body: JSON.stringify({ bookings }) });
  // toast: "Created X bookings. Y skipped — fix highlighted fields and submit again"
}

// 3. Replace entries state: non-selected entries + invalid entries
setEntries([
  ...entries.filter(e => !selectedEntries.some(s => s.filename === e.filename)),
  ...invalidEntries,
]);
// Redirect only if everything went through
if (invalidEntries.length === 0) router.push("/bookings");
```

**Field-level highlighting (ExtractionEntry type addition):**
```typescript
export interface ExtractionEntry {
  // ...existing fields
  validationErrors?: Record<string, string> | null;
}
```

Each input applies: `className={'... ' + (entry.validationErrors?.fieldName ? 'ring-2 ring-destructive' : '')}`. The error ring clears on edit via the onChange handler.

## Pitfalls

1. **Assuming the AI saw what you see.** The PDF text extraction layer is the bottleneck — Viator PDFs look clean visually but extract as noise+ads. Always extract the raw text first.
2. **Assuming the supplier exists.** The matcher is not magical. If the name isn't in the DB, nothing matches. Verify supplier existence first.
3. **Generic client-side error messages.** The "missing fields" toast doesn't tell the user which row or which field is the problem. For debugging, you can add a temporary `console.log(invalid)` to see exactly which entries fail and which fields are null.
4. **Confusing client vs server validation.** The client-side check fires FIRST and must pass before the server-side Zod runs. If a field passes client-side but fails server-side (e.g., `""` for supplierId is falsy in JS but a server UUID validation might be different), the error looks different.

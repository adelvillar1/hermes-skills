# T-PESS 5-Domain Pipeline — Reference Implementation

## Context

The TTESS application (Next.js + Prisma + Postgres) extends its teacher evaluation system to support T-PESS principal evaluations. The AI pipeline follows the domain-chunked generation pattern but with 5 concurrent calls (one per T-PESS domain) instead of the existing 4 (T-TESS). Each domain call returns all its indicators with individual ratings and detailed justifications following a specific 3-element pattern.

## Key Differences from 4-Domain Pattern

| Aspect | 4-Domain (T-TESS) | 5-Domain (T-PESS) |
|--------|-------------------|-------------------|
| Concurrency | 4 calls | 5 calls |
| Per-call output | Dimensions (4-5 each) | Indicators with ratings + justifications (4-6 each) |
| Group 1 metadata | SLO, Closing Narrative, Tayebi template | Executive summary, growth plan, evidence tables |
| Vision extraction | Baseline PDF stamped over model output | No baseline concept — pure evidence-based |
| Schema layout | `dimensions` array (flat) | `indicators` array + `evidenceSummary`, `strength`, `growthOpportunities` per domain |
| Rating philosophy | Standard T-TESS rubric | Refined: "Proficient not default", 3-element justification litmus test |

## File Locations

- `lib/ai/schemas/tpess-result.ts` — Zod schemas
- `lib/ai/prompts/tpess-system.ts` — System prompt with rating philosophy
- `lib/ai/prompts/tpess-user.ts` — Domain-scoped prompt assembler
- `lib/ai/tpess-pipeline.ts` — 5-domain concurrent pipeline
- `lib/docx/tpess-evaluation.ts` — DOCX generator with complex tables
- `lib/data/tpess-rubric.md` — Static rubric reference file

## Domain Indicator Counts (Correct: 20 indicators, not 23)

The T-PESS 2020 Updated Rubric has exactly 20 indicators. The original implementation incorrectly used 23 — see [Section 0: Critical Fix](#section-0-critical-fix-incorrect-rubric-structure) below for the full correction delta.

```typescript
export const TPESS_DOMAIN_INDICATORS: Record<number, string[]> = {
  1: ["1.1", "1.2", "1.3", "1.4", "1.5"],          // 5 indicators
  2: ["2.1", "2.2", "2.3", "2.4"],                 // 4 indicators
  3: ["3.1", "3.2", "3.3", "3.4"],                 // 4 indicators
  4: ["4.1", "4.2"],                                // 2 indicators
  5: ["5.1", "5.2", "5.3", "5.4", "5.5"],          // 5 indicators
};
```

**Changes from wrong (23) to correct (20):**
- **Domain 1:** Removed indicator 1.6 "Core Leadership Tasks" (did not exist in official rubric). Renamed 1.2 to "Schedules for Core Leadership Tasks" (was incorrectly "High-Performing Instructional Leadership Team" — that belongs in D5).
- **Domain 2:** Domain renamed from "Human Capital" to "Effective, Well-Supported Teachers". Indicators 2.1→"Human Capital" (was "Talent Recruitment and Retention"), 2.2→"Talent Management" (was "Staff Evaluation and Development").
- **Domain 3:** Domain renamed from "Executive Leadership" to "Positive School Culture". All 4 indicators renamed: 3.1→"Safe Environment and High Expectations" (was "Communication and Community Engagement"), 3.2→"Behavioral Expectations and Management Systems" (was "Family and Parent Involvement"), 3.3→"Proactive and Responsive Student Support Services" (was "Student Support Services"), 3.4→"Involving Families and Community" (was "Entrepreneurial Operations").
- **Domain 4:** Domain renamed from "Curriculum and Instruction" to "High-Quality Curriculum". Reduced from 4 indicators to 2 — removed 4.3 "Instructional Resources and Support" and 4.4 "Differentiated Instruction and Support for Diverse Learners". Renamed 4.1→"Standards-based Curricula and Assessments" and 4.2→"Instructional Resources and Professional Development" (was "Data-Driven Instruction" — moved to D5.4).
- **Domain 5:** Domain renamed from "Positive School Culture" to "Effective Instruction". Renamed 5.1→"High-Performing Instructional Leadership Team" (moved from original D1), 5.2→"Objective-Driven Plans" (was "Culture of High Expectations"), 5.3→"Effective Classroom Routines and Instructional Strategies" (was "Behavior Expectations and Management Systems"), 5.4→"Data-Driven Instruction" (was "Social and Emotional Learning"), 5.5→"Response to Intervention" (shortened from "Response to Intervention (RTI / MTSS)").

## Per-Domain Chunk Schema

The richer pattern — each group produces its own metadata, not just data rows:

```typescript
const DomainChunkSchema = z.object({
  domainId: z.number().int().min(1).max(5),
  domainName: z.string(),
  domainOverview: z.string(),          // 1-2 sentence overview
  indicators: z.array(IndicatorRating), // 4-6 indicators depending on domain
  evidenceSummary: z.string(),          // 2-3 paragraphs with citations
  strengths: z.array(z.string()).min(3),
  growthOpportunities: z.array(z.string()).min(2),
});
```

This avoids a separate meta-call to generate section headers/overviews — each chunk is self-contained and feeds a standalone section of the final DOCX.

## Concurrent Dispatch (5 calls)

```typescript
const [p1, p2, p3, p4, p5] = await Promise.all([
  buildTPESSPrompt(principalName, documents, 1),
  buildTPESSPrompt(principalName, documents, 2),
  buildTPESSPrompt(principalName, documents, 3),
  buildTPESSPrompt(principalName, documents, 4),
  buildTPESSPrompt(principalName, documents, 5),
]);

const [d1raw, d2raw, d3raw, d4raw, d5raw] = await Promise.all([
  runTPESSDomainWithRetry(1, p1, modelId),
  runTPESSDomainWithRetry(2, p2, modelId),
  runTPESSDomainWithRetry(3, p3, modelId),
  runTPESSDomainWithRetry(4, p4, modelId),
  runTPESSDomainWithRetry(5, p5, modelId),
]);
```

## Array-Name Normalization

The TPESS pipeline normalizes both at the Ollama fallback path and at the merge step:

```typescript
// In the Ollama JSON fallback handler and tool-call handler:
const normalized = args as Record<string, unknown>;
if (!normalized.indicators && normalized.indicator && Array.isArray(normalized.indicator)) {
  normalized.indicators = normalized.indicator;
  delete normalized.indicator;
}
```

## Tool Definition (per-domain)

Each domain gets its own tool definition with `minItems`/`maxItems` matching its indicator count:

```typescript
function buildTPESSToolDef(domain: number) {
  const indicatorCount = TPESS_DOMAIN_INDICATORS[domain].length;
  return {
    name: "submit_domain_analysis",
    description: `Submit Domain ${domain} (${TPESS_DOMAIN_NAMES[domain]}) with ${indicatorCount} indicators.`,
    input_schema: {
      type: "object",
      properties: {
        domainId: { type: "number" },
        domainName: { type: "string" },
        domainOverview: { type: "string" },
        indicators: {
          type: "array",
          description: `${indicatorCount} indicator ratings for Domain ${domain}`,
          items: {
            type: "object",
            properties: {
              indicatorId: { type: "string" },
              indicatorName: { type: "string" },
              rating: { type: "string", enum: ["Distinguished", ...] },
              justification: { type: "string" },
            },
            required: ["indicatorId", "indicatorName", "rating", "justification"],
          },
        },
        evidenceSummary: { type: "string" },
        strengths: { type: "array", items: { type: "string" } },
        growthOpportunities: { type: "array", items: { type: "string" } },
      },
      required: ["domainId", "domainName", "domainOverview", "indicators", "evidenceSummary", "strengths", "growthOpportunities"],
    },
  };
}
```

## Rating Philosophy (T-PESS Specific)

Embedded in both the system prompt and user prompt — not a general pattern but relevant for any evaluation-style chunked generation:

- **Proficient is NOT a default** — if evidence shows commitment/creativity, rate Accomplished
- Each justification requires 3 elements: (1) what principal does well, (2) what would elevate to Distinguished, (3) why current rating is fair
- **Growth areas are "extension, not repair"** — frame as building on good practice
- **No passive voice, no hedging** — "She convened digs" not "Data digs were held"

## Aggregator / Meta-Call Pattern

After all 5 domain calls complete, the pipeline makes one additional AI call called the **aggregator**. This call receives all 5 domain results as context and synthesizes cross-cutting sections that no single domain call can produce:

**What the aggregator generates:**
- **Executive Summary** — 3-4 paragraph overall narrative with ~4 enumerated strengths, ~3 enumerated growth areas
- **Evidence Artifact Summary** — Table mapping each evidence source to what it demonstrates across domains
- **Professional Growth Plan** — 3-5 goals, each with title, action, support, evidence of success
- **Overall Summative Assessment** — 8 sub-sections: holistic assessment, domain summary, ratings distribution, interpretation, domain-by-domain trajectory, revised ratings distribution, forward-looking trajectory, note on evidence completeness

**Architecture:**

```
5 domain calls (concurrent)         6th aggregator call
┌─────────────┐                    ┌──────────────────┐
│ Domain 1    │──┐                 │ executiveSummary │
│ (5 ind.)    │  │                 │ evidenceArtifact │
├─────────────┤  │                 │ growthPlan       │
│ Domain 2    │──┤                 │ overallAssessment│
│ (4 ind.)    │  │  ┌──────────────┘ (10 fields)     │
├─────────────┤  ├──┤                                 │
│ Domain 3    │──┤  └──────────────┐                  │
│ (4 ind.)    │  │                 │ ↕ fallback when  │
├─────────────┤  │                 │   AI fails       │
│ Domain 4    │──┤                 └──────────────────┘
│ (2 ind.)    │  │
├─────────────┤  │     METADATA (deterministic)
│ Domain 5    │──┤     evidenceSources ← documents[]
│ (5 ind.)    │  │     limitationsNote ← boilerplate
└─────────────┘  │
                 └→ Merge → Complete Result (validated)
```

**Tool definition for the aggregator:**

```typescript
function buildTPESSAggregatorToolDef() {
  return {
    name: "submit_synthesis",
    input_schema: {
      type: "object",
      properties: {
        executiveSummary: { type: "string" },
        evidenceArtifactSummary: { type: "array", items: { /* source, type, demonstrates */ } },
        growthPlan: { type: "array", items: { /* goalNumber, title, action, support, evidenceOfSuccess */ } },
        holisticAssessment: { type: "string" },
        domainSummary: { type: "string" },
        ratingsDistribution: { type: "string" },
        ratingsInterpretation: { type: "string" },
        domainTrajectory: { type: "string" },
        revisedRatingsDistribution: { type: "string" },
        trajectory: { type: "string" },
        evidenceNote: { type: "string" },
      },
      required: [/* all 11 fields */],
    },
  };
}
```

**Prompt design for the aggregator:**

The aggregator's system prompt extends the base T-PESS appraiser prompt with synthesis-specific instructions. The user prompt packages all 5 domain results as structured text blocks (indicator ratings + justifications + evidence summaries + strengths + growth opportunities) plus the document list.

**Retry logic:** Same pattern as domain calls but with 3 attempts (not 4, since the context is larger and the task is synthesis, not individual generation). Uses targeted retry on missing fields: `"YOUR PREVIOUS RESPONSE WAS INCOMPLETE. Missing: executiveSummary, growthPlan (min 3 goals)."`

### Deterministic Merge Helpers

Not everything needs AI. These fields are built from document metadata:

```typescript
function buildEvidenceSources(documents: DocumentInput[]): Array<{source; type; status}> {
  return documents.map(d => ({
    source: d.filename,
    type: d.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    status: "Reviewed",
  }));
}

const limitationsNote = `Now Reviewed: All ${documents.length} evidence source(s) were reviewed...`;
```

### Fallback Aggregator

When the AI aggregator fails all 3 retries, a deterministic fallback produces readable (albeit generic) content so the report is never blank:

```typescript
function buildFallbackAggregatorOutput(domains, documents): AggregatorOutput {
  // Build executive summary from domain overviews
  // Build evidence artifact summary from document list
  // Build growth plan (3-5 goals) from unique growth opportunities across domains
  // Build overall assessment with rating counts and domain trajectory
  // If fewer than 3 growth goals exist, pad with 3 standard goals
}
```

This is a last-resort safeguard — not as good as AI-generated content, but prevents a broken report.

### Anthropic SDK Tool Type Compatibility

The Anthropic SDK's `InputSchema` requires:
- `type?: "object"` (marking optional in interface, but actual value must be `"object"`)
- `properties?: { [key: string]: unknown }`
- `required?: string[]`
- `[k: string]: unknown` — index signature allowing extra keys

When defining a shared tool-def type for both domain calls and the aggregator call, the interface must include the index signature to satisfy the SDK's constraint:

```typescript
interface TPESSToolInputSchema {
  type: "object";
  properties?: Record<string, unknown>;
  required?: string[];
  [k: string]: unknown;  // Required for Anthropic SDK compatibility
}
```

Without the index signature, TypeScript rejects the tools array with "Types of property 'input_schema' are incompatible — Index signature for type 'string' is missing." Both `buildTPESSToolDef` and `buildTPESSAggregatorToolDef` return objects compatible with this interface.

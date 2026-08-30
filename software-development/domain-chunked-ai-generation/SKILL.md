---
name: domain-chunked-ai-generation
description: Use when an LLM struggles with too many output fields (8+) in a single tool call. Split the work into concurrent scoped calls (one per logical group/domain), merge results, and post-merge stamp values from an independent source of truth.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [ai, llm, dispatch, chunked, retry, normalization, concurrent]
    related_skills: [writing-plans, dual-emit-llm-generation]
---

# Domain-Chunked AI Generation

## Overview

When an LLM needs to produce a large structured output with 8+ fields (e.g., 16 teacher evaluation dimensions, 30 product attributes, 50 data rows), a single tool call often produces errors: hallucinated field names, missing fields, inconsistent values. The model's attention fragments across too many output slots.

The solution is **domain chunking**: split the output into logical groups, fire one concurrent call per group, then merge and apply post-processing. Each call has a smaller schema (3-5 fields), so the model stays precise.

This skill covers the full pattern: schema splitting, concurrent dispatch, per-call retry with targeted feedback, field-name normalization across model variants, post-merge deterministic value stamping, and the **aggregator/meta-call pattern** for cross-cutting synthesis after the chunked calls complete.

## When to Use

- An LLM call produces a JSON array with 8+ items and the model frequently omits or corrupts items
- The output has a natural grouping (domains, categories, sections, logical partitions)
- You have an independent source of truth for some output fields (e.g., vision extraction, database lookup) that should override the model's inference
- You're working with models that rotate their output field names between runs (Kimi, Gemini, etc.)
- The model's tool-calling behavior is unreliable and needs a JSON-mode fallback

**Don't use for:**
- Outputs with 1-5 simple fields (single call is simpler and cheaper)
- Outputs that need BOTH structured data AND narrative from the same context (use `dual-emit-llm-generation` — single-call dual output, no merge needed)
- Streaming-only use cases (chunking adds merge complexity)
- Tasks where the groups are interdependent (each call needs context from other calls)

## Architecture

```
Input documents
    │
    ├── Vision Extraction (independent source of truth)
    │   └── Extracted ratings dict: { "1.1": "Accomplished", ... }
    │
    └── buildPrompt() x4 (one per domain)
        │
        ├── Call Domain 1 ── retry loop ──┐
        ├── Call Domain 2 ── retry loop ──┤ (4 concurrent)
        ├── Call Domain 3 ── retry loop ──┤
    └── Call Domain 4 ── retry loop ──┘
            │
            ▼
        Per-domain validation
            │
            ▼
    Merge all dimensions
            │
            ▼
    Post-merge baseline stamping
    (overwrite model values with vision-extracted ones)
```

## Implementation Steps

### 1. Schema Design

Define per-group Zod schemas instead of one giant schema.

**Simple pattern** (groups 2-N get only the repeated items):

```typescript
// Group 2-N: dimensions/data only
const DomainChunkSchema = z.object({
  dimensions: z.array(DimensionResultSchema).min(1),
});
```

**Richer pattern** (each group also produces metadata for its section):

```typescript
const DomainChunkSchema = z.object({
  domainId: z.number().int(),
  domainName: z.string(),
  domainOverview: z.string().min(1),
  indicators: z.array(IndicatorRating).min(1),
  evidenceSummary: z.string(),
  strengths: z.array(z.string()).min(3),
  growthOpportunities: z.array(z.string()).min(2),
});
```

Use the richer pattern when each chunk feeds a standalone section in the final output (e.g., one domain section per chapter of a report). This avoids a separate meta-call to generate section headers, overviews, and summaries — each chunk is self-contained.

Define the dimension mapping and canonical names:

```typescript
const DOMAIN_DIMENSIONS: Record<number, string[]> = {
  1: ["1.1", "1.2", "1.3", "1.4"],
  2: ["2.1", "2.2", "2.3", "2.4", "2.5"],
  // ...
};

export const DIMENSION_NAMES: Record<string, string> = {
  "1.1": "Standards and Alignment",
  "1.2": "Data and Assessment",
  // ...used as final fallback in normalization
};
```

Build per-domain tool definitions with correct minItems/maxItems:

```typescript
function buildDomainToolDef(domain: number) {
  const dimIds = DOMAIN_DIMENSIONS[domain];
  return {
    name: "submit_domain_analysis",
    description: `Submit Domain ${domain}. Return exactly ${dimIds.length} dimensions: ${dimIds.join(", ")}.`,
    input_schema: {
      type: "object",
      required: domain === 1 ? ["teacherName", ..., "dimensions"] : ["dimensions"],
      properties: {
        dimensions: {
          type: "array",
          minItems: dimIds.length,
          maxItems: dimIds.length,
          description: `Exactly ${dimIds.length} dimensions for Domain ${domain}: ${dimIds.join(", ")}. No other dimensions.`,
          items: { /* dimension schema */ },
        },
      },
    },
  };
}
```

### 2. Concurrent Dispatch

Fire all domain calls concurrently using `Promise.all`. Build prompts in parallel too.

```typescript
const [p1, p2, p3, p4] = await Promise.all([
  buildPrompt(teacherName, documents, extractedRatings, 1),
  buildPrompt(teacherName, documents, extractedRatings, 2),
  buildPrompt(teacherName, documents, extractedRatings, 3),
  buildPrompt(teacherName, documents, extractedRatings, 4),
]);

const [d1raw, d2raw, d3raw, d4raw] = await Promise.all([
  runDomainWithRetry(1, p1, modelId),
  runDomainWithRetry(2, p2, modelId),
  runDomainWithRetry(3, p3, modelId),
  runDomainWithRetry(4, p4, modelId),
]);
```

### 3. Per-Domain Retry Loop

Each domain call has its own retry with targeted feedback.

```typescript
const MAX_DOMAIN_ATTEMPTS = 4;

async function runDomainWithRetry(domain, prompts, modelId) {
  const toolDef = buildDomainToolDef(domain);
  let userPrompt = prompts.userPrompt;

  for (let attempt = 1; attempt <= MAX_DOMAIN_ATTEMPTS; attempt++) {
    try {
      // Call model (Anthropic or Ollama)
      let raw = await callDomain(systemPrompt, userPrompt, modelId, toolDef);

      // Handle stringified JSON (model wrapped dimensions in quotes)
      if (typeof raw.dimensions === "string") {
        try { raw.dimensions = JSON.parse(raw.dimensions); }
        catch { throw new Error("SCHEMA: dimensions was stringified with unescaped quotes"); }
      }

      // Per-dimension validation
      const failures = checkDomainDimensions(domain, raw.dimensions);
      if (failures.length === 0) return raw;

      // Append targeted retry instruction
      userPrompt += "\n\n" + formatFailures(domain, failures);
    } catch (err) {
      // Rate-limit backoff
      if (msg.includes("too many concurrent") || msg.includes("rate limit")) {
        await new Promise(r => setTimeout(r, attempt * 15_000));
      }
      userPrompt += "\n\n" + formatErrorFeedback(err);
    }
  }
  throw new Error(`Domain ${domain} failed after ${MAX_DOMAIN_ATTEMPTS} attempts`);
}
```

#### Validation checks per dimension

```typescript
function checkDomainDimensions(domain, dims) {
  const expected = DOMAIN_DIMENSIONS[domain];
  const failures = [];

  // Missing dimensions
  for (const id of expected)
    if (!gotIds.has(id))
      failures.push(`Missing dimension ${id}.`);

  // Empty narratives
  for (const dim of dims)
    if (!dim.narrative?.trim())
      failures.push(`Dimension ${dim.id}: narrative is empty.`);

  // Missing quoted evidence (text inside "")
  if (!DOMAIN_QUOTE_RE.test(dim.narrative))
    failures.push(`Dimension ${dim.id}: no verbatim quoted evidence.`);

  return failures;
}
```

### 4. Field-Name Normalization

Models (especially Kimi, Gemini) rotate field names between runs. Use a comprehensive alias map + combined-field parsing + canonical lookup.

```typescript
function normalizeArgs(raw: Record<string, unknown>): Record<string, unknown> {
  if (!Array.isArray(raw.dimensions)) return raw;

  // Log raw first dimension for monitoring new variants
  console.log("[normalize] raw keys:", Object.keys(raw.dimensions[0]));
  console.log("[normalize] raw dim[0]:", JSON.stringify(raw.dimensions[0]));

  return {
    ...raw,
    dimensions: raw.dimensions.map(d => {
      // Handle combined field: "1.1 — Standards and Alignment"
      const combinedRaw = d.dimension || d.dimensionName || "";
      const combinedMatch = /^(\d+\.\d+)\s*[—–\-]?\s*(.*)/.exec(combinedRaw);
      const idFromCombined = combinedMatch?.[1];
      const nameFromCombined = combinedMatch?.[2]?.trim();

      const resolvedId = d.id ?? d.dimensionId ?? d.dimension_id
        ?? d.dimensionCode ?? d.code ?? d.number ?? idFromCombined;

      return {
        ...d,
        id: resolvedId,
        name: d.name ?? d.dimension_name ?? d.dimensionTitle ?? d.title
          ?? nameFromCombined
          ?? (resolvedId ? DIMENSION_NAMES[resolvedId] : undefined),
        narrative: d.narrative ?? d.evidenceNarrative ?? d.evidence ?? d.text ?? d.content,
        domain: typeof d.domain === "number" ? d.domain
          : d.domain ? parseInt(String(d.domain).match(/\d+/)?.[0] ?? "0")
          : resolvedId ? parseInt(String(resolvedId).split(".")[0])
          : undefined,
      };
    }),
  };
}
```

### 5. Post-Merge Value Stamping

After merging dimensions from all groups, overwrite specific fields from an independent source of truth (e.g., vision extraction, database lookup). The model's inferred value is discarded.

```typescript
const ratedDimensions = allDimensions.map((dim) => {
  const extracted = extractedRatings[dim.id];
  if (extracted && extracted !== dim.baselineRating) {
    console.log(`[stamp] ${dim.id}: model=${dim.baselineRating} → extracted=${extracted}`);
  }
  return extracted ? { ...dim, baselineRating: extracted } : dim;
});
```

### 7. Aggregator / Meta-Call Pattern (Cross-Cutting Synthesis)

When each domain chunk can produce per-domain metadata (overviews, evidence summaries, strengths) but the final output requires cross-cutting sections that no single chunk can author (executive summary, growth plan, overall assessment), add a **post-merge aggregator call**.

**Architecture (after all domain calls complete):**

```
Domain 1 ──┐
Domain 2 ──┤  Merge domain results
Domain 3 ──┤       │
Domain 4 ──┤       │
Domain 5 ──┘       │
                   ▼
               Aggregator call
               (single AI call, all domains as context)
                   │
                   ▼
               Exec summary, growth plan,
               overall assessment, artifact table
```

**When to use:**
- The output document has both per-section content (domain evaluations) and cross-cutting content (executive summary, growth plan, overall conclusion)
- The cross-cutting sections require synthesizing information from multiple domain results
- Each domain chunk is self-contained (no domain depends on another), but the final report needs a unified narrative

**When NOT to use:**
- Each section is standalone with no cross-cutting content (merge is sufficient)
- The cross-cutting content can be generated deterministically from domain metadata (e.g., "evidence sources" table from document filenames — no AI needed)
- Token budget or latency is critical (aggregator adds one more round-trip)

**Implementation pattern:**

```typescript
// 1. First, build evidence sources from document metadata (deterministic, no AI)
const evidenceSources = documents.map(d => ({
  source: d.filename,
  type: formatType(d.type),
  status: "Reviewed",
}));

// 2. Run aggregator call after domain calls succeed
const aggregatorResult = await runAggregatorWithRetry(
  principalName, domains, documents, modelId
);

// 3. Merge: deterministic sources + AI-generated synthesis + domain results
const merged = {
  ...domainResults,
  evidenceSources,  // From metadata
  limitationsNote,  // Standard boilerplate
  executiveSummary: aggregatorResult.executiveSummary,
  evidenceArtifactSummary: aggregatorResult.evidenceArtifactSummary || [],
  growthPlan: aggregatorResult.growthPlan || [],
  holisticAssessment: aggregatorResult.holisticAssessment,
  domainSummary: aggregatorResult.domainSummary,
  ratingsDistribution: aggregatorResult.ratingsDistribution,
  // ...
};
```

**Fallback aggregator:** When the AI aggregator fails all retries, produce a deterministic fallback from domain data so the output is never blank:

```typescript
function buildFallbackAggregatorOutput(domains, documents) {
  // Build executive summary from domain overviews concatenated
  // Build evidence artifact summary from document filenames
  // Build growth plan from unique growth opportunities across domains
  // Build overall assessment from rating counts and domain trajectory
}
```

The fallback produces readable (though generic) content — better than empty sections.

**Tool def type compatibility (Anthropic SDK):** When sharing one tool-call function between domain calls and the aggregator call, define the tool type interface including the Anthropic SDK's required index signature:

```typescript
interface TPESSToolInputSchema {
  type: "object";
  properties?: Record<string, unknown>;
  required?: string[];
  [k: string]: unknown;  // Index signature — required by Anthropic SDK's InputSchema
}

interface TPESSToolDef {
  name: string;
  description: string;
  input_schema: TPESSToolInputSchema;
}
```

Without the `[k: string]: unknown` index signature, TypeScript errors with "Index signature for type 'string' is missing in type 'TPESSToolInputSchema'" — even when both tool defs are structurally compatible.

### 8. Tool Calling vs JSON Fallback

Anthropic models use `tool_use` with `tool_choice: { type: "any" }` for guaranteed structured output.

Ollama models attempt native tool calling first, then fall back to `format: "json"` + explicit schema prompt if no `tool_calls` received:

```typescript
// Attempt 1: native tool calling with streaming
const stream = await client.chat({ model, messages, tools: [toolDef], stream: true });

// If no tool_calls in response...
// Fallback: format: "json" + explicit schema reminder
const fallback = await client.chat({
  model,
  format: "json",
  messages: [...messages, { role: "user", content: "You MUST respond with valid JSON matching the submit_tool schema." }],
});
```

Use streaming for Ollama — it keeps connections alive during long generations (necessary on Railway/Fargate where NAT gateways drop idle TCP connections).

### 9. Prompt Isolation Per Group

When chunking, each group's prompt must:
- Scope the model to its specific dimensions only
- Tell the model NOT to include other groups' fields
- Only include metadata (SLO, closing narrative) in group 1 / the first group

```typescript
const scopeBlock = domain
  ? `SCOPE: You are analyzing ONLY Domain ${domain} — dimensions ${DIM_IDS[domain].join(", ")}.
Return exactly ${DIM_IDS[domain].length} dimensions. Do NOT include dimensions from other domains.
${domain !== 1 ? "The SLO and Closing Narrative are handled in a separate call — skip them." : "Include the SLO and Closing Narrative."}`
  : "";
```

## Common Pitfalls

1. **Too many concurrent calls.** 4 concurrent calls works; 8+ may hit rate limits or API contention. Use rate-limit backoff (`attempt × 15s`) when hitting 429s, and start with fewer groups if the model provider is aggressive with throttling.

2. **Combined-field parsing edge cases.** Kimi sometimes returns a combined field like `"1.1 — Standards and Alignment"` with em-dashes (`—`), en-dashes (`–`), or regular hyphens. The regex `^(\\d+\\.\\d+)\\s*[—–\\-]?\\s*(.*)` handles all three. Always log the raw first dimension to detect new variants.

3. **Plural vs singular array field names.** Some models return `indicators` while others return `indicator` (singular) for the same array. Also: `dimensions` vs `dimension`, `items` vs `item`, `ratings` vs `rating`. Normalize at every API entry point — the alias varies by model version, not by provider.

```typescript
// Canonical normalization pattern — apply after both tool-call and JSON-fallback paths:
function normalizeArrayField(raw: Record<string, unknown>, singular: string, plural: string): Record<string, unknown> {
  if (!raw[plural] && raw[singular] && Array.isArray(raw[singular])) {
    raw[plural] = raw[singular];
    delete raw[singular];
  }
  return raw;
}

// Usage:
normalized = normalizeArrayField(normalized, "indicator", "indicators");
normalized = normalizeArrayField(normalized, "dimension", "dimensions");
normalized = normalizeArrayField(normalized, "item", "items");
```

The singular-variant switch happens because models auto-pluralize field names based on their training data. Kimi models (k2.5, k2.6) are especially prone to using singular array names. Log the raw first element keys to detect new variants in production.

3. **Stringified dimensions.** Sonnet occasionally returns `dimensions` as a JSON-quoted string instead of an array literal. Catch this before Zod parsing: `typeof raw.dimensions === "string"` → try `JSON.parse()`. On parse failure (unescaped quotes in narrative text), throw a specific `SCHEMA:` error so the retry instruction is targeted.

4. **Retry feedback must be specific.** Generic "please try again" doesn't help. Include exact dimension IDs that are missing, the specific error message, and a concrete example of what a correct response looks like. The model needs to know *what* to fix.

5. **Prompt bloat on retries.** Appending retry instructions to the user prompt lengthens it each attempt. Keep retry messages concise (2-3 sentences) to avoid hitting context limits on retry 3-4.

6. **Post-merge validation must be strict.** Cross-group validation catches issues per-group retry missed (e.g., SLO rating missing when domain 1 passed but the merged result has a gap). Run final validation after merge.

7. **Forgetting to skip Tayebi template for non-first groups.** If your prompt loads a reference template document, only load it for group 1. Groups 2-N don't need it and loading it wastes tokens.

8. **System prompt in a separate file for complex pipelines.** Don't embed a 150-line system prompt inside the pipeline module. Extract it to `lib/ai/prompts/<name>-system.ts` and import it. This keeps the pipeline code focused on orchestration and makes the prompt independently reviewable/testable.

9. **Anthropic SDK tool type compatibility.** When sharing a tool-call function across different tool definitions (domain call + aggregator call), the shared type must include Anthropic's `[k: string]: unknown` index signature on `InputSchema`. Without it, TypeScript rejects structurally compatible tool defs because the SDK's type uses an index signature. Use the interface pattern in §7 above.

10. **Aggregator prompt bloat.** The aggregator receives ALL domain results as context — each with indicators, justifications, evidence summaries, strengths, growth opportunities. This can be token-heavy (15K+ tokens for 5 domains with 4-6 indicators each). Keep retry messages concise (1-2 sentences) and set max_retries to 3 (not 4) to avoid exhausting token budgets.

11. **Deterministic vs AI merge helpers.** Not every merge step needs AI. Fields that come from metadata (document filenames, upload timestamps, count of sources) should be built deterministically without an AI call. Only the truly synthetic sections (executive summary, growth plan, overall assessment) need the aggregator. This saves tokens and eliminates a failure point.

12. **Fallback aggregator as last resort.** The deterministic fallback aggregator should never be the primary path — it produces generic content. But it prevents a blank or broken report when the AI aggregator fails. Design it to surface real data from the domain results (actual ratings, real strengths/growth items) rather than hardcoded placeholder text.

## Related Patterns

| Pattern | When to use | Relationship |
|---------|-------------|-------------|
| `dual-emit-llm-generation` | 3-12 fields, need BOTH structured data AND narration from same context | Complementary — DualEmit for moderate fields where narrative + data must be internally consistent; domain-chunking when fields exceed single-call attention limits |
| FalkorDB node projection | After generation, project structured data to graph nodes | Downstream consumer |
| Standard structured output | Only need flat JSON, no narration or chunking | Simpler — no merge, no fallback |

## References

- `references/tpess-5-domain-pipeline.md` — Real implementation of 5-domain chunked generation with richer per-chunk schema, array-name normalization, and the rating philosophy pattern. Use as a concrete example when building a new domain-chunked pipeline.

## Verification Checklist
- [ ] Per-group schemas exist with correct minItems/maxItems matching their count
- [ ] Per-group prompts scope the model to its specific dimensions and forbid others' dimensions
- [ ] Concurrent dispatch uses `Promise.all` with correct per-group calls
- [ ] Per-domain retry loop has: attempted-count tracking, targeted retry instructions, rate-limit backoff, and schema-error detection
- [ ] field-name normalization maps all known aliases, handles combined-field parsing, and logs raw first dimension
- [ ] Post-merge value stamping deterministically overwrites model values with independent source of truth
- [ ] Final cross-domain validation runs after merge
- [ ] JSON-mode fallback exists for models that don't return tool_calls
- [ ] Non-first groups skip loading reference templates (token optimization)
- [ ] Aggregator/meta-call exists (if needed): receives all domain results as context, produces cross-cutting sections
- [ ] Fallback aggregator exists: produces readable content from domain data when AI aggregator fails
- [ ] Deterministic merge helpers: evidence sources, limitations note built from metadata, not AI
- [ ] Tool type interface includes `[k: string]: unknown` index signature for Anthropic SDK compatibility

# Hybrid Data Acquisition Pattern

Combining scraping with Ollama synthesis for cost-efficient data expansion.

## Core Principle

AI inference is for **judgment, synthesis, and formatting** — not for **discovery**. When expanding datasets (e.g., port guides), always prefer:
1. Scrape or search for raw data (free/cheap)
2. Feed raw into Ollama for cleanup/structuring (inference cost only for synthesis)
3. Store both raw and structured separately

## Ollama Cloud Reality Check

**Ollama Cloud models do NOT have built-in web search.** The `llama3-groq-tool-use` model supports function calling, but this means calling functions **you provide** — not browsing the internet. There are no "search" or "web" models in the Ollama Cloud catalog.

**Models investigated (May 2026):**
| Model | Tool Use? | Web Search? | Notes |
|-------|-----------|-------------|-------|
| `llama3-groq-tool-use` (8B, 70B) | ✅ Function calling | ❌ No | Client-side tool execution only |
| `r1-1776` (Perplexity) | ❌ No | ❌ No | De-biased reasoning, no live search |
| `glm-4.7-flash` | ❌ No | ❌ No | MoE model, no search capability |
| All 39 Max plan models | — | ❌ None | No dedicated search/web models |

**Implication:** If you need live web data, you must use an external search API + Ollama synthesis.

## Two-Source Strategy for Port Guides

### Source 1: WhatsInPort.com (Ocean Cruise Ports)
- **URL pattern:** `https://www.whatsinport.com/{PortName}.htm` (case-sensitive)
- **Coverage:** Rich narrative content — location, tours, shopping, currency, holidays
- **Blind spot:** River cruise ports return 404 (Budapest, Vienna, Cologne, Passau, etc.)
- **Cost:** Free (scraping)
- **Data quality:** Unstructured prose — needs LLM extraction to match `cleanedSections` schema

### Source 2: External Search API + LLM (River Cruise + Gaps)
- **Search APIs:** Brave Search API, SerpAPI, Google Custom Search
- **LLM for synthesis:** DeepSeek-v4-flash (preferred), Ollama Cloud (gemma4:31b), or DeepSeek-v4-pro
- **Flow:**
  1. Search for "{port name} cruise port guide"
  2. Fetch top 3 result pages
  3. Concatenate raw text
  4. Feed to LLM with extraction prompt
  5. Store structured output
- **Cost:** ~$0.01/port for search + LLM inference (Ollama covered by Max plan; DeepSeek ~$0.001/query)
- **Quality:** Variable — depends on search results; needs validation

**Why DeepSeek-v4-flash for synthesis:**
- OpenAI-compatible API — drop-in replacement for existing code
- Supports tool calls for multi-step research orchestration
- Fast and cost-effective for structured extraction tasks
- Good at following JSON schema constraints

**Note:** DeepSeek (like Ollama) has NO built-in web search. The two-step pattern is mandatory: search API fetches content, DeepSeek structures it.

## Implementation Pattern

```typescript
// Step 1: Try WhatsInPort first (free)
const whatsInPortHtml = await scrapeWhatsInPort(portName);
if (whatsInPortHtml) {
  const structured = await deepseekExtractSections(whatsInPortHtml);
  return storePortGuide(portSlug, whatsInPortHtml, structured, 'whatsinport');
}

// Step 2: Fall back to search + DeepSeek
const searchResults = await braveSearch(`${portName} cruise port guide`);
const rawText = await fetchPages(searchResults);
const structured = await deepseekExtractSections(rawText);
return storePortGuide(portSlug, rawText, structured, 'search+deepseek');
```

## DeepSeek Extraction Prompt Template

```typescript
const DEEPSEEK_EXTRACTION_PROMPT = `Extract the following sections from this port guide text.
Return ONLY a JSON object with these keys: welcome, attractions, shopping, 
gettingAround, safety, weather, localCurrency, portLocation, nearbyCities.

If a section is not present in the text, return an empty string for that key.
Do not invent information. Do not summarize — extract verbatim where possible.

Text:
{{text}}

JSON:`;

async function deepseekExtractSections(text: string) {
  const client = new OpenAI({
    apiKey: process.env.DEEPSEEK_API_KEY,
    baseURL: 'https://api.deepseek.com',
  });
  
  const response = await client.chat.completions.create({
    model: 'deepseek-v4-flash',
    messages: [
      { role: 'system', content: 'You extract structured port guide data from raw text. Return valid JSON only.' },
      { role: 'user', content: DEEPSEEK_EXTRACTION_PROMPT.replace('{{text}}', text.substring(0, 8000)) },
    ],
    response_format: { type: 'json_object' },
  });
  
  return JSON.parse(response.choices[0].message.content);
}
```

## Cost Comparison

| Approach | Cost per Port | Quality | Coverage |
|----------|--------------|---------|----------|
| Pure LLM "describe this port" | $0.002–0.005 | Low (training data only) | All ports (but stale/imagined) |
| WhatsInPort scrape + Ollama cleanup | $0.001–0.002 | High | Ocean cruise only (~60% of active ports) |
| WhatsInPort scrape + DeepSeek cleanup | $0.001–0.002 | High | Ocean cruise only (~60% of active ports) |
| Search API + DeepSeek extraction | $0.01–0.02 | Medium-High | All ports with web presence |
| Search API + Ollama extraction | $0.01–0.02 | Medium | All ports with web presence |
| Manual curation | $5–10 | Very High | Select ports only |

**Model selection guidance:**
- Use **Ollama Cloud** (gemma4:31b) for bulk processing when volume > 100 ports — flat-rate Max plan makes cost predictable
- Use **DeepSeek-v4-flash** for smaller batches or when OpenAI SDK compatibility is needed — better JSON schema adherence
- Use **DeepSeek-v4-pro** when extraction accuracy is critical and cost is secondary

## Validation Rules

Before storing any AI-extracted port guide:
- [ ] Raw source is preserved in separate column
- [ ] At least 3 of 9 sections have non-empty content
- [ ] No hallucinated facts (cross-check 2 random claims against raw)
- [ ] Port name matches slug (prevent "Barcelona" data stored under "barcelona-spain")
- [ ] LLM model version recorded for reproducibility (e.g., `deepseek-v4-flash` or `gemma4:31b-cloud`)

## Files Touched

| File | Purpose |
|------|---------|
| `scripts/scraper/whatsinport-scraper.ts` | WhatsInPort scraper with Ollama cleanup |
| `scripts/scraper/search-port-guides.ts` | Brave Search + Ollama extraction fallback |
| `lib/ollama/port-guide-extraction.ts` | Shared extraction prompt + response parser |
| `prisma/schema.prisma` | Add `source` enum to `port_guides` (whatsinport, search_ollama, manual) |

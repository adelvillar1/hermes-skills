# Finance / Trading / Analytics UI — Citable References

A condensed knowledge bank for future agents building any UI in the finance, trading, analytics, or stock-predictor family. The SKILL.md catalog has a one-line entry; this file has the actual case-study details and design principles extracted from the source material so an agent doesn't have to re-derive them each session.

## TradingView 2025 redesign (canonical reference)

Public case study documented by Rondesign Lab. **Validate any finance-UI design decision against this study before defaulting to your own intuition** — the rationale for every choice is in the study.

**Headline numbers (from the case study):**
- **26% trader efficiency gain** after redesign
- **34% faster access to real-time data**
- 77% of traders reported improved chart control
- 68% appreciated smarter alert setup
- Mobile load time: 4.2s → 1.8s
- 23% longer viewing time after reducing green/red saturation by 18%

**Design decisions and their rationale:**

1. **IBM Plex Mono for every number, ticker, price, percentage, date.** The case study explicitly credits this with preventing misreading of figures like `$1,234.56` as `$12,34.56` (decimal-comma locales) and `$1,234.56` as `$1.23456` (mis-placed decimal). **The single highest-leverage font choice in this domain.** If you use a proportional font for numbers, you will eventually get a bug report about a number rendering wrong — this is the bug to prevent upfront.

2. **Inter Variable for chrome, with `font-feature-settings: "cv01", "ss03"` applied globally.** The case study references IBM Plex Sans for UI but Inter Variable is the modern functional equivalent (the same OpenType features give a more geometric, less humanist character that fits the operator-tool aesthetic). The case study also notes Inter Variable reduced page load by 180KB vs the old IBM Plex Sans — variable fonts are a real perf win at the same design quality.

3. **Reduced saturation on semantic green/red (18% desat).** Pure `#00ff00` and `#ff0000` are eye-straining. The case study's 18% desat → 23% longer viewing time is the empirical anchor. The recommended values (from this skill's other work): green `#3DAA6E` (≈70% saturation), red `#D85060` (≈70% saturation). **Pure green/red is a UX failure in operator tools.**

4. **Dark theme as the default.** 84% of traders struggled with multi-chart layouts in light mode. The case study's 23% longer viewing time after switching to dark is the empirical anchor.

5. **Mobile thumb-zone architecture.** Critical actions in the thumb's natural arc, secondary controls via gestures. Mobile completion time 42s → 31s (26% improvement). For a desktop-primary app, this is less relevant, but the principle (critical actions in the natural reach zone) generalizes.

6. **Sign + color + arrow on every delta, never color alone.** This is in the design system as a rule, not a suggestion. WCAG + color-blind safety. Without the arrow, 8% of male users can't read the direction. **Never ship a number that uses only color to convey direction.**

## Koyfin (institutional-quality data at consumer-grade density)

The single strongest single reference for finance UI density without cosplay. Differentiators from Bloomberg Terminal and TradingView:

- **Customizable dashboards with widget-based layout** — operators build their own layout, not navigate a fixed nav tree
- **Global screeners with sortable, filterable, column-pickable tables** — the screener is the entry point, not a separate screen buried in a submenu
- **Advanced charting with overlays** — chart + table composition (chart on top, table below, both linked)
- **Free tier with $39/mo Plus and $79/mo Pro** — pricing accessibility doesn't compromise density

The lesson: **density doesn't require cosplay.** You can ship a Bloomberg-grade operator tool with modern typography, clear hierarchy, and consumer-app polish. The trap is sliding into "minimalist" SaaS aesthetics (Notion, Cal.com) which signal "intro to our product" not "use it daily."

## Bloomberg Terminal (the density ceiling)

Don't copy the visuals. The all-black grid, the neon green-on-black, the "function key 1 = help" command layer — these are a *historical* aesthetic, not a design choice. They survive because Bloomberg's users are institutional traders who learned the system in 1985 and the switching cost is enormous.

What to copy from Bloomberg:
- **Information density per square inch.** Operators scan. A 1440x900 screen should show more than 20 visible data points; the default is closer to 50-80 in Bloomberg-grade tools.
- **Stable, persistent, dense table layouts.** Tables don't get reorganized on you. Sort order is sticky. Column choices persist across sessions.
- **Keyboard-first navigation.** ⌘K palette for everything, arrow keys for table traversal, no mouse required for the power-user loop.
- **Density toggles (comfortable / compact / dense).** Bloomberg users toggle density 5-10 times per day. The toggle is a first-class UI control, not a hidden settings option.

What NOT to copy:
- The visual style. Monospace green-on-black is dated and signals "we haven't redesigned since 1995."
- The function-key command layer. ⌘K palettes are the modern equivalent.
- The 4-figure-per-month pricing. Not viable for indie/solo projects.

## Kraken crypto exchange UI (a dark mode reference)

Useful when the project is in a darker / more technical corner of finance. Specifically:
- **Dark theme by default, 70% saturation on semantic colors** — same principle as TradingView
- **Data-dense dashboards** (portfolio view, markets view, trade history) without falling into Bloomberg cosplay
- **Per-page color tokens** — different surfaces (markets vs. account vs. trade) have subtly different surface tones (`#101114` vs `#14171A` vs `#1C2025`), giving subtle depth without shadows

When to use Kraken as a reference:
- The project is crypto / web3 / DeFi adjacent
- The user wants "dark" as the primary mode (not just a toggle)
- The aesthetic should feel more like a technical operator tool than a consumer app

When NOT to use Kraken as a reference:
- The project is traditional finance (use TradingView/Koyfin)
- The user wants light mode (Kraken is dark-only)

## The four cardinal rules (one-liner version for plans)

When the plan says "finance / trading / analytics UI," these four are the irreducible design floor:

1. **One specific mono font for every number** (IBM Plex Mono is the safe default)
2. **Dark mode is the default** (operator tool, long sessions, reduced eye strain)
3. **Reduced saturation on semantic green/red** (~70% saturation, TradingView's 18%-desat finding)
4. **Sign + color + arrow on every delta, never color alone**

Any plan in this domain that violates one of these will get a 3/3 cross-LLM review finding on it. Encode them as acceptance criteria or design constraints, not as suggestions.

## How to use this file

When `draft-feature-plan` is invoked and the plan touches a finance/trading/analytics UI surface:

1. Load this file via `skill_view(name="popular-web-designs", file_path="references/finance-analytics-ui-references.md")`
2. Cite the four cardinal rules as acceptance criteria in the plan
3. If the design tokens include semantic green/red, encode the 70%-saturation rule in the lint script
4. If the typography section doesn't specify IBM Plex Mono for numbers, add it as a §11b-style requirement (see `draft-feature-plan` §11b.1)

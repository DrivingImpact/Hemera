# Supplier AI Training Strategy for HemeraScope

**Date:** 2026-04-12
**Author:** Research note for Nico
**Status:** Draft for decision
**Audience:** Hemera founders / product lead

## Context

HemeraScope today is a generic LLM (Claude Sonnet 4.6, via API) wrapped in
prompts and retrieval against UK public registries — Companies House, HSE,
Environment Agency, SBTi CDP disclosures, DEFRA. Each supplier analysis rediscovers
basic facts from scratch, which wastes tokens, slows the pipeline, and introduces
avoidable errors on well-known multinationals (DHL, Maersk, Unilever, BASF,
Siemens, Amazon, and similar).

The question: how do we give the pipeline stronger baseline knowledge about the
top ~500 global suppliers so it reasons from verified facts, not from whatever
the model happens to remember? This note evaluates the four practical options,
costs them at 2026 prices, and recommends an order.

A quick framing point before the options: **this is a knowledge problem, not a
reasoning problem.** Claude already reasons about ESG well; what it lacks is a
reliable, up-to-date factual base about specific companies. That framing matters,
because it points strongly toward retrieval over fine-tuning — and the rest of
the doc explains why.

## Option 1: RAG over a curated supplier dataset

The strongest option, and the one that maps most directly to the actual problem.

### What the corpus contains

For each of the ~500 priority suppliers, one structured "supplier card" covering:

- Legal entity and parent/ultimate owner (LEI, Companies House number where UK)
- Major subsidiaries and brands (so "DHL Supply Chain" resolves to Deutsche Post DHL)
- Countries of operation and headcount band
- SBTi status (committed / validated / targets / none), CDP score, TCFD disclosure
- Published Scope 1/2/3 emissions for most recent 2-3 years (with source + date)
- Known compliance incidents (HSE notices, EA enforcement, court cases, major fines)
- Sector / sub-sector for Exiobase factor mapping
- Data quality notes ("Scope 3 excludes category 11 per 2024 disclosure")

Target size: ~2–4 KB of clean text per supplier, so ~1–2 MB total for 500 cards.
That is tiny — the whole corpus fits comfortably in a single Postgres table.

### How to build the corpus

A hybrid approach is the only realistic one for a small team:

1. **Automated pull** for the structured bits — SBTi public dashboard (CSV), CDP
   public responses, Companies House API, LEI lookup, the supplier's own latest
   sustainability PDF. These are the cheap 70%.
2. **LLM extraction** to normalise the sustainability PDFs into the card schema.
   Use Claude Sonnet with a strict JSON schema; cost per supplier is cents.
3. **Manual QC** by a human analyst on every card before it goes live. Budget
   ~15 minutes per supplier for the top 100, ~5 minutes for the next 400. That
   is roughly 4–5 weeks of one analyst's time — achievable.
4. **Refresh cadence:** top 100 quarterly, next 400 annually, triggered by a
   script that checks for new SBTi/CDP filings. Do not try to live-scrape.

### Storage and retrieval

- **Vector store: pgvector on the existing Postgres.** Pinecone is unnecessary
  at this scale. 500 cards chunked at ~300 tokens is ~5k vectors; pgvector on a
  $30–80/month managed Postgres handles this with room for 100x growth.
  Self-hosting cost is effectively £0 incremental if the app already has a Postgres.
- **Embeddings:** OpenAI `text-embedding-3-large` at $0.13/1M tokens. Embedding
  the entire corpus is ~£0.10 one-time. Re-embedding quarterly is rounding error.
  Alternatives (Voyage, Cohere) are comparable; don't optimise this.
- **Retrieval strategy:** hybrid. Do an exact-match lookup on canonical supplier
  name and LEI first — if the supplier is in the corpus, inject the full card
  deterministically rather than trusting cosine similarity. Fall back to vector
  search only for fuzzy matches ("Maersk Line" → "A.P. Møller – Mærsk A/S") and
  for pulling related incidents from the incident index.
- **Context injection:** put the supplier card inside a cached prompt prefix
  (see Option 4) so every analysis run pays cache-read prices, not full input prices.

### Cost per lookup

- Embedding the query: negligible (<£0.0001)
- Vector search: free (Postgres CPU)
- Injecting a ~2 KB card into a Claude Sonnet call: ~500 tokens cached = ~£0.00015
- **Effective marginal cost: under £0.001 per supplier lookup.**

The real cost is building and maintaining the corpus, not running it.

## Option 2: Fine-tuning

Short version: **not the right tool for this problem, and for Hemera specifically
not the right tool at this stage.** But it is worth understanding why.

### OpenAI fine-tuning (available, mature)

As of April 2026, OpenAI supports fine-tuning on GPT-4o, GPT-4o mini, and GPT-4.1.
Pricing, confirmed this week:

- **GPT-4.1 fine-tune training:** ~$3.00/1M training tokens
- **GPT-4.1 fine-tuned inference:** ~$3.00 input / $12.00 output per 1M tokens
- **GPT-4o fine-tune training:** $25/1M training tokens
- **GPT-4o fine-tuned inference:** $3.75 input / $15 output per 1M tokens

A realistic Hemera fine-tune — say 2,000 high-quality supplier analysis examples
averaging 4k tokens each = 8M tokens, trained for 3 epochs = 24M tokens — would
cost roughly **£60–£600 to train** depending on model. That part is cheap.

The hidden cost is building the 2,000 examples. Each needs to be a fully-worked
supplier analysis in Hemera's house style, verified correct. At 30 minutes per
example that is ~1,000 analyst hours, or roughly £25k–£40k of human time. And
the resulting fine-tune still will not know new facts that emerge after training.

### Anthropic / Claude fine-tuning (limited)

**Confirmed as of April 2026:** Anthropic still does not offer general fine-tuning
through its native API. The only path is Claude 3 Haiku fine-tuning via Amazon
Bedrock, which has been in preview since mid-2024 and has not been extended to
Sonnet 4.x or Opus 4.x. Since Hemera's pipeline runs on Sonnet and benefits from
Sonnet's reasoning quality, this path is effectively closed: fine-tuning Haiku
3 would mean giving up two generations of model improvement to gain style
conformance. Not worth it.

### Open-source fine-tuning (Llama 4, Qwen, Mistral)

Viable technically, wrong choice organisationally. Together AI and Fireworks AI
both offer managed LoRA fine-tuning on Llama 4 Maverick/Scout at roughly
$0.48/1M training tokens, and will serve the fine-tuned model at base-model
inference prices (~$0.20 input / $0.60 output per 1M for Maverick). So the raw
numbers look attractive.

But adopting an open-source stack means Hemera owns:
- a second model provider relationship,
- eval harness for regression testing against Claude,
- a prompting pipeline that has to work on a weaker model than Sonnet,
- and the "is this still better than Claude + RAG?" question every 3 months.

Without an ML engineer, that overhead eats any saving. Park this option until
volume is >100k analyses/month.

### When fine-tuning *would* actually help

Fine-tuning is the right answer when the problem is **style, format, or
implicit domain reasoning** that is hard to specify in a prompt — e.g. making
the model reliably output Hemera's 8-layer methodology structure, or teaching
it DEFRA-specific vocabulary quirks. It is the wrong answer when the problem
is **facts about specific entities** (which is the current problem) because
those facts go stale and the model cannot cite its source.

## Option 3: Prompt engineering with few-shot examples

The cheapest baseline, and genuinely underrated.

Curate 20–50 gold-standard supplier analyses (ideally spanning sectors:
logistics, chemicals, tech, retail, industrial) and inject 3–5 of them as
few-shot examples in every prompt, chosen dynamically to match the target
supplier's sector.

- **Build cost:** ~40 analyst-hours = ~£1.5k. Doable in a week.
- **Token cost per run:** ~15k tokens of examples = ~£0.045 at Sonnet 4.6 input
  pricing. With prompt caching on the examples (see Option 4), drops to ~£0.005.
- **Quality ceiling:** high for style/structure, low for factual grounding.
  Few-shot teaches the model *how* to analyse a supplier, not *what* is true
  about any specific one.

This is the thing to do on Monday morning regardless of which bigger option
gets picked. It is cheap, fast, and compounds with everything else.

## Option 4: Hybrid — RAG + few-shot + prompt caching

The recommended architecture. Each layer does what it is best at:

- **Prompt caching** holds the large, slow-moving stuff: the Hemera methodology
  instructions, the DEFRA factor tables, the 3–5 few-shot examples, and the
  supplier card when it exists. Claude Sonnet 4.6 pricing (confirmed April 2026):
  - Base input: $3/1M tokens
  - Cache write (5-min): $3.75/1M tokens (1.25x)
  - Cache write (1-hour): $6/1M tokens (2x)
  - **Cache read: $0.30/1M tokens (0.1x)**
- **RAG** injects the specific supplier card deterministically when the supplier
  is in the curated set, plus any relevant incident records from a secondary
  incident index.
- **Few-shot** handles reasoning style — sector-matched examples get pulled in
  alongside the card.
- **Live retrieval** (the existing Companies House / HSE / EA tooling) stays
  exactly as it is, for the long tail of suppliers not in the curated set.

The compounding effect is real. A typical HemeraScope run today costs ~£0.15
in tokens. With a 1-hour cached prefix covering methodology + examples + card,
the same run drops to ~£0.03–£0.05 — a 3–5x cost reduction while also improving
quality because the model stops guessing about big suppliers.

## Cost / timeline table

All GBP figures are rough order-of-magnitude, assuming Sonnet 4.6 as the
primary model.

| Approach | Pilot cost | Per-analysis cost at scale | Time to v1 | Skills required |
|---|---|---|---|---|
| Few-shot only (Opt. 3) | £1.5k (analyst time) | £0.01–£0.05 | 1 week | Prompt engineer |
| RAG over 500 suppliers (Opt. 1) | £8k–£15k (mostly curation labour) | <£0.05 incl. model call | 4–6 weeks | Analyst + backend dev |
| OpenAI fine-tune (Opt. 2a) | £25k–£40k (training data creation dominates) | £0.05–£0.20 | 8–12 weeks | Prompt engineer + data ops |
| Open-source fine-tune (Opt. 2c) | £30k–£50k + ongoing eval ops | £0.02–£0.10 | 12+ weeks | ML engineer (not currently on team) |
| Claude fine-tune (Opt. 2b) | N/A — not supported on Sonnet in 2026 | — | — | — |
| Hybrid (Opt. 4, recommended) | £10k–£16k | £0.03–£0.05 | 5–7 weeks | Analyst + backend dev |

Two honest caveats on this table:

- The pilot costs for RAG and fine-tuning are dominated by **analyst curation
  labour**, not infrastructure. If you value that time at zero (founder hours,
  unpaid), the numbers compress dramatically. I have priced it as if an analyst
  costs £250/day.
- The "per-analysis at scale" numbers assume prompt caching is working. Without
  caching, RAG and few-shot both look 3–5x more expensive.

## Recommendation

**Do this, in this order:**

### 1. Ship few-shot + prompt caching this week (Option 3 + part of Option 4)

Curate 20 gold-standard supplier analyses, wire them into the prompt with
dynamic sector-matching, and turn on 1-hour prompt caching on the methodology
block. This is ~1 week of work, costs ~£1.5k, and delivers an immediate
quality and cost win. It is also the foundation the RAG work will build on.

### 2. Build the curated 500-supplier RAG corpus over 4–6 weeks (Option 1)

Start with the top 100 (by frequency in Hemera's current pipeline — whichever
suppliers actually come up in client work). Wire pgvector into the existing
Postgres. Use exact-match on name/LEI first, vector search second. This is
the highest-leverage piece of work and addresses the actual failure mode
(generic knowledge about big global suppliers).

Budget realism: **the bottleneck is human QC, not code.** Do not let the
engineering take longer than 2 weeks; the other 2–4 weeks should be analyst
curation running in parallel.

### 3. Defer fine-tuning until at least Q4 2026

Revisit only if (a) Anthropic opens Sonnet fine-tuning, or (b) analysis volume
exceeds 10k suppliers/month and inference cost becomes the dominant line item,
or (c) there is a specific format/style problem that prompt engineering
provably cannot fix. None of those are true today.

**Why this order:** few-shot is cheap insurance and compounds with everything
else. RAG directly attacks the "model doesn't know DHL's parent" problem and
gives Hemera a proprietary, defensible data asset — the corpus itself is
valuable intellectual property that fine-tuning would not produce. Fine-tuning
is an optimisation to run *after* you know what good output looks like and
have traffic to amortise the build cost against; Hemera has neither yet.

### One thing to watch

Anthropic has been hinting at broader fine-tuning support throughout 2025 and
into early 2026 but has not shipped it for Sonnet or Opus. If that changes
mid-year, the calculus on Option 2b shifts materially because it would let
Hemera fine-tune for *style* on the same model family already in production,
with no provider switch. Worth a calendar reminder to re-check in July 2026.

## Sources

- [Anthropic Claude fine-tuning status (Bedrock, Haiku 3 only)](https://x.com/AnthropicAI/status/1811084348692517323)
- [Claude API pricing and prompt caching docs](https://platform.claude.com/docs/en/about-claude/pricing)
- [Claude prompt caching mechanics](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [OpenAI fine-tuning pricing (GPT-4.1, GPT-4o)](https://developers.openai.com/api/docs/pricing)
- [OpenAI GPT-4o fine-tuning announcement](https://openai.com/index/gpt-4o-fine-tuning/)
- [OpenAI text-embedding-3-large pricing](https://developers.openai.com/api/docs/models/text-embedding-3-large)
- [pgvector vs Pinecone cost comparison 2026](https://encore.dev/articles/pgvector-vs-pinecone)
- [Supabase pgvector vs Pinecone benchmarks](https://supabase.com/blog/pgvector-vs-pinecone)
- [Fireworks AI LoRA fine-tuning tutorial](https://fireworks.ai/blog/supervised-fine-tuning-tutorial)
- [Llama 4 API pricing / self-hosting comparison](https://llmwise.ai/llama-api-pricing/)
- [Claude API pricing guide 2026 (Sonnet 4.6)](https://devtk.ai/en/blog/claude-api-pricing-guide-2026/)

## What I am not sure about

- Exact 2026-Q2 GPT-4.1 fine-tune training price — cited as "~$3/1M" but one
  source disagrees; get a quote before committing.
- Whether Anthropic's Bedrock Haiku fine-tuning has been extended to Haiku 4.5;
  search results were inconclusive. Not load-bearing for the recommendation.
- Long-tail supplier coverage: 500 cards will cover the fat head of Hemera's
  client work, but I don't have data on how long the tail actually is. Worth
  pulling from the pipeline logs before finalising corpus size.

"""LLM-based transaction classifier — Claude Haiku for ambiguous items.

Batches up to 50 transactions per prompt to minimise API calls.
Caches results so the same supplier+description combo is never classified twice.
"""

import json
from anthropic import Anthropic
from hemera.config import get_settings
from hemera.services.classifier import Classification

# In-memory cache — persists for the lifetime of the process.
# In production, this should be backed by the database.
_classification_cache: dict[str, Classification] = {}


SYSTEM_PROMPT = """You are a carbon accounting classifier. You classify financial transactions
into GHG Protocol scopes and categories.

For each transaction, return:
- scope: 1 (direct emissions), 2 (purchased energy), or 3 (value chain)
- ghg_category: for Scope 3, the category number (1-15). null for Scope 1/2.
- category_name: a short descriptive name

Scope 1: fuel for company vehicles, natural gas for heating, refrigerants
Scope 2: electricity, purchased heat/steam/cooling
Scope 3 categories:
  1: Purchased goods and services (most common for SMEs)
  2: Capital goods (furniture, equipment, building work)
  3: Fuel/energy related activities not in Scope 1/2
  4: Upstream transportation and distribution
  5: Waste generated in operations
  6: Business travel (flights, trains, hotels, taxis)
  7: Employee commuting
  8: Upstream leased assets (rent, property leases)
  9-15: Less common for SMEs

Respond with a JSON array matching the input order. Each element:
{"scope": int, "ghg_category": int|null, "category_name": "string"}
"""


async def classify_with_llm(
    transactions: list[dict],
    batch_size: int = 50,
) -> list[Classification]:
    """Classify transactions using Claude Haiku.

    Args:
        transactions: list of dicts with keys: index, supplier, description, amount, category
        batch_size: max transactions per API call

    Returns:
        list of Classification objects aligned with input
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        # No API key — return unknowns
        return [
            Classification(3, 1, "Unclassified — no API key", "llm", 0.0)
            for _ in transactions
        ]

    client = Anthropic(api_key=settings.anthropic_api_key)
    results: list[Classification] = []

    # Process in batches
    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i + batch_size]

        # Check cache first
        batch_results: list[Classification | None] = []
        uncached_indices: list[int] = []
        uncached_items: list[dict] = []

        for j, t in enumerate(batch):
            cache_key = _make_cache_key(t)
            if cache_key in _classification_cache:
                batch_results.append(_classification_cache[cache_key])
            else:
                batch_results.append(None)
                uncached_indices.append(j)
                uncached_items.append(t)

        # Call LLM for uncached items
        if uncached_items:
            llm_results = await _call_llm(client, uncached_items)
            for idx, classification in zip(uncached_indices, llm_results):
                batch_results[idx] = classification
                # Cache the result
                cache_key = _make_cache_key(batch[idx])
                _classification_cache[cache_key] = classification

        results.extend([r for r in batch_results if r is not None])

    return results


async def _call_llm(client: Anthropic, items: list[dict]) -> list[Classification]:
    """Make a single API call to classify a batch of transactions."""
    # Format transactions for the prompt
    lines = []
    for i, t in enumerate(items):
        parts = []
        if t.get("supplier"):
            parts.append(f"Supplier: {t['supplier']}")
        if t.get("description"):
            parts.append(f"Description: {t['description']}")
        if t.get("amount"):
            parts.append(f"Amount: GBP {t['amount']:.2f}")
        if t.get("category"):
            parts.append(f"Account code: {t['category']}")
        lines.append(f"{i+1}. {' | '.join(parts)}")

    user_prompt = (
        f"Classify these {len(items)} transactions into GHG Protocol scopes and categories:\n\n"
        + "\n".join(lines)
        + "\n\nRespond with a JSON array only."
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Parse response
        text = response.content[0].text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        parsed = json.loads(text)

        results = []
        for item in parsed:
            results.append(Classification(
                scope=item.get("scope", 3),
                ghg_category=item.get("ghg_category"),
                category_name=item.get("category_name", "LLM classified"),
                method="llm",
                confidence=0.75,
            ))

        # Pad if LLM returned fewer results than expected
        while len(results) < len(items):
            results.append(Classification(3, 1, "Unclassified", "llm", 0.0))

        return results

    except Exception as e:
        # On any failure, return low-confidence defaults
        return [
            Classification(3, 1, f"Classification failed: {str(e)[:50]}", "llm", 0.0)
            for _ in items
        ]


def _make_cache_key(t: dict) -> str:
    """Create a cache key from supplier + description."""
    supplier = (t.get("supplier") or "").strip().lower()
    desc = (t.get("description") or "").strip().lower()
    return f"{supplier}||{desc}"

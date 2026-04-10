"""Builds AI prompts for all 5 HemeraScope task types."""
import json


def build_prompt(task_type: str, context: dict) -> str:
    """Build a complete prompt string for the given task type.

    Args:
        task_type: One of risk_analysis, client_language, recommended_actions,
                   engagement_summary, exec_summary.
        context: Dict containing the data to embed in the prompt.

    Returns:
        A fully-formed prompt string ready to send to an LLM.

    Raises:
        ValueError: If task_type is not recognised.
    """
    builders = {
        "risk_analysis": _build_risk_analysis,
        "client_language": _build_client_language,
        "recommended_actions": _build_recommended_actions,
        "engagement_summary": _build_engagement_summary,
        "exec_summary": _build_exec_summary,
    }
    if task_type not in builders:
        raise ValueError(
            f"Unknown task_type '{task_type}'. Must be one of: {', '.join(builders)}"
        )
    return builders[task_type](context)


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _build_risk_analysis(ctx: dict) -> str:
    supplier_name = ctx.get("supplier_name", "Unknown Supplier")
    sector = ctx.get("sector", "Unknown")
    sic_codes = ctx.get("sic_codes", [])
    sources_summary = ctx.get("sources_summary", [])
    findings = ctx.get("deterministic_findings", [])
    hemera_score = ctx.get("hemera_score", "N/A")
    domain_scores = ctx.get("domain_scores", {})

    sic_str = ", ".join(str(s) for s in sic_codes) if sic_codes else "none recorded"
    domain_str = (
        "\n".join(f"  - {k}: {v}" for k, v in domain_scores.items())
        if domain_scores
        else "  (no domain breakdown available)"
    )
    sources_str = (
        "\n".join(
            f"  - Layer {s.get('layer', '?')} | {s.get('source', '?')}: {s.get('summary', '')}"
            for s in sources_summary
        )
        if sources_summary
        else "  (no source data available)"
    )
    findings_str = (
        "\n".join(
            f"  - [{f.get('severity', 'info').upper()}] {f.get('title', '')}"
            for f in findings
        )
        if findings
        else "  (no deterministic findings)"
    )

    return f"""You are a supply chain risk analyst for Hemera Intelligence, an ESG and supply chain consultancy. \
Your role is to critically evaluate structured data about a supplier — both the raw source data AND the automated findings generated from it.

## Supplier Overview
- **Name:** {supplier_name}
- **Sector:** {sector}
- **SIC codes:** {sic_str}
- **Hemera Score:** {hemera_score} / 100

## Domain Scores
{domain_str}

## Data Sources Reviewed
{sources_str}

## Automated Deterministic Findings
{findings_str}

## CRITICAL TASK: Verify & Challenge the Automated Findings

Our deterministic system checks public registries and government databases. However, these sources have known gaps:

- **Modern Slavery Statements**: The gov.uk registry only covers statements submitted through the portal. Many large companies publish on their own website instead. If our system says "Not found in gov.uk registry" for a major company like DHL, Tesco, or Unilever — this is almost certainly a registry gap, not an actual absence.
- **Certifications (ISO 14001, B Corp, etc.)**: Our registry checks may miss certifications not listed in the specific databases we query.
- **SBTi targets**: Recently validated targets may not have propagated to the API yet.
- **CDP disclosures**: Some companies disclose through CDP but aren't in our specific lookup path.

**You MUST use your knowledge of {supplier_name} to verify each finding.** For each automated finding, assess:
1. Is this finding likely CORRECT based on what you know about this company?
2. Is this finding likely a REGISTRY GAP — the company probably does have this but it's not in our database?
3. Is this finding UNCERTAIN — you don't have enough knowledge to verify?

## Also Identify
- Patterns across multiple findings that suggest higher risk than any individual finding
- Sector-specific risks that are relevant to {sector} companies
- Gaps in our data — what we should have checked but didn't
- Positive aspects the automated system may have missed

## Response Format
Respond in JSON:
{{
  "risk_summary": "2–4 sentence narrative summary of the real risk picture for this supplier",
  "verified_findings": [
    {{
      "original_title": "title from automated findings",
      "verdict": "correct | likely_registry_gap | uncertain",
      "reasoning": "why you think this",
      "corrected_title": "optional — what the finding should say instead"
    }}
  ],
  "additional_risks": ["any risks the automated system missed"],
  "opportunities": ["positive aspects or engagement opportunities"],
  "score_context": "1–2 sentences — is the Hemera Score fair given what you know about this company?"
}}
"""


def _build_client_language(ctx: dict) -> str:
    supplier_name = ctx.get("supplier_name", "Unknown Supplier")
    findings = ctx.get("findings", [])

    findings_str = (
        "\n".join(
            f"  - [{f.get('severity', 'info').upper()}] {f.get('title', '')}: {f.get('detail', '')}"
            for f in findings
        )
        if findings
        else "  (no findings provided)"
    )

    return f"""You are drafting client-facing language for Hemera Intelligence to share with a supplier. \
Tone must be professional and constructive. Frame any negatives as improvement opportunities. \
The relationship should feel collaborative — we are working together, not issuing a judgment.

## Supplier: {supplier_name}

## Findings to Communicate
{findings_str}

## Task
Rewrite each finding into client-ready language that:
1. Is respectful and professional in tone.
2. Frames weaknesses as areas where the supplier has an opportunity to improve.
3. Acknowledges positive findings warmly.
4. Avoids jargon or language that could feel punitive.

## Response Format
Respond in JSON with the following structure:
{{
  "supplier_name": "{supplier_name}",
  "client_messages": [
    {{
      "finding_title": "original finding title",
      "client_language": "rewritten client-facing text"
    }}
  ]
}}
"""


def _build_recommended_actions(ctx: dict) -> str:
    supplier_name = ctx.get("supplier_name", "Unknown Supplier")
    findings = ctx.get("findings", [])

    findings_str = (
        "\n".join(
            f"  - [{f.get('domain', 'general').upper()}] {f.get('title', '')}"
            for f in findings
        )
        if findings
        else "  (no findings provided)"
    )

    return f"""You are a sustainability consultant at Hemera Intelligence. Based on findings for a supplier, \
your task is to recommend concrete next actions. Position Hemera as a partner that can help — \
Hemera can facilitate, conduct, or support each action where relevant.

## Supplier: {supplier_name}

## Findings
{findings_str}

## Task
For each finding, recommend a specific, actionable next step. Include:
1. A clear action description.
2. The expected benefit or outcome.
3. Where Hemera can facilitate, conduct, or support the action (mention Hemera by name where appropriate).

## Response Format
Respond in JSON with the following structure:
{{
  "supplier_name": "{supplier_name}",
  "recommended_actions": [
    {{
      "finding": "finding title",
      "action": "recommended action",
      "benefit": "expected outcome",
      "hemera_role": "how Hemera can support"
    }}
  ]
}}
"""


def _build_engagement_summary(ctx: dict) -> str:
    supplier_name = ctx.get("supplier_name", "Unknown Supplier")
    engagements = ctx.get("engagements", [])

    engagements_str = (
        "\n".join(
            f"  - Subject: {e.get('subject', 'N/A')} | Status: {e.get('status', 'N/A')} | Notes: {e.get('notes', '')}"
            for e in engagements
        )
        if engagements
        else "  (no engagements recorded)"
    )

    return f"""You are writing a client-facing summary of engagement activity for Hemera Intelligence. \
The tone should convey momentum and positive progress — factual but positive. \
This summary will be shared with the end client to show the value of engagement.

## Supplier: {supplier_name}

## Engagement Log
{engagements_str}

## Task
Write a brief client-facing engagement summary that:
1. Describes the nature and status of engagements.
2. Highlights progress or positive developments.
3. Notes any next steps or pending actions.
4. Is suitable for inclusion in a client report.

## Response Format
Respond in JSON with the following structure:
{{
  "supplier_name": "{supplier_name}",
  "engagement_summary": "2–4 sentence client-facing narrative",
  "progress_highlights": ["highlight 1", "highlight 2", ...],
  "next_steps": ["next step 1", ...]
}}
"""


def _build_exec_summary(ctx: dict) -> str:
    org_name = ctx.get("org_name", "the organisation")
    supplier_count = ctx.get("supplier_count", 0)
    total_spend = ctx.get("total_spend", 0)
    critical_count = ctx.get("critical_count", 0)
    attention_count = ctx.get("attention_count", 0)
    strong_count = ctx.get("strong_count", 0)

    spend_str = f"£{total_spend:,.0f}" if total_spend else "not specified"

    return f"""You are writing an executive summary for a Hemera Intelligence supply chain sustainability report. \
Tone should be collaborative — frame this as a journey that {org_name} is on with Hemera. \
Acknowledge that every supply chain has areas for improvement, and celebrate the progress already made.

## Portfolio Overview — {org_name}
- **Total suppliers assessed:** {supplier_count}
- **Total supply chain spend:** {spend_str}
- **Suppliers — Critical risk:** {critical_count}
- **Suppliers — Requires attention:** {attention_count}
- **Suppliers — Strong performance:** {strong_count}

## Task
Write a compelling executive summary (3–5 paragraphs) that:
1. Opens with the strategic context for supply chain sustainability.
2. Summarises the portfolio risk profile across the {supplier_count} suppliers.
3. Highlights key areas of strength and areas requiring focus.
4. Positions next steps as a collaborative journey with Hemera.
5. Is suitable for a C-suite audience.

## Response Format
Respond in JSON with the following structure:
{{
  "exec_summary": "full multi-paragraph executive summary text",
  "headline_stats": {{
    "suppliers_assessed": {supplier_count},
    "critical_risk": {critical_count},
    "requires_attention": {attention_count},
    "strong_performance": {strong_count}
  }},
  "key_messages": ["message 1", "message 2", "message 3"]
}}
"""

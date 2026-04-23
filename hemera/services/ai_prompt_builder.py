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

    return f"""You are the lead supply-chain risk analyst at Hemera Intelligence. Your output is the FIRST step in a three-stage analyst workflow — Recommended Actions and Engagement Strategy downstream will be built directly on top of what you return, so be precise and complete.

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

## Your Job

Our deterministic rules check public registries. They have known blind spots:

- **Modern Slavery Statements** — gov.uk registry misses many; large companies often publish on their own site. A "not found" for DHL / Tesco / Unilever is almost certainly a registry gap.
- **Certifications (ISO 14001, B Corp, etc.)** — our lookups can miss certifications held in other databases.
- **SBTi / CDP** — newly validated targets or disclosures may not yet propagate.

**Use your knowledge of {supplier_name} to verify every automated finding.** For each one, render a verdict and a confidence level. Then go beyond the rules: what is the actual risk picture for this company, in this sector?

## Required Analysis

1. **Verify each finding** — correct, likely_registry_gap, or uncertain — with confidence high/medium/low.
2. **Cross-finding patterns** — risks that emerge from the combination, not any single item.
3. **Sector-specific risks** — what's typical for {sector} that the rules didn't check.
4. **Data gaps** — what we should have checked but didn't.
5. **Positive signals** — leadership positions, credible commitments, exemplary practices.
6. **Score fairness** — does the Hemera Score over- or under-state this supplier given what you know?

## Output

Return VALID JSON only — no markdown fences, no prose before or after. Keys:

{{
  "risk_summary": "3–5 sentence narrative capturing the real risk picture, written for a senior analyst",
  "verified_findings": [
    {{
      "original_title": "exact title from automated findings",
      "verdict": "correct | likely_registry_gap | uncertain",
      "confidence": "high | medium | low",
      "reasoning": "1–2 sentences — specific evidence, not generic",
      "corrected_title": "optional — what the finding should actually say"
    }}
  ],
  "additional_risks": [
    {{"risk": "concise risk statement", "severity": "critical | high | medium | low", "rationale": "why this matters here"}}
  ],
  "opportunities": [
    {{"opportunity": "concise positive signal or engagement opening", "evidence": "what makes you confident"}}
  ],
  "sector_context": "1–2 sentences on sector-specific risk framing for {sector}",
  "score_context": "1–2 sentences — is {hemera_score}/100 fair? Biased high or low, and why"
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
    # Accept either "findings" (supplier page) or "included_findings" (curation page)
    findings = ctx.get("findings") or ctx.get("included_findings") or []
    risk_analysis = ctx.get("risk_analysis") or {}

    findings_str = (
        "\n".join(
            f"  - [{(f.get('severity') or f.get('domain') or 'info').upper()}] {f.get('title', '')}"
            for f in findings
        )
        if findings
        else "  (no findings provided)"
    )

    # Pull upstream risk-analysis signal so the action plan builds on verdicts,
    # not the raw rule output. Skip findings the analyst flagged as registry gaps.
    if risk_analysis:
        risk_summary = risk_analysis.get("risk_summary", "")
        verified = risk_analysis.get("verified_findings") or []
        correct_findings = [v for v in verified if v.get("verdict") == "correct"]
        gap_findings = [v for v in verified if v.get("verdict") == "likely_registry_gap"]
        additional_risks = risk_analysis.get("additional_risks") or []
        opportunities = risk_analysis.get("opportunities") or []
        sector_context = risk_analysis.get("sector_context", "")

        def _risk_line(r):
            if isinstance(r, dict):
                sev = (r.get("severity") or "medium").upper()
                return f"  - [{sev}] {r.get('risk', '')} — {r.get('rationale', '')}"
            return f"  - {r}"

        def _opp_line(o):
            if isinstance(o, dict):
                return f"  - {o.get('opportunity', '')} — {o.get('evidence', '')}"
            return f"  - {o}"

        correct_str = (
            "\n".join(
                f"  - {v.get('corrected_title') or v.get('original_title', '')} ({v.get('confidence', 'medium')} confidence)"
                for v in correct_findings
            )
            if correct_findings
            else "  (none — analyst did not confirm any automated findings)"
        )
        gap_str = (
            "\n".join(f"  - {v.get('original_title', '')}" for v in gap_findings)
            if gap_findings
            else "  (none)"
        )
        risks_str = "\n".join(_risk_line(r) for r in additional_risks) if additional_risks else "  (none)"
        opps_str = "\n".join(_opp_line(o) for o in opportunities) if opportunities else "  (none)"

        risk_block = f"""
## Upstream Risk Analysis (analyst-verified — this is your primary input)

**Risk summary:** {risk_summary}

**Verified concerns to act on:**
{correct_str}

**Skip these — flagged as registry gaps, not real risks:**
{gap_str}

**Additional risks analyst identified beyond the automated rules:**
{risks_str}

**Opportunities to reinforce or build on:**
{opps_str}

**Sector context:** {sector_context}
"""
    else:
        risk_block = (
            "\n## Upstream Risk Analysis\n(none available — run Risk Analysis first for a better plan; "
            "otherwise act directly on the findings below, but flag low confidence)\n"
        )

    return f"""You are a senior sustainability consultant at Hemera Intelligence. You are building a prioritised action plan for a supplier. This plan is the SECOND step in a three-stage workflow: the Engagement Strategy (next step) will sequence these actions into real supplier conversations.

## Supplier: {supplier_name}
{risk_block}
## Report Findings (analyst-selected)
{findings_str}

## Task

Design a concrete, prioritised action plan. Treat the Risk Analysis as your primary source — do NOT generate actions for items flagged as registry gaps or uncertain unless you explicitly disagree and say so. Ground each action in a specific risk or opportunity.

For each action specify:
1. **Priority** — critical / high / medium / low (based on severity + materiality, not just severity)
2. **Timeframe** — immediate / 30d / 90d / 12m
3. **Concrete action** — not "improve X", but "do Y by Z" — one sentence
4. **Success metric** — how you will know it worked (measurable)
5. **Hemera role** — facilitate (broker a conversation), conduct (run the work), advise (provide framework), or monitor (track progress)
6. **Dependencies** — IDs or titles of other actions that must complete first

Also produce a **strategic_posture** — the overall stance toward this supplier: partner (invest), monitor (light touch), remediate (active intervention), escalate (senior attention), or exit (too much risk). Explain in one sentence.

Actions ordered by priority then timeframe. Aim for 4–8 actions; do not pad. Quality over quantity.

## Output

Return VALID JSON only — no markdown fences, no prose before or after. Keys:

{{
  "supplier_name": "{supplier_name}",
  "strategic_posture": "partner | monitor | remediate | escalate | exit",
  "posture_rationale": "1–2 sentences",
  "recommended_actions": [
    {{
      "id": "A1",
      "finding": "the risk or finding this targets",
      "priority": "critical | high | medium | low",
      "timeframe": "immediate | 30d | 90d | 12m",
      "action": "concrete action description",
      "benefit": "expected outcome in business terms",
      "success_metric": "measurable signal of success",
      "hemera_role": "facilitate | conduct | advise | monitor",
      "depends_on": []
    }}
  ],
  "quick_wins": ["1-line actions that are cheap, fast, and high-visibility"],
  "do_not_pursue": [
    {{"item": "what we're deliberately not acting on", "reason": "why — registry gap, out of scope, low ROI, etc."}}
  ]
}}
"""


def _build_engagement_summary(ctx: dict) -> str:
    supplier_name = ctx.get("supplier_name", "Unknown Supplier")
    engagements = ctx.get("engagements", [])
    risk_analysis = ctx.get("risk_analysis") or {}
    recommended_actions = ctx.get("recommended_actions") or {}

    engagements_str = (
        "\n".join(
            f"  - [{e.get('type', e.get('subject', 'n/a'))}] {e.get('date', '')} — {e.get('notes', '')}"
            for e in engagements
        )
        if engagements
        else "  (no prior engagements recorded)"
    )

    # Compact the upstream risk + action plan into the prompt so the strategy
    # is anchored in what the analyst already decided, not regenerated.
    if risk_analysis:
        risk_summary = risk_analysis.get("risk_summary", "")
        verified = risk_analysis.get("verified_findings") or []
        confirmed = [v for v in verified if v.get("verdict") == "correct"]
        additional = risk_analysis.get("additional_risks") or []
        opportunities = risk_analysis.get("opportunities") or []

        def _line(x, fields):
            if isinstance(x, dict):
                return " — ".join(str(x.get(f, "")) for f in fields if x.get(f))
            return str(x)

        confirmed_str = (
            "\n".join(f"  - {_line(v, ['corrected_title', 'original_title'])}" for v in confirmed)
            if confirmed else "  (none)"
        )
        additional_str = (
            "\n".join(f"  - {_line(r, ['risk', 'severity'])}" for r in additional)
            if additional else "  (none)"
        )
        opps_str = (
            "\n".join(f"  - {_line(o, ['opportunity'])}" for o in opportunities)
            if opportunities else "  (none)"
        )
        risk_block = f"""
## Risk Analysis (upstream)
{risk_summary}

**Confirmed concerns:**
{confirmed_str}

**Additional risks beyond the rules:**
{additional_str}

**Opportunities:**
{opps_str}
"""
    else:
        risk_block = "\n## Risk Analysis\n(none available — strategy will be lower-confidence)\n"

    if recommended_actions:
        posture = recommended_actions.get("strategic_posture", "unspecified")
        posture_rationale = recommended_actions.get("posture_rationale", "")
        actions = recommended_actions.get("recommended_actions") or []

        def _action_line(a):
            if not isinstance(a, dict):
                return f"  - {a}"
            pri = (a.get("priority") or "?").upper()
            tf = a.get("timeframe") or "?"
            desc = a.get("action") or ""
            role = a.get("hemera_role") or ""
            return f"  - [{pri} · {tf}] {desc}" + (f"  (Hemera: {role})" if role else "")

        actions_str = (
            "\n".join(_action_line(a) for a in actions[:8])
            if actions else "  (no actions)"
        )
        actions_block = f"""
## Action Plan (upstream)
**Strategic posture:** {posture} — {posture_rationale}

**Top actions:**
{actions_str}
"""
    else:
        actions_block = "\n## Action Plan\n(none available — strategy will be lower-confidence)\n"

    return f"""You are the engagement lead at Hemera Intelligence. You are designing a FORWARD-LOOKING engagement strategy for this supplier — not a retrospective summary of what has happened. This is the THIRD step in a three-stage workflow; the Risk Analysis and the Action Plan above are your primary inputs.

## Supplier: {supplier_name}
{risk_block}{actions_block}
## Past Engagement Log
{engagements_str}

## Task

Design a pragmatic engagement strategy that sequences the Action Plan into real supplier conversations. Think like an account lead, not a report writer. Specifically:

1. **Opening approach** — how you'd frame the next conversation given the risk picture. If trust is low, that comes before asking hard questions.
2. **Sequenced priorities** — the order to raise issues in. High-severity items aren't always first; sometimes you build credibility with a quick win.
3. **Cadence** — weekly / monthly / quarterly / event-triggered. Justify briefly.
4. **Escalation triggers** — concrete supplier behaviours (non-response for 30d, deflection on Y, refusal of Z) that move us from partner → remediate → escalate.
5. **Tone** — collaborative / direct / formal. Match to posture and sector norms.
6. **Hemera lead** — who owns it: account manager, sector specialist, or senior partner.
7. **Narrative** — a 3–4 sentence story: where we are with this supplier and where we're going.
8. **Progress to celebrate** — anything real from the past engagement log worth highlighting (if empty, leave empty — do not fabricate).
9. **Next concrete steps** — 2–4 items the account team should do in the next 30 days.

## Output

Return VALID JSON only — no markdown fences, no prose before or after. Keep the keys `engagement_summary`, `progress_highlights`, `next_steps` (backward compatibility); add the others.

{{
  "supplier_name": "{supplier_name}",
  "posture": "partner | monitor | remediate | escalate | exit",
  "engagement_summary": "3–4 sentence forward-looking narrative",
  "opening_approach": "how to frame the first/next conversation",
  "sequenced_priorities": [
    {{"sequence": 1, "focus": "...", "rationale": "why this comes first"}}
  ],
  "cadence": "weekly | monthly | quarterly | event_triggered",
  "cadence_rationale": "1 sentence — why this cadence",
  "escalation_triggers": ["concrete supplier behaviour → action we take"],
  "tone": "collaborative | direct | formal",
  "hemera_lead": "account manager | sector specialist | senior partner",
  "progress_highlights": ["only real items from the engagement log; empty array if none"],
  "next_steps": ["2–4 concrete 30-day actions for the account team"]
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

"""Executes AI tasks via API or prepares them for manual/Max mode."""
import hashlib
import json
import logging
from datetime import datetime
from anthropic import Anthropic
from hemera.config import get_settings
from hemera.models.ai_task import AITask
from hemera.services.ai_prompt_builder import build_prompt

log = logging.getLogger(__name__)


# Task-type → list of upstream task types whose most-recent completed output
# should be injected into the context before building the prompt.
_UPSTREAM_DEPS = {
    "recommended_actions": ["risk_analysis"],
    "engagement_summary": ["risk_analysis", "recommended_actions"],
}


def _parse_ai_response(text: str):
    """Parse a stored AI response as JSON, tolerating ```json code fences."""
    s = text.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1 :]
        if s.endswith("```"):
            s = s[: s.rfind("```")]
        s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


def _inject_upstream_results(db, task_type, target_type, target_id, context):
    """Attach most-recent completed upstream AI task outputs to the context.

    Downstream prompts (recommended_actions, engagement_summary) depend on
    prior task outputs so the analyst builds one coherent thread instead of
    three disconnected LLM calls.
    """
    deps = _UPSTREAM_DEPS.get(task_type, [])
    if not deps or target_type != "supplier":
        return context

    enriched = {**(context or {})}
    for dep_type in deps:
        latest = (
            db.query(AITask)
            .filter(
                AITask.task_type == dep_type,
                AITask.target_type == target_type,
                AITask.target_id == target_id,
                AITask.status == "completed",
            )
            .order_by(AITask.completed_at.desc())
            .first()
        )
        if latest and latest.response_text:
            parsed = _parse_ai_response(latest.response_text)
            if parsed is not None:
                enriched[dep_type] = parsed
            else:
                enriched[f"{dep_type}_text"] = latest.response_text
    return enriched


def create_ai_task(db, task_type, target_type, target_id, mode, context):
    """Create an AITask record and execute or stage it depending on mode.

    Args:
        db: SQLAlchemy session.
        task_type: One of the 5 recognised task types.
        target_type: Entity type the task relates to (e.g. "supplier").
        target_id: PK of the target entity.
        mode: "api" to call Claude immediately; anything else stages the prompt.
        context: Dict of data to pass to the prompt builder.

    Returns:
        The persisted AITask instance.
    """
    context = _inject_upstream_results(db, task_type, target_type, target_id, context or {})
    prompt = build_prompt(task_type, context)
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

    task = AITask(
        task_type=task_type,
        target_type=target_type,
        target_id=target_id,
        mode=mode,
        status="pending",
        prompt_text=prompt,
        prompt_hash=prompt_hash,
    )
    db.add(task)
    db.flush()

    if mode == "api":
        _execute_api(task)
    else:
        task.status = "prompt_copied"

    db.flush()
    return task


def complete_manual_task(db, task, response_text):
    """Mark a manual/Max-mode task as completed with a user-supplied response.

    Args:
        db: SQLAlchemy session.
        task: AITask instance to update.
        response_text: The text response to record.

    Returns:
        The updated AITask instance.
    """
    task.response_text = response_text
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    db.flush()
    return task


def _execute_api(task):
    """Call Claude synchronously and store the result on the task.

    Cost calculation uses claude-sonnet-4 pricing:
      input:  $3 / 1M tokens
      output: $15 / 1M tokens
    """
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": task.prompt_text}],
        )
        task.response_text = response.content[0].text
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.token_count = response.usage.input_tokens + response.usage.output_tokens
        task.cost_usd = round(
            response.usage.input_tokens * 3 / 1_000_000
            + response.usage.output_tokens * 15 / 1_000_000,
            4,
        )
    except Exception as e:
        log.error(f"AI task {task.id} failed: {e}")
        task.status = "failed"
        task.response_text = str(e)

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

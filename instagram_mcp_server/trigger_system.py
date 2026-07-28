"""
Comment-based DM trigger system for Instagram MCP Server.

Allows AI agents to set up automated DM responses when users comment
on specific posts with trigger words or phrases.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from datetime import timedelta, timezone
from enum import Enum
from uuid import uuid4

from instagram_mcp_server.common_utils import secure_write_text, utcnow_iso
from instagram_mcp_server.multi_account import accounts_root_dir

logger = logging.getLogger(__name__)

_TRIGGERS_DIR = "triggers"
_TRIGGERS_CONFIG_FILE = "triggers-config.json"


class TriggerMatchType(Enum):
    """How the trigger word should match comments."""
    EXACT = "exact"  # Exact match (case-insensitive)
    CONTAINS = "contains"  # Contains the trigger word
    STARTS_WITH = "starts_with"  # Starts with the trigger word
    ENDS_WITH = "ends_with"  # Ends with the trigger word
    REGEX = "regex"  # Regular expression match


class TriggerStatus(Enum):
    """Status of a trigger."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


@dataclass
class DMTrigger:
    """Configuration for an automated DM trigger."""
    trigger_id: str
    account_id: str
    post_shortcode: str
    post_url: str
    trigger_words: list[str]
    match_type: str  # TriggerMatchType value
    dm_template: str
    status: str  # TriggerStatus value
    created_at: str
    updated_at: str
    last_triggered: str | None = None
    trigger_count: int = 0
    description: str | None = None
    cooldown_minutes: int = 0  # Minimum time between triggers for same user
    max_triggers_per_user: int = 1  # Max times to trigger per user
    case_sensitive: bool = False


@dataclass
class TriggerExecution:
    """Record of a trigger execution."""
    execution_id: str
    trigger_id: str
    account_id: str
    post_shortcode: str
    comment_id: str
    commenter_username: str
    matched_word: str
    dm_sent: bool
    dm_message_id: str | None = None
    error_message: str | None = None
    executed_at: str = field(default_factory=utcnow_iso)


def triggers_root_dir() -> Path:
    """Return the root directory for trigger configurations."""
    return accounts_root_dir() / _TRIGGERS_DIR


def trigger_config_path() -> Path:
    """Return the path to the triggers configuration file."""
    return triggers_root_dir() / _TRIGGERS_CONFIG_FILE


def trigger_executions_dir() -> Path:
    """Return the directory for trigger execution logs."""
    return triggers_root_dir() / "executions"


def trigger_execution_log_path(trigger_id: str) -> Path:
    """Return the execution log path for a specific trigger."""
    return trigger_executions_dir() / f"{trigger_id}.jsonl"


def initialize_trigger_system() -> None:
    """Initialize the trigger system directories."""
    triggers_root_dir().mkdir(parents=True, exist_ok=True)
    trigger_executions_dir().mkdir(parents=True, exist_ok=True)


def create_trigger(
    account_id: str,
    post_shortcode: str,
    post_url: str,
    trigger_words: list[str],
    dm_template: str,
    match_type: str = "contains",
    description: str | None = None,
    cooldown_minutes: int = 0,
    max_triggers_per_user: int = 1,
    case_sensitive: bool = False,
) -> DMTrigger:
    """Create a new DM trigger."""
    initialize_trigger_system()
    
    trigger_id = f"trigger_{uuid4().hex[:12]}"
    now = utcnow_iso()
    
    trigger = DMTrigger(
        trigger_id=trigger_id,
        account_id=account_id,
        post_shortcode=post_shortcode,
        post_url=post_url,
        trigger_words=trigger_words,
        match_type=match_type,
        dm_template=dm_template,
        status=TriggerStatus.ACTIVE.value,
        created_at=now,
        updated_at=now,
        description=description,
        cooldown_minutes=cooldown_minutes,
        max_triggers_per_user=max_triggers_per_user,
        case_sensitive=case_sensitive,
    )
    
    # Save trigger
    triggers = load_all_triggers()
    triggers.append(trigger)
    save_all_triggers(triggers)
    
    logger.info(f"Created DM trigger: {trigger_id} for post {post_shortcode}")
    return trigger


def get_trigger(trigger_id: str) -> DMTrigger | None:
    """Get a specific trigger by ID."""
    triggers = load_all_triggers()
    for trigger in triggers:
        if trigger.trigger_id == trigger_id:
            return trigger
    return None


def get_triggers_for_account(account_id: str) -> list[DMTrigger]:
    """Get all triggers for a specific account."""
    triggers = load_all_triggers()
    return [t for t in triggers if t.account_id == account_id]


def get_triggers_for_post(post_shortcode: str) -> list[DMTrigger]:
    """Get all triggers for a specific post."""
    triggers = load_all_triggers()
    return [t for t in triggers if t.post_shortcode == post_shortcode]


def get_active_triggers() -> list[DMTrigger]:
    """Get all active triggers."""
    triggers = load_all_triggers()
    return [t for t in triggers if t.status == TriggerStatus.ACTIVE.value]


def update_trigger(
    trigger_id: str,
    trigger_words: list[str] | None = None,
    dm_template: str | None = None,
    status: str | None = None,
    description: str | None = None,
    cooldown_minutes: int | None = None,
    max_triggers_per_user: int | None = None,
) -> DMTrigger | None:
    """Update an existing trigger."""
    triggers = load_all_triggers()
    for i, trigger in enumerate(triggers):
        if trigger.trigger_id == trigger_id:
            if trigger_words is not None:
                trigger.trigger_words = trigger_words
            if dm_template is not None:
                trigger.dm_template = dm_template
            if status is not None:
                trigger.status = status
            if description is not None:
                trigger.description = description
            if cooldown_minutes is not None:
                trigger.cooldown_minutes = cooldown_minutes
            if max_triggers_per_user is not None:
                trigger.max_triggers_per_user = max_triggers_per_user
            
            trigger.updated_at = utcnow_iso()
            triggers[i] = trigger
            save_all_triggers(triggers)
            
            logger.info(f"Updated DM trigger: {trigger_id}")
            return trigger
    
    return None


def delete_trigger(trigger_id: str) -> bool:
    """Delete a trigger."""
    triggers = load_all_triggers()
    original_length = len(triggers)
    triggers = [t for t in triggers if t.trigger_id != trigger_id]
    
    if len(triggers) < original_length:
        save_all_triggers(triggers)
        logger.info(f"Deleted DM trigger: {trigger_id}")
        return True
    
    return False


def pause_trigger(trigger_id: str) -> bool:
    """Pause a trigger."""
    return update_trigger(trigger_id, status=TriggerStatus.PAUSED.value) is not None


def resume_trigger(trigger_id: str) -> bool:
    """Resume a paused trigger."""
    return update_trigger(trigger_id, status=TriggerStatus.ACTIVE.value) is not None


def check_comment_trigger(
    post_shortcode: str,
    comment_text: str,
    commenter_username: str,
    comment_id: str,
) -> tuple[DMTrigger | None, str | None]:
    """Check if a comment matches any active triggers for the post.
    
    Returns:
        Tuple of (matched_trigger, matched_word)
    """
    triggers = get_active_triggers_for_post(post_shortcode)
    
    for trigger in triggers:
        # Check cooldown
        if _is_user_in_cooldown(trigger, commenter_username):
            continue
        
        # Check max triggers per user
        if _has_exceeded_max_triggers(trigger, commenter_username):
            continue
        
        # Check trigger word match
        for word in trigger.trigger_words:
            if _matches_trigger(comment_text, word, trigger):
                return trigger, word
    
    return None, None


def record_trigger_execution(
    trigger: DMTrigger,
    comment_id: str,
    commenter_username: str,
    matched_word: str,
    dm_sent: bool,
    dm_message_id: str | None = None,
    error_message: str | None = None,
) -> TriggerExecution:
    """Record a trigger execution for analytics and cooldown tracking."""
    execution = TriggerExecution(
        execution_id=f"exec_{uuid4().hex[:12]}",
        trigger_id=trigger.trigger_id,
        account_id=trigger.account_id,
        post_shortcode=trigger.post_shortcode,
        comment_id=comment_id,
        commenter_username=commenter_username,
        matched_word=matched_word,
        dm_sent=dm_sent,
        dm_message_id=dm_message_id,
        error_message=error_message,
    )
    
    # Log execution
    log_path = trigger_execution_log_path(trigger.trigger_id)
    with open(log_path, "a") as f:
        f.write(json.dumps(asdict(execution)) + "\n")
    
    # Update trigger stats
    if dm_sent:
        trigger.last_triggered = utcnow_iso()
        trigger.trigger_count += 1
        update_trigger(trigger.trigger_id)
    
    return execution


def get_trigger_executions(trigger_id: str, limit: int = 100) -> list[TriggerExecution]:
    """Get recent executions for a trigger."""
    log_path = trigger_execution_log_path(trigger_id)
    if not log_path.exists():
        return []
    
    executions = []
    with open(log_path, "r") as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                executions.append(TriggerExecution(**data))
            except (json.JSONDecodeError, TypeError):
                continue
    
    # Return most recent first
    executions.reverse()
    return executions[:limit]


def get_user_trigger_count(trigger_id: str, username: str) -> int:
    """Get the number of times a user has triggered a specific trigger."""
    executions = get_trigger_executions(trigger_id, limit=1000)
    return sum(1 for e in executions if e.commenter_username == username and e.dm_sent)


def load_all_triggers() -> list[DMTrigger]:
    """Load all triggers from configuration."""
    config_path = trigger_config_path()
    if not config_path.exists():
        return []
    
    try:
        data = json.loads(config_path.read_text())
        return [DMTrigger(**item) for item in data]
    except (OSError, json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to load triggers: {e}")
        return []


def save_all_triggers(triggers: list[DMTrigger]) -> None:
    """Save all triggers to configuration."""
    initialize_trigger_system()
    config_path = trigger_config_path()
    data = [asdict(trigger) for trigger in triggers]
    secure_write_text(config_path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def get_active_triggers_for_post(post_shortcode: str) -> list[DMTrigger]:
    """Get active triggers for a specific post."""
    triggers = get_triggers_for_post(post_shortcode)
    return [t for t in triggers if t.status == TriggerStatus.ACTIVE.value]


def _matches_trigger(comment_text: str, trigger_word: str, trigger: DMTrigger) -> bool:
    """Check if comment text matches the trigger word based on match type."""
    text = comment_text if trigger.case_sensitive else comment_text.lower()
    word = trigger_word if trigger.case_sensitive else trigger_word.lower()
    
    match_type = TriggerMatchType(trigger.match_type)
    
    if match_type == TriggerMatchType.EXACT:
        return text == word
    elif match_type == TriggerMatchType.CONTAINS:
        return word in text
    elif match_type == TriggerMatchType.STARTS_WITH:
        return text.startswith(word)
    elif match_type == TriggerMatchType.ENDS_WITH:
        return text.endswith(word)
    elif match_type == TriggerMatchType.REGEX:
        import re
        try:
            return bool(re.search(word, text))
        except re.error:
            logger.warning(f"Invalid regex in trigger: {word}")
            return False
    
    return False


def _is_user_in_cooldown(trigger: DMTrigger, username: str) -> bool:
    """Check if a user is in cooldown for a trigger."""
    if trigger.cooldown_minutes <= 0:
        return False
    
    from datetime import datetime
    
    executions = get_trigger_executions(trigger.trigger_id, limit=100)
    now = datetime.now(timezone.utc)
    
    for execution in executions:
        if execution.commenter_username == username and execution.dm_sent:
            exec_time = datetime.fromisoformat(execution.executed_at.replace('Z', '+00:00'))
            if exec_time.tzinfo is None:
                exec_time = exec_time.replace(tzinfo=timezone.utc)
            cooldown_end = exec_time + timedelta(minutes=trigger.cooldown_minutes)
            if now < cooldown_end:
                return True
    
    return False


def _has_exceeded_max_triggers(trigger: DMTrigger, username: str) -> bool:
    """Check if a user has exceeded max triggers for a trigger."""
    if trigger.max_triggers_per_user <= 0:
        return False
    
    trigger_count = get_user_trigger_count(trigger.trigger_id, username)
    return trigger_count >= trigger.max_triggers_per_user
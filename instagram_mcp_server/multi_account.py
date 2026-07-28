"""
Multi-account management for Instagram MCP Server.

Provides functionality to manage multiple Instagram accounts with separate
sessions and cookies for AI agent workflows.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from uuid import uuid4

from instagram_mcp_server.common_utils import secure_write_text, utcnow_iso
from instagram_mcp_server.session_state import auth_root_dir

logger = logging.getLogger(__name__)

_ACCOUNTS_DIR = "accounts"
_ACCOUNT_METADATA_FILE = "account-metadata.json"
_ACCOUNT_COOKIES_FILE = "cookies.json"


@dataclass
class AccountMetadata:
    """Metadata for an Instagram account."""
    account_id: str
    username: str
    full_name: str | None = None
    profile_pic_url: str | None = None
    created_at: str | None = None
    last_used: str | None = None
    is_active: bool = True
    
    # Posting-specific fields
    posting_enabled: bool = True
    daily_post_limit: int = 10
    last_post_time: str | None = None
    post_count_today: int = 0
    last_reset_date: str | None = None


def accounts_root_dir() -> Path:
    """Return the root directory for all account profiles."""
    return auth_root_dir() / _ACCOUNTS_DIR


def account_dir(account_id: str) -> Path:
    """Return the directory for a specific account."""
    return accounts_root_dir() / account_id


def account_metadata_path(account_id: str) -> Path:
    """Return the metadata file path for a specific account."""
    return account_dir(account_id) / _ACCOUNT_METADATA_FILE


def account_cookies_path(account_id: str) -> Path:
    """Return the cookies file path for a specific account."""
    return account_dir(account_id) / _ACCOUNT_COOKIES_FILE


def list_accounts() -> list[AccountMetadata]:
    """List all available Instagram accounts."""
    accounts_dir = accounts_root_dir()
    if not accounts_dir.exists():
        return []
    
    accounts = []
    for account_path in accounts_dir.iterdir():
        if not account_path.is_dir():
            continue
        
        metadata_path = account_metadata_path(account_path.name)
        if not metadata_path.exists():
            continue
        
        metadata = _load_account_metadata(metadata_path)
        if metadata:
            accounts.append(metadata)
    
    # Sort by last_used (most recent first)
    accounts.sort(key=lambda x: x.last_used or "", reverse=True)
    return accounts


def get_account(account_id: str) -> AccountMetadata | None:
    """Get metadata for a specific account."""
    metadata_path = account_metadata_path(account_id)
    if not metadata_path.exists():
        return None
    
    return _load_account_metadata(metadata_path)


def create_account(
    username: str,
    cookies: dict[str, str],
    full_name: str | None = None,
    profile_pic_url: str | None = None,
) -> AccountMetadata:
    """Create a new account profile with cookies."""
    account_id = _generate_account_id(username)
    account_path = account_dir(account_id)
    
    # Create account directory
    account_path.mkdir(parents=True, exist_ok=True)
    
    # Create metadata
    metadata = AccountMetadata(
        account_id=account_id,
        username=username,
        full_name=full_name,
        profile_pic_url=profile_pic_url,
        created_at=utcnow_iso(),
        last_used=utcnow_iso(),
        is_active=True,
    )
    
    # Write metadata
    _write_account_metadata(account_metadata_path(account_id), metadata)
    
    # Write cookies
    _write_account_cookies(account_cookies_path(account_id), cookies)
    
    logger.info(f"Created account profile: {username} ({account_id})")
    return metadata


def update_account_last_used(account_id: str) -> None:
    """Update the last_used timestamp for an account."""
    metadata = get_account(account_id)
    if not metadata:
        return
    
    metadata.last_used = utcnow_iso()
    _write_account_metadata(account_metadata_path(account_id), metadata)


def delete_account(account_id: str) -> bool:
    """Delete an account profile."""
    account_path = account_dir(account_id)
    if not account_path.exists():
        logger.warning(f"Account not found: {account_id}")
        return False
    
    try:
        import shutil
        shutil.rmtree(account_path)
        logger.info(f"Deleted account: {account_id}")
        return True
    except OSError as e:
        logger.error(f"Failed to delete account {account_id}: {e}")
        return False


def get_account_cookies(account_id: str) -> dict[str, str] | None:
    """Get cookies for a specific account."""
    cookies_path = account_cookies_path(account_id)
    if not cookies_path.exists():
        return None
    
    return _load_account_cookies(cookies_path)


def set_account_cookies(account_id: str, cookies: dict[str, str]) -> bool:
    """Update cookies for a specific account."""
    cookies_path = account_cookies_path(account_id)
    if not cookies_path.exists():
        logger.warning(f"Account not found: {account_id}")
        return False
    
    _write_account_cookies(cookies_path, cookies)
    update_account_last_used(account_id)
    return True


def get_active_account() -> AccountMetadata | None:
    """Get the most recently used active account."""
    accounts = list_accounts()
    for account in accounts:
        if account.is_active:
            return account
    return None


def set_default_account(account_id: str) -> bool:
    """Set an account as the default (active) account."""
    metadata = get_account(account_id)
    if not metadata:
        return False
    
    # Deactivate all accounts
    for account in list_accounts():
        if account.is_active:
            account.is_active = False
            _write_account_metadata(account_metadata_path(account.account_id), account)
    
    # Activate the specified account
    metadata.is_active = True
    metadata.last_used = utcnow_iso()
    _write_account_metadata(account_metadata_path(account_id), metadata)
    
    logger.info(f"Set default account: {metadata.username} ({account_id})")
    return True


def _generate_account_id(username: str) -> str:
    """Generate a unique account ID based on username."""
    # Simple approach: username + uuid suffix
    # In production, you might want to check for conflicts
    return f"{username.lower()}_{uuid4().hex[:8]}"


def _load_account_metadata(path: Path) -> AccountMetadata | None:
    """Load account metadata from file."""
    try:
        data = json.loads(path.read_text())
        return AccountMetadata(**data)
    except (OSError, json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to load account metadata from {path}: {e}")
        return None


def _write_account_metadata(path: Path, metadata: AccountMetadata) -> None:
    """Write account metadata to file."""
    secure_write_text(path, json.dumps(asdict(metadata), indent=2, sort_keys=True) + "\n")


def _load_account_cookies(path: Path) -> dict[str, str] | None:
    """Load account cookies from file."""
    try:
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return data
        # Handle list format
        if isinstance(data, list):
            cookies = {}
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookies[item["name"]] = item["value"]
            return cookies
        return None
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load cookies from {path}: {e}")
        return None


def _write_account_cookies(path: Path, cookies: dict[str, str]) -> None:
    """Write account cookies to file."""
    secure_write_text(path, json.dumps(cookies, indent=2, sort_keys=True) + "\n")


def check_account_posting_limits(account_id: str) -> tuple[bool, str]:
    """Check if account has reached posting limits.
    
    Args:
        account_id: Account ID to check
        
    Returns:
        Tuple of (can_post, reason)
    """
    account = get_account(account_id)
    if not account:
        return False, "Account not found"
    
    if not account.posting_enabled:
        return False, "Posting disabled for this account"
    
    # Check daily limit
    if account.daily_post_limit > 0:
        if account.post_count_today >= account.daily_post_limit:
            return False, f"Daily posting limit reached ({account.post_count_today}/{account.daily_post_limit})"
    
    # Check cooldown
    if account.last_post_time:
        from datetime import datetime, timedelta, timezone
        last_post = datetime.fromisoformat(account.last_post_time)
        cooldown = timedelta(minutes=30)  # 30-minute cooldown
        if datetime.now(timezone.utc) < last_post + cooldown:
            remaining = (last_post + cooldown) - datetime.now(timezone.utc)
            return False, f"Account in cooldown ({remaining.seconds//60} minutes remaining)"
    
    return True, ""


def increment_account_post_count(account_id: str) -> None:
    """Increment daily post count for account.
    
    Args:
        account_id: Account ID to increment
    """
    account = get_account(account_id)
    if not account:
        return
    
    from datetime import datetime
    
    # Reset count if new day
    if account.last_reset_date:
        last_reset = datetime.fromisoformat(account.last_reset_date)
        if last_reset.date() < datetime.now().date():
            account.post_count_today = 0
            account.last_reset_date = datetime.now().isoformat()
    
    account.post_count_today += 1
    account.last_post_time = datetime.now().isoformat()
    
    # Save updated metadata
    metadata_path = account_metadata_path(account_id)
    secure_write_text(metadata_path, json.dumps(asdict(account), indent=2) + "\n")


def get_account_posting_history(account_id: str, limit: int = 50) -> list[dict]:
    """Get posting history for an account.
    
    Args:
        account_id: Account ID to get history for
        limit: Maximum number of entries to return
        
    Returns:
        List of posting history entries
    """
    history_file = account_dir(account_id) / "posting-history.jsonl"
    
    if not history_file.exists():
        return []
    
    history = []
    try:
        with open(history_file) as f:
            for line in f.readlines()[-limit:]:
                history.append(json.loads(line))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load posting history for {account_id}: {e}")
    
    return history


def record_post_attempt(
    account_id: str,
    media_type: str,
    success: bool,
    post_id: str | None = None,
    error_message: str | None = None
) -> None:
    """Record a post attempt in account history.
    
    Args:
        account_id: Account ID
        media_type: Type of media (photo, video, carousel, story, reel)
        success: Whether the post was successful
        post_id: Instagram post ID if successful
        error_message: Error message if failed
    """
    history_file = account_dir(account_id) / "posting-history.jsonl"
    
    entry = {
        "timestamp": utcnow_iso(),
        "media_type": media_type,
        "success": success,
        "post_id": post_id,
        "error_message": error_message
    }
    
    try:
        with open(history_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError as e:
        logger.warning(f"Failed to record post attempt for {account_id}: {e}")
    
    # Update account metadata if successful
    if success:
        update_account_last_used(account_id)
        increment_account_post_count(account_id)
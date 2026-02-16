"""
API key authentication and usage tracking middleware for ContentSplit.
"""

import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import Header, HTTPException

# Usage storage (file-based; swap for Redis/DB in production)
USAGE_FILE = Path(__file__).parent / "data" / "usage.json"
KEYS_FILE = Path(__file__).parent / "data" / "api_keys.json"

# Plan limits (requests per month)
PLANS = {
    "free": {"limit": 50, "rate_per_min": 5, "platforms": ["twitter_thread", "linkedin", "summary"]},
    "starter": {"limit": 500, "rate_per_min": 30, "platforms": "all", "price": 9},
    "pro": {"limit": 5000, "rate_per_min": 60, "platforms": "all", "price": 29},
    "enterprise": {"limit": 50000, "rate_per_min": 120, "platforms": "all", "price": 99},
}


def _load_json(path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def get_or_create_key(email: str, plan: str = "free") -> str:
    """Create or retrieve an API key for a user."""
    import hashlib
    keys = _load_json(KEYS_FILE)
    
    # Check if email already has a key
    for key, info in keys.items():
        if info.get("email") == email:
            return key
    
    # Generate new key
    raw = f"{email}:{time.time()}:{os.urandom(16).hex()}"
    api_key = f"cs_{hashlib.sha256(raw.encode()).hexdigest()[:32]}"
    
    keys[api_key] = {
        "email": email,
        "plan": plan,
        "created": datetime.now().isoformat(),
        "active": True,
    }
    _save_json(KEYS_FILE, keys)
    return api_key


def validate_api_key(x_api_key: Optional[str] = Header(None)) -> dict:
    """Validate API key and check usage limits. Returns user info."""
    
    # Allow unauthenticated access for demo (free tier, very limited)
    if not x_api_key:
        return {"plan": "free", "email": "anonymous", "key": "anonymous"}
    
    keys = _load_json(KEYS_FILE)
    key_info = keys.get(x_api_key)
    
    if not key_info:
        raise HTTPException(401, "Invalid API key")
    
    if not key_info.get("active", True):
        raise HTTPException(403, "API key is deactivated")
    
    plan = key_info.get("plan", "free")
    plan_config = PLANS.get(plan, PLANS["free"])
    
    # Check monthly usage
    usage = _load_json(USAGE_FILE)
    month_key = datetime.now().strftime("%Y-%m")
    user_usage = usage.get(x_api_key, {}).get(month_key, 0)
    
    if user_usage >= plan_config["limit"]:
        raise HTTPException(
            429,
            f"Monthly limit reached ({plan_config['limit']} requests). Upgrade your plan at https://contentsplit.dev/pricing"
        )
    
    return {**key_info, "key": x_api_key, "plan": plan, "usage": user_usage, "limit": plan_config["limit"]}


def track_usage(api_key: str):
    """Increment usage counter for an API key."""
    usage = _load_json(USAGE_FILE)
    month_key = datetime.now().strftime("%Y-%m")
    
    if api_key not in usage:
        usage[api_key] = {}
    
    usage[api_key][month_key] = usage[api_key].get(month_key, 0) + 1
    _save_json(USAGE_FILE, usage)


def get_usage_stats(api_key: str) -> dict:
    """Get usage statistics for an API key."""
    usage = _load_json(USAGE_FILE)
    keys = _load_json(KEYS_FILE)
    
    key_info = keys.get(api_key, {})
    plan = key_info.get("plan", "free")
    plan_config = PLANS.get(plan, PLANS["free"])
    
    month_key = datetime.now().strftime("%Y-%m")
    current_usage = usage.get(api_key, {}).get(month_key, 0)
    
    return {
        "plan": plan,
        "current_month": month_key,
        "requests_used": current_usage,
        "requests_limit": plan_config["limit"],
        "requests_remaining": max(0, plan_config["limit"] - current_usage),
        "rate_per_min": plan_config["rate_per_min"],
    }

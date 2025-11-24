"""
Shared state module to avoid circular imports
"""
from typing import Dict, Any, Set
from fastapi import WebSocket

# Cache for broadcaster - single source of truth
BROADCASTER_CACHE: Dict[str, Any] = {
    "positions": None,
    "balance": None,
    "trades": None,
    "orders": None,
    "last_update": {
        "positions": 0,
        "balance": 0,
        "trades": 0,
        "orders": 0,
    }
}

# Set of connected WebSocket clients
BROADCAST_CLIENTS: Set[WebSocket] = set()

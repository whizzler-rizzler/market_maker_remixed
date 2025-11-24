"""
Bot logger - stores logs in memory for API access
"""
from collections import deque
from datetime import datetime
from typing import Dict, Any, List
import threading

# Thread-safe deque to store logs (max 500 entries)
LOG_BUFFER = deque(maxlen=500)
LOG_LOCK = threading.Lock()


def log_bot(message: str, level: str = "INFO"):
    """
    Add a bot log entry with timestamp
    
    Args:
        message: Log message
        level: Log level (INFO, WARNING, ERROR, DEBUG)
    """
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "message": message
    }
    
    with LOG_LOCK:
        LOG_BUFFER.append(entry)
    
    # Also print to console (for Render logs)
    print(f"[BOT {level}] {message}")


def get_bot_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get recent bot logs
    
    Args:
        limit: Maximum number of logs to return
    
    Returns:
        List of log entries (newest first)
    """
    with LOG_LOCK:
        logs = list(LOG_BUFFER)
    
    # Return newest first
    logs.reverse()
    return logs[:limit]


def clear_bot_logs():
    """Clear all bot logs"""
    with LOG_LOCK:
        LOG_BUFFER.clear()

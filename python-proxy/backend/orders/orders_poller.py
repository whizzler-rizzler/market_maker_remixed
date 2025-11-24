"""
Orders Poller - Fetches open orders from Extended API
Polls every 0.5 seconds (2x per second)
"""
import asyncio
import aiohttp
import os
from typing import Dict, Any, Optional
from datetime import datetime

# Extended API configuration
EXTENDED_API_KEY = os.getenv("Extended_1_API_KEY")
EXTENDED_API_BASE_URL = os.getenv("EXTENDED_API_BASE_URL", "https://api.starknet.extended.exchange/api/v1")
BASE_URL = EXTENDED_API_BASE_URL.rstrip("/")

# Cache for orders data
ORDERS_CACHE: Dict[str, Any] = {
    "orders": None,
    "last_update": 0,
}

async def fetch_open_orders() -> Optional[Dict[str, Any]]:
    """Fetch open orders from Extended API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}/orders",
                headers={
                    "X-Api-Key": EXTENDED_API_KEY,
                    "User-Agent": "extended-orders-poller/1.0",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=3.0)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ [ORDERS] Fetched {len(data.get('data', []))} open orders")
                    return data
                else:
                    print(f"❌ [ORDERS] HTTP {response.status}")
                    return None
    except Exception as e:
        print(f"❌ [ORDERS] Error fetching orders: {e}")
        return None

async def orders_poller():
    """Background task that polls orders every 0.5 seconds"""
    print("🚀 [ORDERS POLLER] Starting - polling every 0.5s (2x/sec)")
    
    while True:
        try:
            data = await fetch_open_orders()
            
            if data:
                ORDERS_CACHE["orders"] = data
                ORDERS_CACHE["last_update"] = int(datetime.now().timestamp() * 1000)
            
            # Wait 0.5 seconds before next poll (2x per second)
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"❌ [ORDERS POLLER] Error in poller loop: {e}")
            await asyncio.sleep(0.5)

def get_cached_orders() -> Dict[str, Any]:
    """Get cached orders data"""
    return {
        "status": "OK" if ORDERS_CACHE["orders"] else "NO_DATA",
        "data": ORDERS_CACHE["orders"].get("data", []) if ORDERS_CACHE["orders"] else [],
        "last_update": ORDERS_CACHE["last_update"],
    }

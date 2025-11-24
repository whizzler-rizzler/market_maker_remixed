from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiohttp
import asyncio
import os
from typing import Dict, Any, Set, Optional, Literal
import json
import time
from datetime import datetime
from order_manager import get_order_manager

app = FastAPI(title="Extended API Broadcaster Proxy")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from environment variables
EXTENDED_API_KEY = os.getenv("EXTENDED_API_KEY")
EXTENDED_API_BASE_URL = os.getenv("EXTENDED_API_BASE_URL", "https://api.starknet.extended.exchange/api/v1")
BASE_URL = EXTENDED_API_BASE_URL.rstrip("/")

if not EXTENDED_API_KEY:
    raise ValueError("EXTENDED_API_KEY environment variable is required")

print(f"✅ Extended API Key configured")
print(f"🎯 BASE_URL: {BASE_URL}")

# ============= BROADCASTER GLOBAL STATE =============
# Cache for broadcaster - this is the single source of truth
BROADCASTER_CACHE: Dict[str, Any] = {
    "positions": None,
    "balance": None,
    "trades": None,
    "last_update": {
        "positions": 0,
        "balance": 0,
        "trades": 0,
    }
}

# Set of connected WebSocket clients
BROADCAST_CLIENTS: Set[WebSocket] = set()

# Poller state tracking
TRADES_POLL_COUNTER = 0  # Counter to track when to poll trades (every 20 cycles = 5 seconds)


# ============= UTILITY FUNCTIONS =============
def data_changed(old_data: Any, new_data: Any) -> bool:
    """
    Compare two data structures to detect changes.
    Returns True if data is different.
    """
    if old_data is None and new_data is not None:
        return True
    if old_data is not None and new_data is None:
        return True
    # Convert to JSON strings for comparison (handles nested dicts/lists)
    return json.dumps(old_data, sort_keys=True) != json.dumps(new_data, sort_keys=True)


async def fetch_extended_api(endpoint: str) -> Dict[str, Any] | None:
    """
    Generic function to fetch data from Extended API.
    Returns None on error (silent fail for broadcaster).
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}{endpoint}",
                headers={
                    "X-Api-Key": EXTENDED_API_KEY,
                    "User-Agent": "extended-broadcaster/2.0",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=5.0)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"⚠️ [{endpoint}] HTTP {response.status}")
                    return None
    except Exception as e:
        print(f"❌ [{endpoint}] Error: {e}")
        return None


async def broadcast_to_clients(message: Dict[str, Any]):
    """
    Broadcast a message to all connected WebSocket clients.
    Removes disconnected clients automatically.
    """
    if not BROADCAST_CLIENTS:
        return  # No clients to broadcast to
    
    disconnected = set()
    message_json = json.dumps(message)
    
    for client in BROADCAST_CLIENTS:
        try:
            await client.send_text(message_json)
        except Exception as e:
            print(f"⚠️ [Broadcast] Failed to send to client: {e}")
            disconnected.add(client)
    
    # Remove disconnected clients
    for client in disconnected:
        BROADCAST_CLIENTS.discard(client)
        print(f"🗑️ [Broadcast] Removed disconnected client (remaining: {len(BROADCAST_CLIENTS)})")


# ============= BACKGROUND POLLER =============
async def poll_fast_data():
    """
    Poll positions and balance from Extended API (4x per second).
    Broadcasts changes to all connected clients.
    """
    # Fetch positions and balance in parallel
    positions_task = fetch_extended_api("/user/positions")
    balance_task = fetch_extended_api("/user/balance")
    
    new_positions, new_balance = await asyncio.gather(
        positions_task,
        balance_task,
        return_exceptions=True
    )
    
    # Handle positions update
    if not isinstance(new_positions, Exception) and new_positions is not None:
        if data_changed(BROADCASTER_CACHE["positions"], new_positions):
            BROADCASTER_CACHE["positions"] = new_positions
            BROADCASTER_CACHE["last_update"]["positions"] = time.time()
            print(f"📊 [Broadcaster] Positions changed - broadcasting to {len(BROADCAST_CLIENTS)} clients")
            await broadcast_to_clients({
                "type": "positions",
                "data": new_positions,
                "timestamp": time.time()
            })
    
    # Handle balance update
    if not isinstance(new_balance, Exception) and new_balance is not None:
        if data_changed(BROADCASTER_CACHE["balance"], new_balance):
            BROADCASTER_CACHE["balance"] = new_balance
            BROADCASTER_CACHE["last_update"]["balance"] = time.time()
            print(f"💰 [Broadcaster] Balance changed - broadcasting to {len(BROADCAST_CLIENTS)} clients")
            await broadcast_to_clients({
                "type": "balance",
                "data": new_balance,
                "timestamp": time.time()
            })


async def poll_trades():
    """
    Poll trades from Extended API (1x per 5 seconds).
    Broadcasts changes to all connected clients.
    """
    new_trades = await fetch_extended_api("/user/trades")
    
    if new_trades is not None:
        if data_changed(BROADCASTER_CACHE["trades"], new_trades):
            BROADCASTER_CACHE["trades"] = new_trades
            BROADCASTER_CACHE["last_update"]["trades"] = time.time()
            print(f"📜 [Broadcaster] Trades changed - broadcasting to {len(BROADCAST_CLIENTS)} clients")
            await broadcast_to_clients({
                "type": "trades",
                "data": new_trades,
                "timestamp": time.time()
            })


async def background_poller():
    """
    Main background task that continuously polls Extended API.
    - Fast loop (250ms): positions + balance (4x/sec)
    - Slow loop (5000ms): trades (1x/5sec = every 20 fast cycles)
    """
    global TRADES_POLL_COUNTER
    
    print("🚀 [Broadcaster] Background poller started")
    
    while True:
        try:
            # Fast polling: positions + balance
            await poll_fast_data()
            
            # Slow polling: trades (every 20 cycles = 5 seconds)
            TRADES_POLL_COUNTER += 1
            if TRADES_POLL_COUNTER >= 20:
                await poll_trades()
                TRADES_POLL_COUNTER = 0
            
            # Wait 250ms before next cycle (4x per second)
            await asyncio.sleep(0.25)
            
        except Exception as e:
            print(f"❌ [Broadcaster] Poller error: {e}")
            # Continue running even if error occurs
            await asyncio.sleep(1)


# ============= STARTUP EVENT =============
@app.on_event("startup")
async def startup_broadcaster():
    """
    Start the background poller when the app starts.
    """
    print("⚡ [Startup] Initializing broadcaster...")
    asyncio.create_task(background_poller())
    print("✅ [Startup] Broadcaster initialized")


# ============= REST API ENDPOINTS =============
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "extended-broadcaster-proxy",
        "broadcaster": {
            "connected_clients": len(BROADCAST_CLIENTS),
            "cache_initialized": all([
                BROADCASTER_CACHE["positions"] is not None,
                BROADCASTER_CACHE["balance"] is not None,
                BROADCASTER_CACHE["trades"] is not None,
            ])
        }
    }


@app.get("/api/cached-account")
async def get_cached_account():
    """
    Return cached account data from broadcaster.
    
    ✅ NO rate limits - served from memory
    ✅ Frontend can call 100x/s if needed
    ✅ Zero Extended API calls
    
    Returns the latest cached data with cache age information.
    """
    current_time = time.time()
    
    return {
        "positions": BROADCASTER_CACHE["positions"] or [],
        "balance": BROADCASTER_CACHE["balance"],
        "trades": BROADCASTER_CACHE["trades"] or [],
        "cache_age_ms": {
            "positions": int((current_time - BROADCASTER_CACHE["last_update"]["positions"]) * 1000) if BROADCASTER_CACHE["last_update"]["positions"] > 0 else None,
            "balance": int((current_time - BROADCASTER_CACHE["last_update"]["balance"]) * 1000) if BROADCASTER_CACHE["last_update"]["balance"] > 0 else None,
            "trades": int((current_time - BROADCASTER_CACHE["last_update"]["trades"]) * 1000) if BROADCASTER_CACHE["last_update"]["trades"] > 0 else None,
        },
        "last_update": {
            "positions": BROADCASTER_CACHE["last_update"]["positions"],
            "balance": BROADCASTER_CACHE["last_update"]["balance"],
            "trades": BROADCASTER_CACHE["last_update"]["trades"],
        }
    }


@app.get("/api/broadcaster/stats")
async def broadcaster_stats():
    """
    Get broadcaster statistics and monitoring info.
    Useful for debugging and monitoring.
    """
    current_time = time.time()
    
    return {
        "broadcaster": {
            "connected_clients": len(BROADCAST_CLIENTS),
            "extended_api_rate": "4x/s (positions+balance), 1x/5s (trades)",
            "total_requests_to_extended": "4 req/s regardless of frontend clients"
        },
        "cache": {
            "positions_initialized": BROADCASTER_CACHE["positions"] is not None,
            "balance_initialized": BROADCASTER_CACHE["balance"] is not None,
            "trades_initialized": BROADCASTER_CACHE["trades"] is not None,
            "positions_age_seconds": int(current_time - BROADCASTER_CACHE["last_update"]["positions"]) if BROADCASTER_CACHE["last_update"]["positions"] > 0 else None,
            "balance_age_seconds": int(current_time - BROADCASTER_CACHE["last_update"]["balance"]) if BROADCASTER_CACHE["last_update"]["balance"] > 0 else None,
            "trades_age_seconds": int(current_time - BROADCASTER_CACHE["last_update"]["trades"]) if BROADCASTER_CACHE["last_update"]["trades"] > 0 else None,
        },
        "last_poll": {
            "positions": BROADCASTER_CACHE["last_update"]["positions"],
            "balance": BROADCASTER_CACHE["last_update"]["balance"],
            "trades": BROADCASTER_CACHE["last_update"]["trades"],
        }
    }


# ============= WEBSOCKET BROADCAST ENDPOINT =============
@app.websocket("/ws/broadcast")
async def websocket_broadcast(websocket: WebSocket):
    """
    WebSocket endpoint for broadcasting real-time updates.
    
    Flow:
    1. Client connects
    2. Immediately send full snapshot of cached data
    3. Client waits for diff updates (only changes are broadcasted)
    4. Keep-alive with ping/pong
    """
    await websocket.accept()
    print(f"✅ [WS] New client connected (total: {len(BROADCAST_CLIENTS) + 1})")
    
    # Add client to broadcast set
    BROADCAST_CLIENTS.add(websocket)
    
    try:
        # Step 1: Send immediate snapshot of current cached data
        snapshot = {
            "type": "snapshot",
            "positions": BROADCASTER_CACHE["positions"],
            "balance": BROADCASTER_CACHE["balance"],
            "trades": BROADCASTER_CACHE["trades"],
            "timestamp": time.time()
        }
        await websocket.send_json(snapshot)
        print(f"📸 [WS] Sent snapshot to client")
        
        # Step 2: Keep connection alive and wait for broadcasts
        # The background poller will automatically send updates via broadcast_to_clients()
        while True:
            try:
                # Ping every 30 seconds to keep connection alive
                await asyncio.sleep(30)
                await websocket.send_json({"type": "ping", "timestamp": time.time()})
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"⚠️ [WS] Error in keep-alive: {e}")
                break
                
    except WebSocketDisconnect:
        print(f"👋 [WS] Client disconnected gracefully")
    except Exception as e:
        print(f"❌ [WS] Connection error: {e}")
    finally:
        # Remove client from broadcast set
        BROADCAST_CLIENTS.discard(websocket)
        print(f"🗑️ [WS] Client removed (remaining: {len(BROADCAST_CLIENTS)})")


# ============= ORDER MANAGEMENT ENDPOINTS =============

class CreateOrderRequest(BaseModel):
    market: str
    side: Literal["BUY", "SELL"]
    price: str
    size: str
    timeInForce: Literal["POST_ONLY", "GTC", "IOC", "FOK"] = "POST_ONLY"
    reduceOnly: bool = False

@app.post("/api/orders/create")
async def create_order(order_request: CreateOrderRequest):
    """
    Create a new order on Extended Exchange
    Supports POST_ONLY for market making
    """
    try:
        manager = get_order_manager()
        result = await manager.create_order(
            market=order_request.market,
            side=order_request.side,
            price=order_request.price,
            size=order_request.size,
            time_in_force=order_request.timeInForce,
            reduce_only=order_request.reduceOnly,
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=result.get("error", "Order creation failed")
            )
    except Exception as e:
        print(f"❌ Error in create_order endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orders")
async def get_open_orders(market: Optional[str] = None):
    """
    Get all open orders, optionally filtered by market
    """
    try:
        manager = get_order_manager()
        result = await manager.get_open_orders(market=market)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=result.get("error", "Failed to fetch orders")
            )
    except Exception as e:
        print(f"❌ Error in get_open_orders endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/orders/{order_id}")
async def cancel_order(order_id: str):
    """
    Cancel an order by ID
    """
    try:
        manager = get_order_manager()
        result = await manager.cancel_order(order_id)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=result.get("status", 500),
                detail=result.get("error", "Failed to cancel order")
            )
    except Exception as e:
        print(f"❌ Error in cancel_order endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= LEGACY ENDPOINTS (for backward compatibility) =============
@app.get("/api/account/info")
async def get_account_info():
    """Get account information (direct proxy to Extended API)"""
    result = await fetch_extended_api("/user/account/info")
    if result is None:
        raise HTTPException(status_code=503, detail="Extended API unavailable")
    return result


@app.get("/api/positions")
async def get_positions():
    """Get user positions (direct proxy to Extended API)"""
    result = await fetch_extended_api("/user/positions")
    if result is None:
        raise HTTPException(status_code=503, detail="Extended API unavailable")
    return result


@app.get("/api/balance")
async def get_balance():
    """Get user balance (direct proxy to Extended API)"""
    result = await fetch_extended_api("/user/balance")
    if result is None:
        raise HTTPException(status_code=503, detail="Extended API unavailable")
    return result


@app.get("/api/trades")
async def get_trades():
    """Get user trades history (direct proxy to Extended API)"""
    result = await fetch_extended_api("/user/trades")
    if result is None:
        raise HTTPException(status_code=503, detail="Extended API unavailable")
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

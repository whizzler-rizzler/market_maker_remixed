from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiohttp
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, Set, Optional, Literal
import json
import time
from datetime import datetime

# Add parent directory to Python path to import bot module
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.order_manager import get_order_manager
from bot.price_feed import start_price_feed

# Try to import bot module with error handling
try:
    from bot.simple_mm_bot import start_bot, stop_bot, get_bot_status, config as bot_config
    print("✅ Bot module imported successfully")
    BOT_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Bot module import failed: {e}")
    BOT_AVAILABLE = False
    # Define dummy functions if import fails
    async def start_bot(): return {"error": "Bot module not available"}
    async def stop_bot(): return {"error": "Bot module not available"}
    def get_bot_status(): return {"error": "Bot module not available"}
    class bot_config:
        enabled = False

# Import orders poller
from backend.orders.orders_poller import orders_poller, get_cached_orders, ORDERS_CACHE

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
EXTENDED_API_KEY = os.getenv("Extended_1_API_KEY")
EXTENDED_API_BASE_URL = os.getenv("EXTENDED_API_BASE_URL", "https://api.starknet.extended.exchange/api/v1")
BASE_URL = EXTENDED_API_BASE_URL.rstrip("/")

if not EXTENDED_API_KEY:
    raise ValueError("Extended_1_API_KEY environment variable is required")

print(f"✅ Extended API Key configured")
print(f"🎯 BASE_URL: {BASE_URL}")

# ============= BROADCASTER GLOBAL STATE =============
# Import shared state to avoid circular dependencies
from backend.shared_state import BROADCASTER_CACHE, BROADCAST_CLIENTS

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
    
    # Start orders poller in separate task
    asyncio.create_task(orders_poller())
    
    prev_orders = None
    
    while True:
        try:
            # Fast polling: positions + balance
            await poll_fast_data()
            
            # Slow polling: trades (every 20 cycles = 5 seconds)
            TRADES_POLL_COUNTER += 1
            if TRADES_POLL_COUNTER >= 20:
                await poll_trades()
                TRADES_POLL_COUNTER = 0
            
            # Sync orders from poller to broadcaster cache
            if ORDERS_CACHE["orders"]:
                current_orders = ORDERS_CACHE["orders"].get("data", [])
                BROADCASTER_CACHE["orders"] = current_orders
                BROADCASTER_CACHE["last_update"]["orders"] = ORDERS_CACHE["last_update"]
                
                # Broadcast orders diff if changed
                if current_orders != prev_orders:
                    await broadcast_to_clients({
                        "type": "orders",
                        "data": current_orders,
                        "timestamp": int(time.time() * 1000)
                    })
                    prev_orders = current_orders
            
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
    Start the background poller and price feed when the app starts.
    """
    print("⚡ [Startup] Initializing broadcaster...")
    asyncio.create_task(background_poller())
    print("✅ [Startup] Broadcaster initialized")
    
    # Start price feed WebSocket
    print("⚡ [Startup] Initializing price feed...")
    start_price_feed()
    print("✅ [Startup] Price feed initialized")


# ============= REST API ENDPOINTS =============
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "extended-broadcaster-proxy",
        "bot_module_available": BOT_AVAILABLE,
        "broadcaster": {
            "connected_clients": len(BROADCAST_CLIENTS),
            "cache_initialized": all([
                BROADCASTER_CACHE["positions"] is not None,
                BROADCASTER_CACHE["balance"] is not None,
                BROADCASTER_CACHE["trades"] is not None,
                BROADCASTER_CACHE["orders"] is not None,
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
        "orders": BROADCASTER_CACHE["orders"] or [],
        "cache_age_ms": {
            "positions": int((current_time - BROADCASTER_CACHE["last_update"]["positions"]) * 1000) if BROADCASTER_CACHE["last_update"]["positions"] > 0 else None,
            "balance": int((current_time - BROADCASTER_CACHE["last_update"]["balance"]) * 1000) if BROADCASTER_CACHE["last_update"]["balance"] > 0 else None,
            "trades": int((current_time - BROADCASTER_CACHE["last_update"]["trades"]) * 1000) if BROADCASTER_CACHE["last_update"]["trades"] > 0 else None,
            "orders": int((current_time - BROADCASTER_CACHE["last_update"]["orders"]) * 1000) if BROADCASTER_CACHE["last_update"]["orders"] > 0 else None,
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
            "orders_initialized": BROADCASTER_CACHE["orders"] is not None,
            "positions_age_seconds": int(current_time - BROADCASTER_CACHE["last_update"]["positions"]) if BROADCASTER_CACHE["last_update"]["positions"] > 0 else None,
            "balance_age_seconds": int(current_time - BROADCASTER_CACHE["last_update"]["balance"]) if BROADCASTER_CACHE["last_update"]["balance"] > 0 else None,
            "trades_age_seconds": int(current_time - BROADCASTER_CACHE["last_update"]["trades"]) if BROADCASTER_CACHE["last_update"]["trades"] > 0 else None,
            "orders_age_seconds": int(current_time - BROADCASTER_CACHE["last_update"]["orders"]) if BROADCASTER_CACHE["last_update"]["orders"] > 0 else None,
        },
        "last_poll": {
            "positions": BROADCASTER_CACHE["last_update"]["positions"],
            "balance": BROADCASTER_CACHE["last_update"]["balance"],
            "trades": BROADCASTER_CACHE["last_update"]["trades"],
            "orders": BROADCASTER_CACHE["last_update"]["orders"],
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
            "orders": BROADCASTER_CACHE["orders"],
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
async def get_open_orders():
    """
    Get cached open orders from orders poller (2x per second refresh)
    ✅ NO rate limits - served from memory
    ✅ Orders are polled separately every 0.5s
    """
    return get_cached_orders()

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


# ============= MARKET MAKING BOT ENDPOINTS =============
from bot.bot_logger import get_bot_logs, clear_bot_logs

@app.get("/api/bot/logs")
async def api_bot_logs(limit: int = 100):
    """Get recent bot logs from memory"""
    try:
        logs = get_bot_logs(limit=limit)
        return {
            "logs": logs,
            "total": len(logs)
        }
    except Exception as e:
        print(f"❌ Error getting bot logs: {e}")


@app.get("/api/orders")
async def api_orders():
    """Get cached open orders (polled 2x/sec)"""
    try:
        return get_cached_orders()
    except Exception as e:
        print(f"❌ Error getting orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/bot-logs")
async def websocket_bot_logs(websocket: WebSocket):
    """
    WebSocket endpoint for LIVE bot log streaming
    Sends new logs in real-time as they appear
    """
    await websocket.accept()
    print(f"✅ [WS Bot Logs] Client connected")
    
    try:
        # Send initial snapshot of existing logs
        existing_logs = get_bot_logs(limit=100)
        await websocket.send_json({
            "type": "snapshot",
            "logs": existing_logs
        })
        
        # Track last known log count to detect new logs
        last_log_count = len(existing_logs)
        
        # Keep connection alive and check for new logs every 500ms
        while True:
            await asyncio.sleep(0.5)
            
            current_logs = get_bot_logs(limit=100)
            current_count = len(current_logs)
            
            # If new logs appeared, send only the new ones
            if current_count > last_log_count:
                new_logs = current_logs[:current_count - last_log_count]
                await websocket.send_json({
                    "type": "new_logs",
                    "logs": new_logs
                })
                last_log_count = current_count
                
    except WebSocketDisconnect:
        print(f"👋 [WS Bot Logs] Client disconnected")
    except Exception as e:
        print(f"❌ [WS Bot Logs] Error: {e}")
    finally:
        print(f"🗑️ [WS Bot Logs] Connection closed")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/bot/logs")
async def api_clear_bot_logs():
    """Clear all bot logs"""
    try:
        clear_bot_logs()
        return {"status": "cleared"}
    except Exception as e:
        print(f"❌ Error clearing bot logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/start")
async def api_start_bot():
    """Start the market making bot"""
    try:
        if not BOT_AVAILABLE:
            raise HTTPException(status_code=503, detail="Bot module not available")
        result = await start_bot()
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/stop")
async def api_stop_bot():
    """Stop the market making bot"""
    try:
        if not BOT_AVAILABLE:
            raise HTTPException(status_code=503, detail="Bot module not available")
        result = await stop_bot()
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error stopping bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bot/status")
async def api_bot_status():
    """Get current bot status and statistics"""
    try:
        if not BOT_AVAILABLE:
            raise HTTPException(status_code=503, detail="Bot module not available")
        return get_bot_status()
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting bot status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BotConfigUpdate(BaseModel):
    market: Optional[str] = None
    spread_percentage: Optional[float] = None
    order_size: Optional[str] = None
    refresh_interval: Optional[int] = None
    price_move_threshold: Optional[float] = None


@app.post("/api/bot/config")
async def api_update_bot_config(update: BotConfigUpdate):
    """Update bot configuration (only when bot is stopped)"""
    try:
        if not BOT_AVAILABLE:
            raise HTTPException(status_code=503, detail="Bot module not available")
        
        if bot_config.enabled:
            raise HTTPException(
                status_code=400, 
                detail="Cannot update config while bot is running. Stop the bot first."
            )
        
        if update.market is not None:
            bot_config.market = update.market
        if update.spread_percentage is not None:
            bot_config.spread_percentage = update.spread_percentage
        if update.order_size is not None:
            bot_config.order_size = update.order_size
        if update.refresh_interval is not None:
            bot_config.refresh_interval = update.refresh_interval
        if update.price_move_threshold is not None:
            bot_config.price_move_threshold = update.price_move_threshold
        
        return {
            "status": "updated",
            "config": {
                "market": bot_config.market,
                "spread_percentage": bot_config.spread_percentage,
                "order_size": bot_config.order_size,
                "refresh_interval": bot_config.refresh_interval,
                "price_move_threshold": bot_config.price_move_threshold
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating bot config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

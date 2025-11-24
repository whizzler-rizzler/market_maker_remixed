"""
FastAPI Backend - Simplified
Core endpoints only: bot control + account data
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add bot to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.simple_mm_bot import start_bot, stop_bot, get_status, get_pnl
from bot.order_manager import get_order_manager
from bot.config import config

app = FastAPI(title="Bot_lovable API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check if credentials are configured (optional - only needed when using bot)
def check_credentials():
    """Check if Extended credentials exist"""
    for key in os.environ.keys():
        if key.startswith("Extended_1_API_KEY"):
            return True
    return False

EXTENDED_API_KEY = check_credentials()
if EXTENDED_API_KEY:
    print(f"✅ Extended API credentials configured")
else:
    print(f"⚠️ Extended API credentials not set - bot features will be disabled")


# ============= MODELS =============
class OrderRequest(BaseModel):
    market: str
    side: str  # BUY or SELL
    price: str
    size: str
    post_only: bool = True

class BotConfigUpdate(BaseModel):
    market: str | None = None
    spread: float | None = None
    size: str | None = None
    refresh_interval: int | None = None


# ============= ENDPOINTS =============
@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "service": "bot_lovable"}


@app.get("/api/bot/status")
async def bot_status():
    """Get bot status"""
    if not EXTENDED_API_KEY:
        return {"error": "Extended API credentials not configured"}
    
    status = get_status()
    pnl = await get_pnl()
    return {**status, **pnl}


@app.post("/api/bot/start")
async def bot_start():
    """Start market making bot"""
    if not EXTENDED_API_KEY:
        raise HTTPException(status_code=400, detail="Extended API credentials not configured")
    
    result = await start_bot()
    return result


@app.post("/api/bot/stop")
async def bot_stop():
    """Stop bot"""
    if not EXTENDED_API_KEY:
        raise HTTPException(status_code=400, detail="Extended API credentials not configured")
    
    result = await stop_bot()
    return result


@app.post("/api/orders")
async def create_order(request: OrderRequest):
    """Create order manually"""
    if not EXTENDED_API_KEY:
        raise HTTPException(status_code=400, detail="Extended API credentials not configured")
    
    order_mgr = get_order_manager()
    
    # Validate side
    if request.side not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="side must be BUY or SELL")
    
    result = await order_mgr.create_order(
        market=request.market,
        side=request.side,  # type: ignore
        price=request.price,
        size=request.size,
        post_only=request.post_only
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@app.get("/api/positions")
async def get_positions():
    """Get current positions"""
    if not EXTENDED_API_KEY:
        raise HTTPException(status_code=400, detail="Extended API credentials not configured")
    
    order_mgr = get_order_manager()
    result = await order_mgr.get_positions()
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result["data"]


@app.get("/api/balance")
async def get_balance():
    """Get account balance"""
    if not EXTENDED_API_KEY:
        raise HTTPException(status_code=400, detail="Extended API credentials not configured")
    
    order_mgr = get_order_manager()
    result = await order_mgr.get_balance()
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result["data"]


@app.get("/api/pnl")
async def get_pnl_endpoint():
    """Get current PnL"""
    if not EXTENDED_API_KEY:
        raise HTTPException(status_code=400, detail="Extended API credentials not configured")
    
    pnl = await get_pnl()
    return pnl


@app.get("/api/bot/config")
async def get_config():
    """Get current bot configuration"""
    return {
        "market": config.market,
        "spread": config.spread_percentage,
        "size": config.order_size,
        "refresh_interval": config.refresh_interval
    }


@app.post("/api/bot/config")
async def update_config(updates: BotConfigUpdate):
    """Update bot configuration (restart required to apply)"""
    changed = []
    
    if updates.market is not None:
        config.market = updates.market
        changed.append(f"market={updates.market}")
    
    if updates.spread is not None:
        config.spread_percentage = updates.spread
        changed.append(f"spread={updates.spread}")
    
    if updates.size is not None:
        config.order_size = updates.size
        changed.append(f"size={updates.size}")
    
    if updates.refresh_interval is not None:
        config.refresh_interval = updates.refresh_interval
        changed.append(f"refresh_interval={updates.refresh_interval}")
    
    return {
        "success": True,
        "message": f"Configuration updated: {', '.join(changed)}",
        "note": "Restart bot to apply changes",
        "config": {
            "market": config.market,
            "spread": config.spread_percentage,
            "size": config.order_size,
            "refresh_interval": config.refresh_interval
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)

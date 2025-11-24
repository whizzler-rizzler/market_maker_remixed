"""
Simple Market Making Bot - Core Functions Only
- POST_ONLY orders
- Position management  
- Basic PnL tracking
"""
import asyncio
from typing import Dict, Optional, Any
from decimal import Decimal
from .config import config
from .order_manager import get_order_manager
from .price_feed import get_price, start_price_feed


# Bot state
ACTIVE_ORDERS: Dict[str, Dict] = {}
LAST_PRICE: float = 0
STARTING_EQUITY: float = 0
bot_task: Optional[asyncio.Task] = None


def calculate_quotes(price: float, spread: float) -> tuple[float, float]:
    """Calculate bid/ask around market price"""
    bid = price * (1 - spread)
    ask = price * (1 + spread)
    
    # SDK will handle price rounding in create_order()
    return (bid, ask)


async def get_market_price(market: str) -> float:
    """
    Get current market price from WebSocket price feed
    """
    price = get_price(market)
    
    if price is None:
        raise ValueError(f"No price available for {market} - WebSocket may not be connected")
    
    return price


async def place_orders(bid: float, ask: float, size: str, market: str):
    """Place POST_ONLY bid and ask orders"""
    global ACTIVE_ORDERS
    
    order_mgr = get_order_manager()
    
    # Place both orders
    buy_result = await order_mgr.create_order(
        market=market,
        side="BUY",
        price=str(bid),
        size=size,
        post_only=True
    )
    
    sell_result = await order_mgr.create_order(
        market=market,
        side="SELL",
        price=str(ask),
        size=size,
        post_only=True
    )
    
    # Track successful orders
    if buy_result.get("success"):
        order_id = buy_result["data"]["id"]
        ACTIVE_ORDERS[order_id] = {"side": "BUY", "price": bid}
        print(f"✅ BUY @ {bid:.2f}")
    
    if sell_result.get("success"):
        order_id = sell_result["data"]["id"]
        ACTIVE_ORDERS[order_id] = {"side": "SELL", "price": ask}
        print(f"✅ SELL @ {ask:.2f}")


async def cancel_all_orders():
    """Cancel all bot orders"""
    global ACTIVE_ORDERS
    
    order_mgr = get_order_manager()
    
    for order_id in list(ACTIVE_ORDERS.keys()):
        await order_mgr.cancel_order(order_id)
    
    count = len(ACTIVE_ORDERS)
    ACTIVE_ORDERS.clear()
    print(f"🗑️ Cancelled {count} orders")


async def get_pnl() -> Dict[str, float]:
    """Calculate basic PnL"""
    global STARTING_EQUITY
    
    order_mgr = get_order_manager()
    balance_result = await order_mgr.get_balance()
    
    if balance_result["success"]:
        current_equity = float(balance_result["data"]["equity"] or 0)
        
        if STARTING_EQUITY == 0:
            STARTING_EQUITY = current_equity
        
        pnl = current_equity - STARTING_EQUITY
        pnl_pct = (pnl / STARTING_EQUITY * 100) if STARTING_EQUITY > 0 else 0
        
        return {
            "starting_equity": STARTING_EQUITY,
            "current_equity": current_equity,
            "pnl": pnl,
            "pnl_pct": pnl_pct
        }
    
    return {"pnl": 0, "pnl_pct": 0}


async def bot_main_loop():
    """Main bot loop - simplified"""
    global LAST_PRICE
    
    print("🤖 Bot started")
    
    # Start price feed
    start_price_feed()
    
    # Wait for initial prices
    print("⏳ Waiting for price feed...")
    for i in range(10):
        price = get_price(config.market)
        if price:
            print(f"✅ Got initial price: ${price:,.2f}")
            break
        await asyncio.sleep(1)
    else:
        print("⚠️ No initial price after 10s - continuing anyway")
    
    try:
        while config.enabled:
            # Get current price
            try:
                current_price = await get_market_price(config.market)
            except Exception as e:
                print(f"❌ Price error: {e}")
                await asyncio.sleep(config.refresh_interval)
                continue
            
            # Refresh if price changed significantly (or first run)
            price_change = abs(current_price - LAST_PRICE) / LAST_PRICE if LAST_PRICE > 0 else 1.0
            
            if price_change > 0.002:  # 0.2% threshold (or first run)
                await cancel_all_orders()
                
                bid, ask = calculate_quotes(current_price, config.spread_percentage)
                await place_orders(bid, ask, config.order_size, config.market)
                
                LAST_PRICE = current_price
                print(f"📊 Quotes: {bid:.2f} / {ask:.2f}")
            
            # Sleep
            await asyncio.sleep(config.refresh_interval)
    
    except Exception as e:
        print(f"❌ Bot error: {e}")
        config.enabled = False
    finally:
        await cancel_all_orders()
        print("🛑 Bot stopped")


async def start_bot() -> Dict[str, Any]:
    """Start bot"""
    global bot_task, LAST_PRICE, STARTING_EQUITY
    
    if bot_task and not bot_task.done():
        return {"status": "already_running"}
    
    # Reset
    LAST_PRICE = 0
    STARTING_EQUITY = 0
    ACTIVE_ORDERS.clear()
    
    config.enabled = True
    bot_task = asyncio.create_task(bot_main_loop())
    
    return {
        "status": "started",
        "config": {
            "market": config.market,
            "spread": config.spread_percentage,
            "size": config.order_size
        }
    }


async def stop_bot() -> Dict[str, Any]:
    """Stop bot"""
    global bot_task
    
    config.enabled = False
    
    if bot_task:
        await bot_task
        bot_task = None
    
    await cancel_all_orders()
    
    return {"status": "stopped"}


def get_status() -> Dict[str, Any]:
    """Get bot status"""
    return {
        "running": config.enabled,
        "active_orders": len(ACTIVE_ORDERS),
        "last_price": LAST_PRICE,
        "market": config.market
    }

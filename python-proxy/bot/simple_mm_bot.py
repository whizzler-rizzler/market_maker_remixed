"""
Simple Market Making Bot
Automatically places and refreshes POST_ONLY bid/ask orders around market price
"""
import asyncio
from typing import Dict, Optional, Any
from .config import config
from order_manager import get_order_manager

# Global state
ACTIVE_BOT_ORDERS: Dict[str, Dict] = {}
LAST_QUOTE_PRICE: float = 0
bot_task: Optional[asyncio.Task] = None


def get_current_price(market: str) -> float:
    """
    Get current market price from broadcaster cache or public prices
    """
    # Import here to avoid circular dependency
    from main import BROADCASTER_CACHE
    
    # Try to get from positions data
    positions = BROADCASTER_CACHE.get("positions", {})
    if isinstance(positions, dict) and "data" in positions:
        for position in positions["data"]:
            if position.get("market") == market:
                mark_price = position.get("mark_price")
                if mark_price:
                    return float(mark_price)
    
    # Try to get from balance data (has mark prices)
    balance = BROADCASTER_CACHE.get("balance", {})
    if isinstance(balance, dict) and "data" in balance:
        mark_prices = balance.get("data", {}).get("mark_prices", {})
        if market in mark_prices:
            return float(mark_prices[market])
    
    raise ValueError(f"Could not find price for market {market}")


def calculate_quotes(price: float, spread: float) -> tuple[float, float]:
    """
    Calculate bid and ask prices around market price
    """
    bid_price = price * (1 - spread)
    ask_price = price * (1 + spread)
    return (bid_price, ask_price)


async def place_mm_orders(bid: float, ask: float, size: str, market: str) -> Dict[str, str]:
    """
    Place POST_ONLY bid and ask orders
    """
    global ACTIVE_BOT_ORDERS
    
    order_manager = get_order_manager()
    
    # Place BUY order
    buy_order = await asyncio.to_thread(
        order_manager.create_order,
        market=market,
        side="BUY",
        price=str(bid),
        size=size,
        time_in_force="POST_ONLY",
        reduce_only=False
    )
    
    # Place SELL order
    sell_order = await asyncio.to_thread(
        order_manager.create_order,
        market=market,
        side="SELL",
        price=str(ask),
        size=size,
        time_in_force="POST_ONLY",
        reduce_only=False
    )
    
    # Track orders
    buy_order_id = buy_order.get("data", {}).get("order_id")
    sell_order_id = sell_order.get("data", {}).get("order_id")
    
    if buy_order_id:
        ACTIVE_BOT_ORDERS[buy_order_id] = {"side": "BUY", "price": bid, "size": size}
    if sell_order_id:
        ACTIVE_BOT_ORDERS[sell_order_id] = {"side": "SELL", "price": ask, "size": size}
    
    print(f"✅ Bot orders placed: BUY @ {bid:.2f}, SELL @ {ask:.2f}")
    
    return {"buy_order_id": buy_order_id, "sell_order_id": sell_order_id}


async def cancel_all_bot_orders():
    """
    Cancel all active bot orders
    """
    global ACTIVE_BOT_ORDERS
    
    if len(ACTIVE_BOT_ORDERS) == 0:
        return
    
    order_manager = get_order_manager()
    order_ids = list(ACTIVE_BOT_ORDERS.keys())
    
    for order_id in order_ids:
        try:
            await asyncio.to_thread(order_manager.cancel_order, order_id)
        except Exception as e:
            print(f"⚠️ Failed to cancel order {order_id}: {e}")
    
    count = len(ACTIVE_BOT_ORDERS)
    ACTIVE_BOT_ORDERS.clear()
    print(f"🗑️ Cancelled {count} bot orders")


def should_refresh_quotes(current_price: float, last_price: float, threshold: float) -> bool:
    """
    Check if quotes should be refreshed based on price movement
    """
    if last_price == 0:
        return True
    
    price_change = abs(current_price - last_price) / last_price
    
    if price_change > threshold:
        print(f"🔄 Price changed {price_change:.2%}, refreshing quotes")
        return True
    
    return False


async def bot_main_loop():
    """
    Main bot loop - continuously monitors price and refreshes quotes
    """
    global LAST_QUOTE_PRICE, ACTIVE_BOT_ORDERS
    
    print("🚀 Market Making Bot started")
    
    try:
        while config.enabled:
            # 1. Get current price
            try:
                current_price = get_current_price(config.market)
            except Exception as e:
                print(f"❌ Failed to get price: {e}")
                await asyncio.sleep(config.refresh_interval)
                continue
            
            # 2. Check if refresh needed
            if should_refresh_quotes(current_price, LAST_QUOTE_PRICE, config.price_move_threshold):
                # 3. Cancel old orders
                if len(ACTIVE_BOT_ORDERS) > 0:
                    await cancel_all_bot_orders()
                
                # 4. Calculate new quotes
                bid, ask = calculate_quotes(current_price, config.spread_percentage)
                
                # 5. Place new orders
                try:
                    await place_mm_orders(bid, ask, config.order_size, config.market)
                    LAST_QUOTE_PRICE = current_price
                    print(f"✅ Bot quotes updated: {bid:.2f} / {ask:.2f} (price: {current_price:.2f})")
                except Exception as e:
                    print(f"❌ Failed to place orders: {e}")
            else:
                print(f"⏸️ No refresh needed (price: {current_price:.2f}, last: {LAST_QUOTE_PRICE:.2f})")
            
            # 6. Wait
            await asyncio.sleep(config.refresh_interval)
    
    except Exception as e:
        print(f"❌ Bot loop error: {e}")
        config.enabled = False
    finally:
        # Cleanup on stop
        await cancel_all_bot_orders()
        print("🛑 Market Making Bot stopped")


async def start_bot() -> Dict[str, Any]:
    """
    Start the market making bot
    """
    global bot_task
    
    if bot_task is not None and not bot_task.done():
        return {"status": "already_running", "config": config.__dict__}
    
    config.enabled = True
    bot_task = asyncio.create_task(bot_main_loop())
    
    return {
        "status": "started",
        "config": {
            "market": config.market,
            "spread_percentage": config.spread_percentage,
            "order_size": config.order_size,
            "refresh_interval": config.refresh_interval,
            "price_move_threshold": config.price_move_threshold
        }
    }


async def stop_bot() -> Dict[str, Any]:
    """
    Stop the market making bot
    """
    global bot_task
    
    config.enabled = False
    
    if bot_task is not None:
        await bot_task
        bot_task = None
    
    await cancel_all_bot_orders()
    
    return {"status": "stopped"}


def get_bot_status() -> Dict[str, Any]:
    """
    Get current bot status and statistics
    """
    return {
        "running": config.enabled,
        "config": {
            "market": config.market,
            "spread_percentage": config.spread_percentage,
            "order_size": config.order_size,
            "refresh_interval": config.refresh_interval,
            "price_move_threshold": config.price_move_threshold
        },
        "active_orders": len(ACTIVE_BOT_ORDERS),
        "last_quote_price": LAST_QUOTE_PRICE,
        "current_quotes": {
            "bid": LAST_QUOTE_PRICE * (1 - config.spread_percentage) if LAST_QUOTE_PRICE > 0 else 0,
            "ask": LAST_QUOTE_PRICE * (1 + config.spread_percentage) if LAST_QUOTE_PRICE > 0 else 0
        },
        "order_ids": list(ACTIVE_BOT_ORDERS.keys())
    }

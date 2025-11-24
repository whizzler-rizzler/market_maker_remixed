"""
Simple Market Making Bot
Automatically places and refreshes POST_ONLY bid/ask orders around market price
"""
import asyncio
from typing import Dict, Optional, Any
from .config import config
from bot.order_manager import get_order_manager
from bot.bot_logger import log_bot


# Global state
ACTIVE_BOT_ORDERS: Dict[str, Dict] = {}
LAST_QUOTE_PRICE: float = 0
bot_task: Optional[asyncio.Task] = None


def get_current_price(market: str) -> float:
    """
    Get current market price from broadcaster cache (uses live mark_price from balance data)
    """
    from backend.shared_state import BROADCASTER_CACHE
    
    
    log_bot(f"Searching price for {market} in cache", "DEBUG")
    
    # PRIORITY 1: Try to get from balance data (mark_prices dictionary) - most reliable and updated via WebSocket
    balance = BROADCASTER_CACHE.get("balance", {})
    if isinstance(balance, dict) and "data" in balance:
        balance_data = balance.get("data", {})
        mark_prices = balance_data.get("mark_prices", {}) or balance_data.get("markPrices", {})
        log_bot(f"Balance mark_prices available: {list(mark_prices.keys()) if mark_prices else 'None'}", "DEBUG")
        
        if market in mark_prices:
            price = float(mark_prices[market])
            log_bot(f"✅ Found LIVE price {price} in balance mark_prices for {market}", "INFO")
            return price
    
    # PRIORITY 2: Fallback to positions data (mark_price field) - may be stale
    positions = BROADCASTER_CACHE.get("positions", {})
    log_bot(f"Positions cache type: {type(positions)}, keys: {positions.keys() if isinstance(positions, dict) else 'N/A'}", "DEBUG")
    
    if isinstance(positions, dict) and "data" in positions:
        positions_data = positions.get("data", [])
        log_bot(f"Found {len(positions_data) if isinstance(positions_data, list) else 0} positions", "DEBUG")
        
        if isinstance(positions_data, list):
            for position in positions_data:
                if position.get("market") == market:
                    mark_price = position.get("mark_price") or position.get("markPrice")
                    if mark_price:
                        log_bot(f"⚠️ Using FALLBACK price {mark_price} from positions for {market}", "WARNING")
                        return float(mark_price)
    
    # Log cache structure for debugging
    log_bot(f"❌ Cache structure - positions: {type(positions)}, balance: {type(balance)}", "ERROR")
    log_bot(f"❌ Available markets in balance: {list(mark_prices.keys()) if mark_prices else 'None'}", "ERROR")
    raise ValueError(f"Could not find price for market {market} in broadcaster cache")


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
    
    # Place BUY order (order_manager.create_order is already async)
    buy_order = await order_manager.create_order(
        market=market,
        side="BUY",
        price=str(bid),
        size=size,
        time_in_force="POST_ONLY",
        reduce_only=False
    )
    
    # Place SELL order
    sell_order = await order_manager.create_order(
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
    
    log_bot(f"Orders placed: BUY @ {bid:.2f}, SELL @ {ask:.2f}", "INFO")
    
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
            await order_manager.cancel_order(order_id)
        except Exception as e:
            log_bot(f"Failed to cancel order {order_id}: {e}", "WARNING")
    
    count = len(ACTIVE_BOT_ORDERS)
    ACTIVE_BOT_ORDERS.clear()
    log_bot(f"Cancelled {count} bot orders", "INFO")


def should_refresh_quotes(current_price: float, last_price: float, threshold: float) -> bool:
    """
    Check if quotes should be refreshed based on price movement
    """
    if last_price == 0:
        return True
    
    price_change = abs(current_price - last_price) / last_price
    
    if price_change > threshold:
        log_bot(f"Price changed {price_change:.2%}, refreshing quotes", "INFO")
        return True
    
    return False


async def bot_main_loop():
    """
    Main bot loop - continuously monitors price and refreshes quotes
    """
    global LAST_QUOTE_PRICE, ACTIVE_BOT_ORDERS
    
    log_bot("Market Making Bot started", "INFO")
    
    try:
        while config.enabled:
            # 1. Get current price
            try:
                current_price = get_current_price(config.market)
            except Exception as e:
                log_bot(f"Failed to get price: {e}", "ERROR")
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
                    log_bot(f"Quotes updated: {bid:.2f} / {ask:.2f} (price: {current_price:.2f})", "INFO")
                except Exception as e:
                    log_bot(f"Failed to place orders: {e}", "ERROR")
            else:
                log_bot(f"No refresh needed (price: {current_price:.2f}, last: {LAST_QUOTE_PRICE:.2f})", "DEBUG")
            
            # 6. Wait
            await asyncio.sleep(config.refresh_interval)
    
    except Exception as e:
        log_bot(f"Bot loop error: {e}", "ERROR")
        config.enabled = False
    finally:
        # Cleanup on stop
        await cancel_all_bot_orders()
        log_bot("Market Making Bot stopped", "INFO")


async def start_bot() -> Dict[str, Any]:
    """
    Start the market making bot
    """
    global bot_task, LAST_QUOTE_PRICE, ACTIVE_BOT_ORDERS
    
    if bot_task is not None and not bot_task.done():
        return {"status": "already_running", "config": config.__dict__}
    
    # Reset state on start
    LAST_QUOTE_PRICE = 0
    ACTIVE_BOT_ORDERS.clear()
    
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

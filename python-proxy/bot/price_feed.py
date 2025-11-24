"""
Real-time Price Feed using Supabase WebSocket
Streams prices from Extended Exchange
"""
import asyncio
import json
from typing import Dict, Optional
import websockets


# Global price cache
PRICE_CACHE: Dict[str, float] = {}
PRICE_FEED_TASK: Optional[asyncio.Task] = None


async def price_feed_worker():
    """
    Background worker that maintains WebSocket connection
    and updates price cache
    """
    ws_url = "wss://ujtavgmgeefutsadbyzv.supabase.co/functions/v1/crypto-data-stream"
    
    while True:
        try:
            print("🔌 Connecting to price feed...")
            async with websockets.connect(ws_url) as websocket:
                print("✅ Connected to price feed")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        
                        # Extract data
                        exchange = data.get("exchange", "").lower()  # Lowercase for comparison
                        symbol = data.get("symbol")
                        price = data.get("price")
                        
                        # Filter for Extended exchange - CASE INSENSITIVE
                        if exchange == "extended" and symbol and price:
                            price_float = float(price)
                            PRICE_CACHE[symbol] = price_float
                            print(f"✅ Extended: {symbol} = ${price_float:,.2f}")
                        # Also cache Lighter and Paradex for fallback
                        elif exchange in ["lighter", "paradex"] and symbol and price:
                            PRICE_CACHE[symbol] = float(price)
                    
                    except json.JSONDecodeError:
                        print(f"⚠️ Failed to parse message: {message[:100]}")
                    except Exception as e:
                        print(f"⚠️ Error processing message: {e}")
        
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            print("🔄 Reconnecting in 3 seconds...")
            await asyncio.sleep(3)


def get_price(symbol: str) -> Optional[float]:
    """
    Get latest price from cache
    Handles both "BTC-USD" and "BTC" format
    """
    # Try full symbol first
    price = PRICE_CACHE.get(symbol)
    if price is not None:
        return price
    
    # Try base currency (before dash) - Extended exchange uses "BTC" not "BTC-USD"
    if "-" in symbol:
        base = symbol.split("-")[0]
        price = PRICE_CACHE.get(base)
        if price is not None:
            print(f"📊 Price for {symbol} found as {base}: ${price:,.2f}")
            return price
    
    return None


def start_price_feed():
    """Start price feed background task"""
    global PRICE_FEED_TASK
    
    if PRICE_FEED_TASK is None or PRICE_FEED_TASK.done():
        PRICE_FEED_TASK = asyncio.create_task(price_feed_worker())
        print("🚀 Price feed started")
    else:
        print("⚠️ Price feed already running")


def get_all_prices() -> Dict[str, float]:
    """Get all cached prices"""
    return PRICE_CACHE.copy()

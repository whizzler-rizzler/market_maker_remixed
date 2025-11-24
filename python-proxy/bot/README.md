# Market Making Bot

Automatyczny bot market makingowy dla Extended Exchange.

## Architektura

```
bot/
├── simple_mm_bot.py     # Główna logika bota
├── config.py            # Konfiguracja parametrów
├── order_manager.py     # Zarządzanie zleceniami Extended API
├── bot_logger.py        # System logowania
└── __init__.py
```

## Funkcjonalność

### 1. Automatyczne Market Making
- Umieszcza POST_ONLY zlecenia bid/ask wokół ceny rynkowej
- Automatycznie refreshuje zlecenia przy zmianie ceny
- Śledzi aktywne zlecenia bota
- Loguje wszystkie operacje

### 2. Zarządzanie Cenami
Bot używa **LIVE mark_price z balance data** (aktualizowane przez WebSocket):

```python
# PRIORITY 1: Balance mark_prices (LIVE from WebSocket)
balance_data.get("mark_prices", {})  # ✅ Najbardziej aktualne

# PRIORITY 2: Positions mark_price (Fallback - może być stare)
position.get("mark_price")  # ⚠️ Tylko jako fallback
```

**Dlaczego balance.mark_prices?**
- Aktualizowane 4x/sekundę przez broadcaster
- Zawiera ceny dla wszystkich rynków
- Zawsze świeże (< 250ms)

### 3. Parametry Konfiguracji (`config.py`)

```python
class BotConfig:
    market: str = "BTC-USD"              # Rynek do tradingu
    spread_percentage: float = 0.001     # 0.1% spread
    order_size: str = "0.01"             # Rozmiar zlecenia
    refresh_interval: int = 5            # Sekundy między checkamii
    price_move_threshold: float = 0.002  # 0.2% zmiana → refresh
    enabled: bool = False                # Status bota
```

## Używanie

### Start Bot
```bash
curl -X POST http://localhost:8000/api/bot/start
```

Response:
```json
{
  "status": "started",
  "config": {
    "market": "BTC-USD",
    "spread_percentage": 0.001,
    "order_size": "0.01",
    "refresh_interval": 5,
    "price_move_threshold": 0.002
  }
}
```

### Stop Bot
```bash
curl -X POST http://localhost:8000/api/bot/stop
```

### Get Status
```bash
curl http://localhost:8000/api/bot/status
```

Response:
```json
{
  "running": true,
  "config": {...},
  "active_orders": 2,
  "last_quote_price": 86198.85,
  "current_quotes": {
    "bid": 86112.65,
    "ask": 86285.05
  },
  "order_ids": ["order_1", "order_2"]
}
```

### Update Config (only when stopped)
```bash
curl -X POST http://localhost:8000/api/bot/config \
  -H "Content-Type: application/json" \
  -d '{
    "spread_percentage": 0.002,
    "order_size": "0.02"
  }'
```

### Get Logs
```bash
curl http://localhost:8000/api/bot/logs?limit=50
```

## Logika Bota

### Main Loop (`bot_main_loop()`)

```
1. Pobierz current price (LIVE mark_price z balance)
   ↓
2. Sprawdź czy refresh needed (price move > threshold)
   ↓
3. Jeśli TAK:
   a) Anuluj stare zlecenia
   b) Oblicz nowe quotes (bid/ask)
   c) Umieść nowe POST_ONLY zlecenia
   ↓
4. Sleep (refresh_interval)
   ↓
5. Repeat
```

### Quote Calculation

```python
# Market price: $86,198.85
# Spread: 0.1% (0.001)

bid_price = 86198.85 * (1 - 0.001) = $86,112.65
ask_price = 86198.85 * (1 + 0.001) = $86,285.05
```

### Refresh Trigger

Bot refreshuje zlecenia gdy:
```python
price_change = abs(current_price - last_price) / last_price
if price_change > price_move_threshold:
    refresh_orders()
```

## Order Manager

### Signing Flow
```python
1. Generate order hash (Pedersen hash chain)
2. Sign with Starknet private key (ECDSA)
3. Add signature to order
4. Submit to Extended API
```

### Order Types
- **POST_ONLY**: Adds liquidity (rests on book), earns maker fee
- **GTC**: Good Till Cancel
- **IOC**: Immediate or Cancel
- **FOK**: Fill or Kill

## Monitoring

### Bot Logs
```python
[BOT INFO] Market Making Bot started
[BOT INFO] ✅ Found LIVE price 86198.85 in balance mark_prices for BTC-USD
[BOT INFO] Quotes updated: 86112.65 / 86285.05 (price: 86198.85)
[BOT INFO] Orders placed: BUY @ 86112.65, SELL @ 86285.05
[BOT DEBUG] No refresh needed (price: 86198.85, last: 86198.85)
```

### Active Orders Tracking
Bot śledzi wszystkie aktywne zlecenia:
```python
ACTIVE_BOT_ORDERS = {
    "order_id_1": {"side": "BUY", "price": 86112.65, "size": "0.01"},
    "order_id_2": {"side": "SELL", "price": 86285.05, "size": "0.01"}
}
```

## Bezpieczeństwo

- Bot anuluje wszystkie zlecenia przy stop
- Wszystkie operacje są logowane
- Używa POST_ONLY (nie może wziąć liquidity)
- Konfiguracja tylko gdy bot stopped

## Troubleshooting

### "Could not find price for market"
- Sprawdź czy broadcaster działa (`/api/broadcaster/stats`)
- Sprawdź czy WebSocket jest connected
- Sprawdź czy market symbol jest poprawny

### Orders not placed
- Sprawdź logi bota (`/api/bot/logs`)
- Sprawdź Extended API credentials
- Sprawdź balance konta

### Bot keeps refreshing
- Zwiększ `price_move_threshold` (np. 0.005 = 0.5%)
- Zwiększ `refresh_interval` (np. 10 sekund)

## Development

### Test Price Fetching
```python
from bot.simple_mm_bot import get_current_price
price = get_current_price("BTC-USD")
print(f"Current price: ${price:.2f}")
```

### Test Quote Calculation
```python
from bot.simple_mm_bot import calculate_quotes
bid, ask = calculate_quotes(86198.85, 0.001)
print(f"Bid: ${bid:.2f}, Ask: ${ask:.2f}")
```

## Future Improvements

1. **Dynamic Spread**: Adjust spread based on volatility
2. **Inventory Management**: Skew quotes based on position
3. **Multiple Markets**: Run on multiple pairs simultaneously
4. **Risk Limits**: Max position size, max loss per day
5. **Partial Fills**: Handle partially filled orders
6. **Order Book Analysis**: Better quote placement based on book depth

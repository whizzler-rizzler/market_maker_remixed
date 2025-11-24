# Market Making Bot Architecture

## Overview

Bot market makingowy dla giełdy Extended oparty o Python (backend na Render) i React (frontend).

## Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend                          │
│  - OrderPanel (składanie zleceń)                           │
│  - Real-time monitoring (WebSocket + REST)                 │
│  - Position tracking (REST API - 4x/sekundę)              │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ HTTP/WebSocket
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Python Proxy (Render)                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Order Manager Module                                  │  │
│  │ - Starknet signature generation                       │  │
│  │ - Order creation (POST_ONLY, REDUCE_ONLY)            │  │
│  │ - Order cancellation                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Broadcaster Module                                    │  │
│  │ - Caching (positions, balance, trades)               │  │
│  │ - WebSocket broadcasting (real-time updates)         │  │
│  │ - Polling: 250ms (fast), 5s (trades)                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ HTTPS + Starknet signatures
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Extended API                                   │
│  - Private REST API (orders, positions, balance)           │
│  - Requires Starknet signatures                            │
└─────────────────────────────────────────────────────────────┘
```

## Komponenty

### 1. Order Manager (`order_manager.py`)

Moduł odpowiedzialny za składanie i zarządzanie zleceniami:

**Funkcje:**
- `generate_order_hash()` - Generuje hash zlecenia dla Starknet
- `sign_order()` - Podpisuje zlecenie kluczem prywatnym Starknet
- `create_order()` - Tworzy zlecenie na giełdzie Extended
- `get_open_orders()` - Pobiera otwarte zlecenia
- `cancel_order()` - Anuluje zlecenie

**Parametry zlecenia:**
- `market` - Para (np. "BTC-PERP")
- `side` - Strona (BUY/SELL)
- `price` - Cena
- `size` - Rozmiar
- `timeInForce` - POST_ONLY (market making), GTC, IOC, FOK
- `reduceOnly` - Czy tylko redukcja pozycji

### 2. Broadcaster Module (istniejący w `main.py`)

System real-time aktualizacji:
- Poluje dane co 250ms (positions + balance)
- Poluje trades co 5s
- Wykrywa zmiany i broadcastuje tylko różnice
- WebSocket endpoint: `/ws/broadcast`

### 3. Frontend Order Panel (`OrderPanel.tsx`)

Interfejs użytkownika do składania zleceń:
- Wybór rynku, strony (BUY/SELL)
- Ustawienie ceny i rozmiaru
- Wybór typu zlecenia (POST_ONLY, GTC, IOC, FOK)
- Opcja REDUCE_ONLY

## Flow Składania Zlecenia

```
1. User wypełnia formularz w OrderPanel
   ↓
2. Frontend wysyła POST /api/orders/create
   ↓
3. Order Manager:
   a) Generuje hash zlecenia (Pedersen hash)
   b) Podpisuje hash kluczem prywatnym Starknet
   c) Dodaje signature do zlecenia
   ↓
4. Wysyła podpisane zlecenie do Extended API
   ↓
5. Extended API:
   a) Weryfikuje sygnaturę
   b) Sprawdza balance i limity
   c) Umieszcza zlecenie w księdze
   ↓
6. Odpowiedź zwracana do frontendu
```

## Podpisywanie Starknet

Extended wymaga podpisów Starknet dla zleceń:

```python
# 1. Generuj hash zlecenia (Pedersen hash chain)
order_hash = pedersen_hash(public_key, market_id)
order_hash = pedersen_hash(order_hash, side)
order_hash = pedersen_hash(order_hash, price)
# ... więcej pól

# 2. Podpisz hash
signature = sign_calldata(order_hash, private_key)

# 3. Dodaj do zlecenia
order_params["signature"] = {
    "r": hex(signature[0]),
    "s": hex(signature[1])
}
```

## Typy Zleceń

### POST_ONLY (Market Making)
- Zlecenie dodaje płynność (rests on book)
- Jeśli wykonałoby się natychmiast → anulowane
- Idealne dla market makingu (zarabia maker fee)

### REDUCE_ONLY
- Może tylko zmniejszać pozycję
- Nie może otworzyć nowej pozycji
- Używane do bezpiecznego zamykania

### GTC (Good Till Cancel)
- Zlecenie aktywne aż do wykonania lub anulowania
- Może wykonać się natychmiast (jako taker)

### IOC (Immediate or Cancel)
- Wykonaj natychmiast lub anuluj
- Nie resta na księdze

### FOK (Fill or Kill)
- Wykonaj całość natychmiast lub anuluj całość

## Real-time Data Flow

### REST API (główne źródło - najszybsze)
```
Frontend ← (250ms polling) → Python Proxy ← (cache) → Extended API
```

- Poluje 4x/sekundę
- Cache z broadcaster (świeży < 250ms)
- Pozycje, balance, trades

### WebSocket (krytyczne fieldy)
```
Frontend ← (WebSocket) → Python Proxy ← (polling 250ms) → Extended API
```

- Broadcastuje tylko zmiany
- Wykrywa różnice w danych
- Minimalizuje traffic

## Konfiguracja

### Zmienne środowiskowe (Render)

```bash
# Extended API
EXTENDED_API_KEY=your_api_key
EXTENDED_API_BASE_URL=https://api.starknet.extended.exchange/api/v1

# Starknet credentials
Extended_2_D61658C_CLIENT_ID=your_client_id
Extended_2_D61658C_STARKNET_PUBLIC=0x...
Extended_2_D61658C_STARKNET_PRIVATE=0x...
Extended_2_D61658C_VAULT_NUMBER=1
```

### Frontend

```bash
VITE_PYTHON_PROXY_URL=https://your-service.onrender.com
```

## API Endpoints

### Order Management
- `POST /api/orders/create` - Utwórz zlecenie
- `GET /api/orders` - Pobierz otwarte zlecenia
- `DELETE /api/orders/{id}` - Anuluj zlecenie

### Account Data
- `GET /api/cached-account` - Cache account data
- `WS /ws/broadcast` - Real-time updates

## Testing

### 1. Test order creation
```bash
curl -X POST http://localhost:8000/api/orders/create \
  -H "Content-Type: application/json" \
  -d '{
    "market": "BTC-PERP",
    "side": "BUY",
    "price": "60000",
    "size": "0.001",
    "timeInForce": "POST_ONLY"
  }'
```

### 2. Check open orders
```bash
curl http://localhost:8000/api/orders
```

## Market Making Strategy (przykład)

```python
# Prosty market maker (przykład - do rozbudowy)
async def simple_market_maker():
    # 1. Pobierz current price
    market_price = await get_market_price("BTC-PERP")
    
    # 2. Oblicz spread (np. 0.1%)
    spread = 0.001
    buy_price = market_price * (1 - spread)
    sell_price = market_price * (1 + spread)
    
    # 3. Postaw zlecenia POST_ONLY
    await create_order(
        market="BTC-PERP",
        side="BUY",
        price=str(buy_price),
        size="0.001",
        timeInForce="POST_ONLY"
    )
    
    await create_order(
        market="BTC-PERP",
        side="SELL",
        price=str(sell_price),
        size="0.001",
        timeInForce="POST_ONLY"
    )
    
    # 4. Monitoruj fills i adjust
```

## Security

- Klucze prywatne Starknet tylko w środowisku Render
- Nigdy nie expose private keys w frontend
- Wszystkie requests podpisane
- Monitor activity logs

## Monitoring

### Logi
- Order creation attempts
- Signature generation
- API responses
- Errors

### Metrics
- Orders placed
- Fill rate
- PnL
- Position size

## Następne Kroki

1. ✅ **DONE:** Moduł tworzenia zleceń POST_ONLY
2. **TODO:** Automated market making logic
3. **TODO:** Risk management (position limits, stop loss)
4. **TODO:** Multiple market support
5. **TODO:** Dynamic spread adjustment
6. **TODO:** Inventory management

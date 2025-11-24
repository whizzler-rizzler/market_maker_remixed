# Extended API Proxy Service

Ten serwis działa jako pośrednik między aplikacją web a Extended API.

## Struktura Projektu

```
python-proxy/
├── backend/              # Backend FastAPI + Broadcaster
│   ├── main.py          # Główny serwer FastAPI
│   ├── shared_state.py  # Globalny cache broadcestera
│   ├── requirements.txt # Zależności Pythona
│   ├── runtime.txt      # Wersja Pythona dla Render
│   └── .env.example     # Przykładowa konfiguracja
│
├── bot/                 # Market Making Bot
│   ├── simple_mm_bot.py # Logika bota
│   ├── config.py        # Konfiguracja bota
│   ├── order_manager.py # Zarządzanie zleceniami Extended API
│   └── bot_logger.py    # System logowania bota
│
└── README.md            # Ten plik
```

## Instalacja

1. Zainstaluj zależności:
```bash
cd backend
pip install -r requirements.txt
```

2. Utwórz plik `.env` na podstawie `.env.example`:
```bash
cp .env.example .env
```

3. Dodaj swoje dane Extended API do pliku `.env`:
```
Extended_1_API_KEY=twoj_klucz_api
Extended_1_Stark_Key_Public=twoj_publiczny_klucz_starknet
Extended_1_Stark_Key_Private=twoj_prywatny_klucz_starknet
Extended_1_Client_Id=twoj_client_id
Extended_1_Vault_Number=twoj_vault_number
EXTENDED_API_BASE_URL=https://api.starknet.extended.exchange/api/v1
```

## Uruchomienie

### Lokalnie (development)
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Serwis będzie dostępny na: `http://localhost:8000`

### Produkcja (na Render)
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

## Endpointy API

### Broadcaster Endpoints
- `GET /health` - Health check
- `GET /api/cached-account` - Cached data (balance, positions, trades) - NO rate limits
- `GET /api/broadcaster/stats` - Broadcaster statistics
- `WS /ws/broadcast` - WebSocket real-time updates

### Order Management Endpoints
- `POST /api/orders/create` - Create new order (POST_ONLY support)
- `GET /api/orders` - Get open orders
- `DELETE /api/orders/{order_id}` - Cancel order

### Bot Endpoints
- `GET /api/bot/status` - Bot status and configuration
- `POST /api/bot/start` - Start market making bot
- `POST /api/bot/stop` - Stop market making bot
- `POST /api/bot/config` - Update bot configuration (only when stopped)
- `GET /api/bot/logs` - Get bot logs
- `DELETE /api/bot/logs` - Clear bot logs

### Legacy Endpoints (direct proxy)
- `GET /api/account/info` - Account information
- `GET /api/positions` - Current positions
- `GET /api/balance` - Account balance
- `GET /api/trades` - Trade history

## Testowanie

```bash
# Health check
curl http://localhost:8000/health

# Pobierz cached data (NO rate limits!)
curl http://localhost:8000/api/cached-account

# Broadcaster stats
curl http://localhost:8000/api/broadcaster/stats

# Bot status
curl http://localhost:8000/api/bot/status

# Start bot
curl -X POST http://localhost:8000/api/bot/start

# Bot logs
curl http://localhost:8000/api/bot/logs
```

## Deployment na Render

1. Połącz repozytorium z Render
2. Ustaw Build Command: `cd backend && pip install -r requirements.txt`
3. Ustaw Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000`
4. Dodaj zmienne środowiskowe z pliku `.env`
5. Deploy

## Architektura

### Broadcaster
- Automatyczne pollowanie Extended API (4x/s dla positions+balance, 1x/5s dla trades)
- WebSocket broadcasting zmian do wszystkich klientów
- Zero Extended API calls od frontendu - wszystko przez broadcaster cache

### Market Making Bot
- Automatyczne umieszczanie POST_ONLY zleceń bid/ask wokół ceny rynkowej
- Refresh zleceń przy zmianie ceny (threshold configurable)
- Śledzenie aktywnych zleceń bota
- Logowanie wszystkich operacji

### Order Manager
- Podpisywanie zleceń Starknet ECDSA
- Obsługa POST_ONLY, GTC, IOC, FOK
- Rate limiting i error handling

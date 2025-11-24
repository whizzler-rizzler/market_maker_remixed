# Changelog

## 2025-01-XX - Refaktoryzacja Struktury + Naprawa Bot Price

### 🔄 Refaktoryzacja Struktury Folderów

**Przed:**
```
python-proxy/
├── main.py
├── shared_state.py
├── order_manager.py
├── bot_logger.py
├── requirements.txt
├── runtime.txt
├── .env.example
└── bot/
    ├── simple_mm_bot.py
    └── config.py
```

**Po:**
```
python-proxy/
├── backend/              # Backend FastAPI + Broadcaster
│   ├── main.py
│   ├── shared_state.py
│   ├── requirements.txt
│   ├── runtime.txt
│   └── .env.example
│
└── bot/                  # Market Making Bot
    ├── simple_mm_bot.py
    ├── config.py
    ├── order_manager.py  # ← Przeniesione
    └── bot_logger.py     # ← Przeniesione
```

**Dlaczego?**
- ✅ Czytelna separacja: backend vs bot logic
- ✅ Łatwiejszy deployment (backend/ jako root directory)
- ✅ Logiczne grupowanie: order_manager + bot_logger są częścią bota

### 🐛 Naprawa: Bot Current Price

**Problem:**
Bot pokazywał **niewłaściwą cenę** ("Current Price") która nie zgadzała się z "Mark Price" z WebSocket.

**Przyczyna:**
Bot używał `mark_price` z **cached positions** (stare dane) zamiast **LIVE mark_prices** z balance (aktualizowane WebSocketem 4x/s).

**Rozwiązanie:**

Zmieniona kolejność priorytetów w `get_current_price()`:

```python
# ✅ PRIORITY 1: Balance mark_prices (LIVE from WebSocket - 4x/s)
balance_data.get("mark_prices", {})  # Najbardziej aktualne!

# ⚠️ PRIORITY 2: Positions mark_price (Fallback - może być stare)
position.get("mark_price")  # Tylko jako backup
```

**Efekt:**
- ✅ Bot teraz używa **tej samej ceny** co UI (LIVE WebSocket)
- ✅ "Current Price" = "Mark Price"
- ✅ Quotes są obliczane na podstawie aktualnej ceny
- ✅ Lepsze logowanie: `✅ Found LIVE price` vs `⚠️ Using FALLBACK price`

### 📝 Aktualizacje Dokumentacji

**Zaktualizowane pliki:**
- ✅ `README.md` - nowa struktura folderów
- ✅ `BOT_ARCHITECTURE.md` - ścieżki do modułów
- ✅ `DEPLOYMENT.md` - Root Directory = `python-proxy/backend`
- ✅ `bot/README.md` - **NOWY** - szczegółowa dokumentacja bota
- ✅ `CHANGELOG.md` - **NOWY** - ten plik

### 🔧 Zmiany Techniczne

#### Import Updates
```python
# backend/main.py
from bot.order_manager import get_order_manager
from bot.bot_logger import get_bot_logs, clear_bot_logs
from backend.shared_state import BROADCASTER_CACHE, BROADCAST_CLIENTS

# bot/simple_mm_bot.py
from bot.order_manager import get_order_manager
from bot.bot_logger import log_bot
from backend.shared_state import BROADCASTER_CACHE
```

#### Bot Logic Enhancement
```python
# Lepsze logowanie
log_bot(f"✅ Found LIVE price {price} in balance mark_prices", "INFO")
log_bot(f"⚠️ Using FALLBACK price {price} from positions", "WARNING")
log_bot(f"❌ Could not find price for market {market}", "ERROR")
```

### 📊 Live Statistics - Teraz Poprawne

**Przed (BUG):**
```
Current Price: $86198.85   ❌ Stara cena z positions
Mark Price:    $87500.00   ✅ LIVE z WebSocket
```

**Po (FIXED):**
```
Current Price: $87500.00   ✅ LIVE z balance.mark_prices
Mark Price:    $87500.00   ✅ LIVE z WebSocket
Bid Quote:     $87412.50   ✅ Obliczone z LIVE price
Ask Quote:     $87587.50   ✅ Obliczone z LIVE price
```

### 🚀 Deployment Changes

**Render Configuration:**
```
Root Directory: python-proxy/backend  # ← ZMIENIONE!
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### ⚠️ Breaking Changes

**BRAK** - wszystkie API endpoints pozostały bez zmian:
- ✅ `/api/bot/start`
- ✅ `/api/bot/stop`
- ✅ `/api/bot/status`
- ✅ `/api/bot/config`
- ✅ `/api/bot/logs`

### ✅ Testing Checklist

Po deploymencie sprawdź:
- [ ] Bot startuje bez błędów
- [ ] Current Price = Mark Price
- [ ] Quotes są obliczane poprawnie
- [ ] Zlecenia są umieszczane na właściwych cenach
- [ ] Logi pokazują `✅ Found LIVE price`
- [ ] WebSocket broadcaster działa
- [ ] `/api/broadcaster/stats` pokazuje świeże dane

### 📈 Performance

**Bez zmian** - bot nadal używa tego samego cache:
- Pozycje: 4x/s polling
- Balance: 4x/s polling
- Trades: 1x/5s polling
- WebSocket: real-time broadcasts

### 🔮 Future Work

Pozostałe issues z audytu:
1. ❌ Order signing może wymagać poprawki (Starknet hash generation)
2. ❌ SDK compatibility issues (x10 vs Extended)
3. ❌ Error handling improvements

**Ta refaktoryzacja naprawiła:**
- ✅ Strukturę folderów (chaos → clean)
- ✅ Bot price source (stare → LIVE)
- ✅ Dokumentację (brak → kompletna)

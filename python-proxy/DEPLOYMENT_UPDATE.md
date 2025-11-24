# 🚀 Deployment Update Required

## Problem

Twój backend na Render.com używa **starej wersji kodu** sprzed migracji na x10 SDK.

Bot pokazuje `"running": true` ale **NIE SKŁADA ORDERÓW** bo:
- Stary kod używa `starkware.crypto.signature` (nieprawidłowa biblioteka)
- x10 SDK nie jest zainstalowany
- OrderManager fail przy inicjalizacji

## Rozwiązanie

Musisz **zdeployować nową wersję** na Render z poprawnymi plikami.

---

## Opcja 1: Deploy przez GitHub (zalecane)

### Krok 1: Push nowy kod na GitHub

```bash
cd python-proxy
git add .
git commit -m "Migrate to x10 SDK for order signing"
git push origin main
```

### Krok 2: Trigger redeploy na Render

1. Idź do https://dashboard.render.com
2. Znajdź swój Python Backend service
3. Kliknij **"Manual Deploy"** → **"Deploy latest commit"**
4. Poczekaj ~2-3 min na build i deploy

---

## Opcja 2: Manual File Upload (jeśli nie używasz GitHub)

### Pliki które się zmieniły:

1. **`python-proxy/bot/order_manager.py`** - CAŁKOWICIE PRZEPISANY
   - Używa x10 SDK zamiast ręcznego signing
   - Automatyczne Starknet signing

2. **`python-proxy/backend/requirements.txt`** - ZMIENIONE
   ```txt
   fastapi==0.115.5
   uvicorn[standard]==0.32.1
   aiohttp==3.9.1
   python-dotenv==1.0.1
   websockets==11.0.3
   x10-python-trading-starknet>=0.0.11  # ← NOWA BIBLIOTEKA!
   ```

3. **`python-proxy/bot/SIGNING_GUIDE.md`** - USUNIĘTY (nieaktualna dokumentacja)

### Upload files do Render:

1. Zaloguj się do Render Dashboard
2. Otwórz swój Python service → **Shell**
3. Upload nowe pliki:

```bash
# Upload order_manager.py
cat > /opt/render/project/src/bot/order_manager.py << 'EOF'
[skopiuj całą zawartość nowego order_manager.py tutaj]
EOF

# Update requirements.txt
cat > /opt/render/project/src/backend/requirements.txt << 'EOF'
fastapi==0.115.5
uvicorn[standard]==0.32.1
aiohttp==3.9.1
python-dotenv==1.0.1
websockets==11.0.3
x10-python-trading-starknet>=0.0.11
EOF

# Reinstall dependencies
pip install -r /opt/render/project/src/backend/requirements.txt

# Restart service
supervisorctl restart all
```

---

## Weryfikacja że działa

Po deploy, sprawdź bot logs w UI:
- Powinny pojawić się logi:
  ```
  ✅ OrderManager initialized with x10 SDK
     Vault: [twój vault]
     Public Key: [pierwsze 10 znaków]
  ```

- Bot powinien składać ordery:
  ```
  📝 Creating POST_ONLY BUY order:
     Market: BTC-USD
     Price: 85400.0
     Size: 0.01
  🔐 SDK will automatically sign order...
  ✅ Order created successfully!
     Order ID: [order_id]
  ```

---

## Co zostało zmienione?

### ❌ Stary kod (NIEPRAWIDŁOWY):
```python
from starkware.crypto.signature.signature import sign, pedersen_hash
# Manual Pedersen hash chain
order_hash = pedersen_hash(market_id, side_int)
order_hash = pedersen_hash(order_hash, price_scaled)
# Manual signing
r, s = sign(msg_hash=order_hash, priv_key=private_key_int)
```

### ✅ Nowy kod (PRAWIDŁOWY):
```python
from x10.perpetual.accounts import StarkPerpetualAccount
from x10.perpetual.trading_client import PerpetualTradingClient

# SDK robi WSZYSTKO automatycznie!
order = await self.client.orders.place_order(
    market_name=market,
    side=order_side,
    order_type=sdk_order_type,
    size=size_decimal,
    price=price_decimal,
    expiration=expiration,
    reduce_only=reduce_only,
    post_only=post_only
)
```

---

## Environment Variables

**NIE MUSISZ ZMIENIAĆ** env variables na Render - SDK używa tych samych credentials:

```bash
Extended_1_API_KEY=...
Extended_1_Stark_Key_Public=...
Extended_1_Stark_Key_Private=...
Extended_1_Vault_Number=...
```

SDK automatycznie czyta te zmienne i używa do signing.

---

## FAQ

**Q: Czy muszę usunąć stare dependencies?**  
A: NIE. `pip install` automatycznie nadpisze starą wersję.

**Q: Czy muszę zmieniać .env?**  
A: NIE. x10 SDK używa tych samych env variables co stary kod.

**Q: Ile trwa deploy?**  
A: ~2-3 minuty jeśli używasz GitHub auto-deploy.

**Q: Co jeśli nadal nie działa?**  
A: Sprawdź Render logs:
1. Dashboard → Twój service → Logs
2. Szukaj błędów typu:
   - `ModuleNotFoundError: No module named 'x10'` (dependencies nie zainstalowane)
   - `ImportError` (błędne importy)
   - `ValueError: Missing Extended API credentials` (brak env variables)

---

## Pomoc

Jeśli masz problemy:
1. Sprawdź bot logs w UI (panel "Bot Logs (Backend)")
2. Sprawdź Render logs w Dashboard
3. Upewnij się że `requirements.txt` zawiera `x10-python-trading-starknet>=0.0.11`
4. Zrestartuj service: `supervisorctl restart all`

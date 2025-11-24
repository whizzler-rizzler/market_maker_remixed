# Deployment Guide - Extended Market Making Bot

## Prerequisites

1. Extended API credentials:
   - `EXTENDED_API_KEY` - Your API key
   - `Extended_2_D61658C_CLIENT_ID` - Client ID
   - `Extended_2_D61658C_STARKNET_PUBLIC` - Starknet public key
   - `Extended_2_D61658C_STARKNET_PRIVATE` - Starknet private key
   - `Extended_2_D61658C_VAULT_NUMBER` - Vault number

## Deployment to Render

### Step 1: Create a New Web Service

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" and select "Web Service"
3. Connect your repository

### Step 2: Configure Build Settings

```
Build Command: pip install -r python-proxy/requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Step 3: Environment Variables

Add all required environment variables in Render dashboard:

```
EXTENDED_API_KEY=your_api_key_here
EXTENDED_API_BASE_URL=https://api.starknet.extended.exchange/api/v1
Extended_2_D61658C_CLIENT_ID=your_client_id
Extended_2_D61658C_STARKNET_PUBLIC=your_starknet_public_key
Extended_2_D61658C_STARKNET_PRIVATE=your_starknet_private_key
Extended_2_D61658C_VAULT_NUMBER=your_vault_number
```

### Step 4: Deploy

1. Set Root Directory to `python-proxy`
2. Click "Create Web Service"
3. Wait for deployment to complete

## Testing the Deployment

### 1. Health Check

```bash
curl https://your-service.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-..."
}
```

### 2. Test Order Creation (POST ONLY)

```bash
curl -X POST https://your-service.onrender.com/api/orders/create \
  -H "Content-Type: application/json" \
  -d '{
    "market": "BTC-PERP",
    "side": "BUY",
    "price": "60000",
    "size": "0.001",
    "timeInForce": "POST_ONLY",
    "reduceOnly": false
  }'
```

### 3. Check Open Orders

```bash
curl https://your-service.onrender.com/api/orders
```

## API Endpoints

### Order Management

- `POST /api/orders/create` - Create new order (POST_ONLY supported)
- `GET /api/orders` - Get all open orders
- `GET /api/orders?market=BTC-PERP` - Get orders for specific market
- `DELETE /api/orders/{order_id}` - Cancel order by ID

### Account Data (Broadcaster)

- `GET /health` - Health check
- `GET /api/cached-account` - Get cached account data (fast)
- `GET /api/broadcaster/stats` - Get broadcaster statistics
- `WS /ws/broadcast` - WebSocket for real-time updates

### Legacy Endpoints

- `GET /api/account/info` - Account information
- `GET /api/positions` - Current positions
- `GET /api/balance` - Account balance
- `GET /api/trades` - Trade history

## Frontend Configuration

Update the frontend environment variable to point to your Render service:

```
VITE_PYTHON_PROXY_URL=https://your-service.onrender.com
```

## Market Making Strategy Notes

### POST ONLY Orders

POST_ONLY orders are designed for market making:
- Orders will ONLY execute if they add liquidity (rest on order book)
- If order would execute immediately (take liquidity), it's cancelled
- Ideal for market making strategies to earn maker fees

### REDUCE ONLY Orders

REDUCE_ONLY orders can only decrease your position:
- Cannot open new positions
- Cannot increase existing positions
- Used to exit positions safely

### Order Flow

1. Bot places POST_ONLY limit orders on both sides
2. Orders rest on the book, waiting for fills
3. When filled, bot earns maker rebate
4. Bot can use REDUCE_ONLY to exit positions

## Monitoring

### Logs

Monitor logs in Render dashboard to see:
- Order creation attempts
- Signature generation
- API responses
- WebSocket connections

### Broadcaster Stats

Check broadcaster stats endpoint:
```bash
curl https://your-service.onrender.com/api/broadcaster/stats
```

Shows:
- Cache age
- Last poll times
- Connected WebSocket clients
- Data freshness

## Troubleshooting

### "Missing credentials" error

Make sure all environment variables are set in Render dashboard.

### Order signature fails

Verify:
- Starknet private key is correct
- Public key matches private key
- Client ID is correct

### Orders rejected

Check:
- Market symbol is correct (e.g., "BTC-PERP")
- Price and size are valid
- Account has sufficient balance
- API key has trading permissions

## Security Notes

- Never expose Starknet private keys
- Keep API keys secure in environment variables
- Monitor bot activity regularly
- Set position limits to prevent over-trading

## Next Steps

1. Test order creation on testnet first
2. Start with small sizes
3. Monitor fills and fees
4. Adjust spread and size as needed
5. Implement automated market making logic

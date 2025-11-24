# 🚀 Backend Deployment Guide

## Render Configuration

### Step 1: Create Web Service
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your repository

### Step 2: Build Settings

**CRITICAL: Set Root Directory**
```
Root Directory: python-proxy/backend
```

**Build & Start Commands:**
```
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Step 3: Environment Variables

Add all Extended API credentials:

```bash
# Extended API
EXTENDED_API_KEY=your_api_key
EXTENDED_API_BASE_URL=https://api.starknet.extended.exchange/api/v1

# Starknet Credentials
Extended_1_API_KEY=your_api_key
Extended_1_Stark_Key_Public=0x...
Extended_1_Stark_Key_Private=0x...
Extended_1_Client_Id=your_client_id
Extended_1_Vault_Number=1
```

### Step 4: Deploy

Click "Create Web Service" and wait for deployment.

## Post-Deployment Verification

### 1. Health Check
```bash
curl https://your-service.onrender.com/health
```

Expected:
```json
{
  "status": "ok",
  "service": "extended-broadcaster-proxy",
  "bot_module_available": true
}
```

### 2. Broadcaster Stats
```bash
curl https://your-service.onrender.com/api/broadcaster/stats
```

### 3. Bot Status
```bash
curl https://your-service.onrender.com/api/bot/status
```

## Frontend Configuration

Update `.env` or environment variables:

```bash
VITE_PYTHON_PROXY_URL=https://your-service.onrender.com
```

## Troubleshooting

### "Module not found" errors
- Check Root Directory is set to `python-proxy/backend`
- Verify Build Command installs from correct requirements.txt

### Bot import errors
- Check if bot module exists: `python-proxy/bot/`
- Verify imports in `backend/main.py`

### Price issues
- Check broadcaster is running: `/api/broadcaster/stats`
- Verify WebSocket connection
- Check bot logs: `/api/bot/logs`

## Monitoring

### Logs
Check Render logs for:
- `✅ Bot module imported successfully`
- `✅ Extended API Key configured`
- `🚀 [Broadcaster] Background poller started`

### Broadcaster
```bash
curl https://your-service.onrender.com/api/broadcaster/stats
```

Should show:
- `connected_clients` > 0
- `cache` initialized
- Recent `last_poll` timestamps

### Bot
```bash
curl https://your-service.onrender.com/api/bot/logs
```

Should show:
- `✅ Found LIVE price` (not fallback)
- Bot operations
- Order placements

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { useBotStatus } from '@/hooks/useBotStatus';
import { usePublicPricesWebSocket } from '@/hooks/usePublicPricesWebSocket';
import { Play, Square, Settings, Wifi } from 'lucide-react';

export const BotControlPanel = () => {
  const { botStatus, isLoading, startBot, stopBot, updateConfig } = useBotStatus();
  const { prices: publicPrices, isConnected: wsConnected } = usePublicPricesWebSocket();
  const [liveMarkPrice, setLiveMarkPrice] = useState<number>(0);
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [configForm, setConfigForm] = useState({
    market: botStatus?.config.market || 'BTC-USD',
    spread_percentage: botStatus?.config.spread_percentage || 0.001,
    order_size: botStatus?.config.order_size || '0.01',
    refresh_interval: botStatus?.config.refresh_interval || 5,
    price_move_threshold: botStatus?.config.price_move_threshold || 0.002,
  });

  const handleStart = async () => {
    console.log('🚀 [BotControlPanel] Start button clicked!', {
      isRunning,
      isStarting,
      botStatus,
    });
    setIsStarting(true);
    try {
      console.log('📞 [BotControlPanel] Calling startBot()...');
      await startBot();
      console.log('✅ [BotControlPanel] startBot() completed');
    } catch (err) {
      console.error('❌ [BotControlPanel] startBot() failed:', err);
    } finally {
      setIsStarting(false);
    }
  };

  const handleStop = async () => {
    setIsStopping(true);
    try {
      await stopBot();
    } finally {
      setIsStopping(false);
    }
  };

  const handleSaveConfig = async () => {
    setIsSaving(true);
    try {
      await updateConfig({
        market: configForm.market,
        spread_percentage: Number(configForm.spread_percentage),
        order_size: configForm.order_size,
        refresh_interval: Number(configForm.refresh_interval),
        price_move_threshold: Number(configForm.price_move_threshold),
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Get LIVE mark price from WebSocket for the configured market
  useEffect(() => {
    if (!botStatus?.config.market) return;
    
    const marketBase = botStatus.config.market.split('-')[0]; // "BTC"
    const marketQuote = botStatus.config.market.split('-')[1]; // "USD"
    
    const possibleSymbols = [
      `${marketBase}${marketQuote}`, // "BTCUSD"
      `${marketBase}USDT`,           // "BTCUSDT"
      `${marketBase}USD`,            // "BTCUSD"
      marketBase,                    // "BTC"
    ];
    
    const publicPrice = Array.from(publicPrices.values()).find((price: any) =>
      possibleSymbols.includes(price.symbol)
    );
    
    if (publicPrice) {
      const wsPrice = parseFloat(publicPrice.price);
      setLiveMarkPrice(wsPrice);
      console.log(`✅ [BotControlPanel] LIVE WS price ${wsPrice} for ${botStatus.config.market} (${publicPrice.symbol})`);
    }
  }, [publicPrices, botStatus?.config.market]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>🤖 Market Making Bot</CardTitle>
          <CardDescription>Loading bot status...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const isRunning = botStatus?.running || false;
  const currentPrice = liveMarkPrice > 0 ? liveMarkPrice : (botStatus?.last_quote_price || 0);
  const spread = botStatus?.config.spread_percentage || 0.001;
  const bidPrice = currentPrice > 0 ? currentPrice * (1 - spread) : (botStatus?.current_quotes.bid || 0);
  const askPrice = currentPrice > 0 ? currentPrice * (1 + spread) : (botStatus?.current_quotes.ask || 0);
  const activeOrders = botStatus?.active_orders || 0;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {/* Control Panel */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                🤖 Market Making Bot
              </CardTitle>
              <CardDescription>Automated POST_ONLY market maker</CardDescription>
            </div>
            <Badge variant={isRunning ? "default" : "secondary"} className="text-xs">
              {isRunning ? "🟢 RUNNING" : "⚪ STOPPED"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Control Buttons */}
          <div className="flex gap-2">
            <Button
              onClick={handleStart}
              disabled={isRunning || isStarting}
              className="flex-1"
              variant="default"
            >
              <Play className="w-4 h-4 mr-2" />
              {isStarting ? 'Starting...' : 'Start Bot'}
            </Button>
            <Button
              onClick={handleStop}
              disabled={!isRunning || isStopping}
              className="flex-1"
              variant="destructive"
            >
              <Square className="w-4 h-4 mr-2" />
              {isStopping ? 'Stopping...' : 'Stop Bot'}
            </Button>
          </div>

          {/* Live Stats */}
          <div className="space-y-2 pt-4 border-t">
            <h4 className="text-sm font-semibold flex items-center gap-2">
              <Wifi className={`w-4 h-4 ${liveMarkPrice > 0 ? 'text-success animate-pulse' : 'text-muted-foreground'}`} />
              Live Statistics {liveMarkPrice > 0 ? '(WebSocket)' : '(Polling)'}
            </h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-muted-foreground flex items-center gap-1">
                  Current Price
                  {liveMarkPrice > 0 && (
                    <span className="text-xs text-success">🔴 LIVE</span>
                  )}
                </p>
                <p className="font-mono font-bold">
                  {currentPrice > 0 ? `$${currentPrice.toFixed(2)}` : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Active Orders</p>
                <p className="font-mono font-bold">{activeOrders}</p>
              </div>
              <div>
                <p className="text-muted-foreground flex items-center gap-1">
                  Bid Quote
                  {liveMarkPrice > 0 && (
                    <span className="text-xs text-success">🔴 LIVE</span>
                  )}
                </p>
                <p className="font-mono font-bold text-green-500">
                  {bidPrice > 0 ? `$${bidPrice.toFixed(2)}` : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground flex items-center gap-1">
                  Ask Quote
                  {liveMarkPrice > 0 && (
                    <span className="text-xs text-success">🔴 LIVE</span>
                  )}
                </p>
                <p className="font-mono font-bold text-red-500">
                  {askPrice > 0 ? `$${askPrice.toFixed(2)}` : 'N/A'}
                </p>
              </div>
            </div>
            {botStatus?.order_ids && botStatus.order_ids.length > 0 && (
              <div>
                <p className="text-muted-foreground text-xs">Order IDs:</p>
                <div className="flex flex-wrap gap-1 mt-1">
                  {botStatus.order_ids.map((id) => (
                    <Badge key={id} variant="outline" className="text-xs font-mono">
                      {id.slice(0, 8)}...
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Configuration Panel */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Bot Configuration
          </CardTitle>
          <CardDescription>
            Configure bot parameters (only when stopped)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="market">Market</Label>
            <Input
              id="market"
              value={configForm.market}
              onChange={(e) => setConfigForm({ ...configForm, market: e.target.value })}
              disabled={isRunning}
              placeholder="BTC-USD"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="spread">Spread (%)</Label>
            <Input
              id="spread"
              type="number"
              step="0.001"
              value={configForm.spread_percentage * 100}
              onChange={(e) =>
                setConfigForm({
                  ...configForm,
                  spread_percentage: Number(e.target.value) / 100,
                })
              }
              disabled={isRunning}
              placeholder="0.1"
            />
            <p className="text-xs text-muted-foreground">
              Distance from mark price (e.g., 0.1% = ±$60 on $60,000)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="size">Order Size</Label>
            <Input
              id="size"
              value={configForm.order_size}
              onChange={(e) => setConfigForm({ ...configForm, order_size: e.target.value })}
              disabled={isRunning}
              placeholder="0.01"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="refresh">Refresh (sec)</Label>
              <Input
                id="refresh"
                type="number"
                value={configForm.refresh_interval}
                onChange={(e) =>
                  setConfigForm({ ...configForm, refresh_interval: Number(e.target.value) })
                }
                disabled={isRunning}
                placeholder="5"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="threshold">Threshold (%)</Label>
              <Input
                id="threshold"
                type="number"
                step="0.001"
                value={configForm.price_move_threshold * 100}
                onChange={(e) =>
                  setConfigForm({
                    ...configForm,
                    price_move_threshold: Number(e.target.value) / 100,
                  })
                }
                disabled={isRunning}
                placeholder="0.2"
              />
            </div>
          </div>

          <Button
            onClick={handleSaveConfig}
            disabled={isRunning || isSaving}
            className="w-full"
            variant="outline"
          >
            {isSaving ? 'Saving...' : 'Save Configuration'}
          </Button>

          {isRunning && (
            <p className="text-xs text-muted-foreground text-center">
              Stop the bot to modify configuration
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

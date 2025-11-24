import { useState, useEffect } from "react";
import { Bot, Activity, RotateCcw, ArrowUpDown } from "lucide-react";
import { PortfolioStats } from "@/components/PortfolioStats";
import { AccountCard } from "@/components/AccountCard";
import { ExtendedDataPanel } from "@/components/ExtendedDataPanel";
import { RestAPIDebugPanel } from "@/components/RestAPIDebugPanel";
import { WebSocketDebugPanel } from "@/components/WebSocketDebugPanel";
import { FrequencyMonitor } from "@/components/FrequencyMonitor";
import { TradeHistory } from "@/components/TradeHistory";
import { OrderPanel } from "@/components/OrderPanel";
import { useExtendedWebSocket } from "@/hooks/useExtendedWebSocket";
import { useAccountRestAPI } from "@/hooks/useAccountRestAPI";
import { usePublicPricesWebSocket } from "@/hooks/usePublicPricesWebSocket";
import { useTradeHistory } from "@/hooks/useTradeHistory";
import { useBroadcasterStats } from "@/hooks/useBroadcasterStats";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";

const Index = () => {
  // Layer 1: REST API data (main source - fastest)
  const restAccountData = useAccountRestAPI();
  
  // Layer 2: WebSocket for critical real-time updates
  const { isConnected, extendedData, error } = useExtendedWebSocket();
  
  // Layer 3: Public prices WebSocket for mark prices
  const { prices: publicPrices } = usePublicPricesWebSocket();
  
  // Layer 4: Trade history
  const tradeHistory = useTradeHistory();
  
  // Broadcaster stats for monitoring
  const broadcasterStats = useBroadcasterStats();
  
  const [portfolioData, setPortfolioData] = useState({
    totalPnl: 0.00,
    realizedPnl: 0.00,
    totalNotional: 0,
    activePositions: 0,
    leverage: 0.00,
    collateral: 0,
    equity: 0,
    availableBalance: 0,
    marginRatio: 0,
    exposure: 0,
    volume: 0,
    volume24h: 0,
    volume7d: 0,
    longPositions: 0,
    longPnl: 0.00,
    longNotional: 0,
    shortPositions: 0,
    shortPnl: 0.00,
    shortNotional: 0,
  });

  const [accounts, setAccounts] = useState([
    {
      name: "Loading...",
      address: "...",
      balance: 0,
      equity: 0,
      pnl: 0.00,
      notional: 0.00,
      positions: 0,
      marginRatio: 0,
      vol24h: 0,
      vol7d: 0,
      volTotal: 0,
      ath: 0.00,
      atl: 0.00,
      positionDetails: [] as any[],
    },
  ]);

  // Store all positions by market as a Map to accumulate them
  const [allPositions, setAllPositions] = useState<Map<string, any>>(new Map());
  const [sortBy, setSortBy] = useState<'pnl' | 'size' | 'time'>('pnl');
  const [lastWsUpdate, setLastWsUpdate] = useState<Date | null>(null);

  const [lastUpdate, setLastUpdate] = useState(new Date().toLocaleTimeString('pl-PL'));
  const { toast } = useToast();

  // Process REST API data (main data source - fastest)
  useEffect(() => {
    if (!restAccountData.balance && restAccountData.positions.length === 0) return;

    console.log('🔄 [Index] REST API data updated:', restAccountData);
    setLastUpdate(new Date().toLocaleTimeString('pl-PL'));

    // Process account data from REST API
    if (restAccountData.balance) {
      const bal = restAccountData.balance;
      
      setPortfolioData(prev => ({
        ...prev,
        totalPnl: parseFloat(bal.unrealisedPnl || '0'),
        realizedPnl: 0, // Will be calculated from positions
        collateral: parseFloat(bal.balance || '0'),
        equity: parseFloat(bal.equity || '0'),
        availableBalance: parseFloat(bal.availableForTrade || '0'),
        marginRatio: parseFloat(bal.marginRatio || '0'),
        leverage: parseFloat(bal.leverage || '0'),
        exposure: parseFloat(bal.exposure || '0'),
      }));

      setAccounts(prev => [{
        ...prev[0],
        name: 'Main account',
        balance: parseFloat(bal.balance || '0'),
        equity: parseFloat(bal.equity || '0'),
        pnl: parseFloat(bal.unrealisedPnl || '0'),
        marginRatio: parseFloat(bal.marginRatio || '0'),
      }]);
    }

    // Process positions from REST API - ALWAYS update map (even if empty)
    const positions = restAccountData.positions;
    
    // Update allPositions Map with data from REST API
    setAllPositions(prev => {
      const updated = new Map(prev);
      
      if (positions.length === 0) {
        // No positions - clear the entire map
        if (updated.size > 0) {
          console.log('🗑️ [Index] No positions returned - clearing all');
          updated.clear();
        }
      } else {
        // Has positions - update map
        positions.forEach((pos: any) => {
          if (pos.status === 'OPENED') {
            // WYŁĄCZNIE cena z publicznego WebSocketu - NIE używaj REST API
            const marketBase = pos.market.split('-')[0]; // "BTC"
            const marketQuote = pos.market.split('-')[1]; // "USD"

            const possibleSymbols = [
              `${marketBase}${marketQuote}`, // "BTCUSD"
              `${marketBase}USDT`,           // "BTCUSDT"
              `${marketBase}USD`,            // "BTCUSD"
              marketBase,                    // "BTC"
            ];

            const publicPrice = Array.from(publicPrices.values()).find((price: any) =>
              possibleSymbols.includes(price.symbol)
            );

            let latestMarkPrice = 0;
            
            if (publicPrice) {
              latestMarkPrice = parseFloat(publicPrice.price);
              console.log(`✅ [Index] Using PUBLIC WS price ${latestMarkPrice} for ${pos.market} (${publicPrice.symbol} @ ${publicPrice.exchange})`);
            } else {
              // Zachowaj poprzednią wartość z mapy jeśli istnieje
              const existingPosition = updated.get(pos.market);
              if (existingPosition && existingPosition.markPrice > 0) {
                latestMarkPrice = existingPosition.markPrice;
                console.log(`🔄 [Index] No fresh WS price for ${pos.market}, keeping previous: ${latestMarkPrice}`);
              } else {
                console.warn(`❌ [Index] NO PUBLIC WS PRICE for ${pos.market} - markPrice will be 0! Available symbols:`, Array.from(publicPrices.keys()));
              }
            }
            
            const positionData = {
              market: pos.market,
              side: pos.side,
              leverage: pos.leverage,
              size: pos.size,
              value: pos.value,
              openPrice: parseFloat(pos.openPrice || '0'),
              markPrice: latestMarkPrice,
              liquidationPrice: parseFloat(pos.liquidationPrice || '0'),
              unrealisedPnl: parseFloat(pos.midPriceUnrealisedPnl || '0'),
              realisedPnl: parseFloat(pos.realisedPnl || '0'),
              margin: parseFloat(pos.margin || '0'),
              status: pos.status,
              createdAt: pos.createdAt,
              updatedAt: pos.updatedAt,
            };
            
            updated.set(pos.market, positionData);
          }
        });
      }
      
      console.log('🗺️ [Index] All positions map updated, open positions:', updated.size);
      
      // Calculate stats from updated map
      const allPositionsArray = Array.from(updated.values());
      
      const totalNotional = allPositionsArray.reduce((sum: number, pos: any) => 
        sum + parseFloat(pos.value || 0), 0
      );
      
      const longPositions = allPositionsArray.filter((p: any) => p.side === 'LONG');
      const shortPositions = allPositionsArray.filter((p: any) => p.side === 'SHORT');
      
      const longPnl = longPositions.reduce((sum: number, pos: any) => 
        sum + parseFloat(pos.unrealisedPnl || 0), 0
      );
      
      const longNotional = longPositions.reduce((sum: number, pos: any) => 
        sum + parseFloat(pos.value || 0), 0
      );
      
      const shortPnl = shortPositions.reduce((sum: number, pos: any) => 
        sum + parseFloat(pos.unrealisedPnl || 0), 0
      );
      
      const shortNotional = shortPositions.reduce((sum: number, pos: any) => 
        sum + parseFloat(pos.value || 0), 0
      );

      const realizedPnl = allPositionsArray.reduce((sum: number, pos: any) => 
        sum + parseFloat(pos.realisedPnl || 0), 0
      );

      const volume = allPositionsArray.reduce((sum: number, pos: any) => 
        sum + Math.abs(parseFloat(pos.value || 0)), 0
      );

      setPortfolioData(prev => ({
        ...prev,
        totalNotional,
        activePositions: allPositionsArray.length,
        realizedPnl,
        volume,
        volume24h: 0,
        volume7d: 0,
        longPositions: longPositions.length,
        longPnl,
        longNotional,
        shortPositions: shortPositions.length,
        shortPnl,
        shortNotional,
        totalPnl: longPnl + shortPnl,
      }));

      setAccounts(prev => [{
        ...prev[0],
        notional: totalNotional,
        positions: allPositionsArray.length,
        positionDetails: allPositionsArray,
        pnl: longPnl + shortPnl,
      }]);

      return updated;
    });
  }, [restAccountData, publicPrices]);

  // Process WebSocket data (only for critical fields detection)
  useEffect(() => {
    if (!extendedData.balance) return;

    console.log('⚡ [Index] WebSocket critical fields updated:', extendedData.balance);
    setLastWsUpdate(new Date());

    // Update only the 4 critical fields from WebSocket
    const bal = extendedData.balance;
    
    setPortfolioData(prev => ({
      ...prev,
      marginRatio: bal.marginRatio ? parseFloat(bal.marginRatio) : prev.marginRatio,
      equity: bal.equity ? parseFloat(bal.equity) : prev.equity,
      availableBalance: bal.availableForTrade ? parseFloat(bal.availableForTrade) : prev.availableBalance,
    }));

    setAccounts(prev => [{
      ...prev[0],
      equity: bal.equity ? parseFloat(bal.equity) : prev[0].equity,
      marginRatio: bal.marginRatio ? parseFloat(bal.marginRatio) : prev[0].marginRatio,
    }]);
  }, [extendedData]);

  // Sort positions based on selected criteria
  const sortedPositions = (positions: any[]) => {
    const sorted = [...positions];
    switch (sortBy) {
      case 'pnl':
        return sorted.sort((a, b) => b.unrealisedPnl - a.unrealisedPnl);
      case 'size':
        return sorted.sort((a, b) => parseFloat(b.value || 0) - parseFloat(a.value || 0));
      case 'time':
        return sorted.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
      default:
        return sorted;
    }
  };

  const handleResetPositions = () => {
    setAllPositions(new Map());
    toast({
      title: "Pozycje zresetowane",
      description: "Mapa pozycji została wyczyszczona",
    });
  };

  const handleSortChange = () => {
    const sortOptions: ('pnl' | 'size' | 'time')[] = ['pnl', 'size', 'time'];
    const currentIndex = sortOptions.indexOf(sortBy);
    const nextSort = sortOptions[(currentIndex + 1) % sortOptions.length];
    setSortBy(nextSort);
    toast({
      title: "Sortowanie zmienione",
      description: `Sortowanie według: ${nextSort === 'pnl' ? 'PnL' : nextSort === 'size' ? 'Rozmiaru' : 'Czasu aktualizacji'}`,
    });
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-primary/10 border border-primary/20">
              <Bot className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-primary">
                Bot Control Panel - Real-Time
              </h1>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <div className="flex items-center gap-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success animate-pulse' : 'bg-destructive'}`} />
              <span className="text-muted-foreground">
                {isConnected ? '✅ WebSocket Connected (Extended)' : '❌ WebSocket Disconnected'}
              </span>
            </div>
            <div className="text-xs text-muted-foreground">
              Last update: {lastUpdate}
            </div>
            {error && (
              <div className="text-xs text-destructive font-mono">{error}</div>
            )}
          </div>
        </div>

        {/* Frequency Monitor */}
        <FrequencyMonitor 
          broadcasterStats={broadcasterStats.stats}
          lastWsUpdate={lastWsUpdate}
          isWsConnected={isConnected}
        />

        {/* Market Making Bot Order Panel */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-1 h-6 bg-primary rounded-full" />
            <h2 className="text-xl font-bold text-primary">MARKET MAKING BOT</h2>
          </div>
          <OrderPanel />
        </div>

        {/* Overview Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-1 h-6 bg-primary rounded-full" />
            <h2 className="text-xl font-bold text-primary">OVERVIEW - PORTFOLIO</h2>
          </div>
          <PortfolioStats data={portfolioData} />
        </div>

        {/* Accounts Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-1 h-6 bg-primary rounded-full" />
              <h2 className="text-xl font-bold text-primary">EXTENDED</h2>
            </div>
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleSortChange}
                className="gap-2"
              >
                <ArrowUpDown className="w-4 h-4" />
                Sort: {sortBy === 'pnl' ? 'PnL' : sortBy === 'size' ? 'Size' : 'Time'}
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleResetPositions}
                className="gap-2"
              >
                <RotateCcw className="w-4 h-4" />
                Reset Positions
              </Button>
            </div>
          </div>
          <div className="space-y-4">
            {accounts.map((account, index) => (
              <AccountCard 
                key={index} 
                account={{
                  ...account,
                  positionDetails: sortedPositions(account.positionDetails || [])
                }} 
              />
            ))}
            <TradeHistory trades={tradeHistory.trades} />
          </div>
        </div>

        {/* Debug Panels */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-1 h-6 bg-destructive rounded-full" />
            <h2 className="text-xl font-bold text-destructive">DEBUG PANELS</h2>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RestAPIDebugPanel />
            <WebSocketDebugPanel />
          </div>
        </div>


        {/* Real-time indicator */}
        <div className="mt-8 text-center p-4 bg-primary/10 rounded-lg border border-primary/20">
          <p className="text-lg font-semibold text-primary flex items-center justify-center gap-2">
            <Activity className={`w-5 h-5 ${isConnected ? 'animate-pulse' : ''}`} />
            🔴 LIVE • WebSocket Stream
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time WebSocket connection to Extended API
          </p>
        </div>
      </div>
    </div>
  );
};

export default Index;

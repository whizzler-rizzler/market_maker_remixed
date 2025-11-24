import { Card } from "@/components/ui/card";
import { Activity, Wifi, Users, Clock } from "lucide-react";
import { useEffect, useState } from "react";

interface BroadcasterStats {
  broadcaster?: {
    connected_clients: number;
  };
  cache?: {
    positions_age_seconds: number;
    balance_age_seconds: number;
    trades_age_seconds: number;
  };
  last_poll?: {
    positions: number;
    balance: number;
    trades: number;
  };
}

interface FrequencyMonitorProps {
  broadcasterStats: BroadcasterStats | null;
  lastWsUpdate: Date | null;
  isWsConnected: boolean;
}

export const FrequencyMonitor = ({ broadcasterStats, lastWsUpdate, isWsConnected }: FrequencyMonitorProps) => {
  const [wsFrequency, setWsFrequency] = useState<number[]>([]);
  const [lastWsTime, setLastWsTime] = useState<Date | null>(null);

  useEffect(() => {
    if (lastWsUpdate && lastWsTime) {
      const diff = lastWsUpdate.getTime() - lastWsTime.getTime();
      setWsFrequency(prev => [...prev.slice(-9), diff]);
    }
    if (lastWsUpdate) {
      setLastWsTime(lastWsUpdate);
    }
  }, [lastWsUpdate]);

  const avgWs = wsFrequency.length > 0 
    ? Math.round(wsFrequency.reduce((a, b) => a + b, 0) / wsFrequency.length)
    : 0;

  const connectedClients = broadcasterStats?.broadcaster?.connected_clients ?? 0;
  const cacheAgePositions = broadcasterStats?.cache?.positions_age_seconds ?? 0;
  const cacheAgeBalance = broadcasterStats?.cache?.balance_age_seconds ?? 0;
  const cacheAgeTrades = broadcasterStats?.cache?.trades_age_seconds ?? 0;
  const lastPollPositions = broadcasterStats?.last_poll?.positions;
  const lastPollTrades = broadcasterStats?.last_poll?.trades;

  return (
    <Card className="p-6 border-border/50 bg-card/50 backdrop-blur-sm">
      <div className="space-y-4">
        <h3 className="text-lg font-bold text-primary">📊 BROADCASTER MONITOR</h3>
        
        <div className="grid grid-cols-4 gap-4">
          {/* Broadcaster Fast Data Polling */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Activity className="w-4 h-4 text-primary animate-pulse" />
              <span>Extended API</span>
            </div>
            <div className="text-2xl font-mono font-bold text-primary">
              4 req/s
            </div>
            <div className="text-xs text-muted-foreground">
              Positions + Balance
            </div>
            <div className="text-xs font-mono text-muted-foreground">
              {lastPollPositions 
                ? new Date(lastPollPositions * 1000).toLocaleTimeString('pl-PL', { 
                    hour12: false, 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit'
                  })
                : 'N/A'
              }
            </div>
          </div>

          {/* Broadcaster Trades Polling */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="w-4 h-4 text-primary/70" />
              <span>Trades API</span>
            </div>
            <div className="text-2xl font-mono font-bold text-primary/70">
              1x/5s
            </div>
            <div className="text-xs text-muted-foreground">
              Trade history
            </div>
            <div className="text-xs font-mono text-muted-foreground">
              {lastPollTrades 
                ? new Date(lastPollTrades * 1000).toLocaleTimeString('pl-PL', { 
                    hour12: false, 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit'
                  })
                : 'N/A'
              }
            </div>
          </div>

          {/* WebSocket Broadcast */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Wifi className={`w-4 h-4 ${isWsConnected ? 'text-success animate-pulse' : 'text-destructive'}`} />
              <span>WebSocket</span>
            </div>
            <div className="text-2xl font-mono font-bold text-success">
              {avgWs > 0 ? `${avgWs}ms` : '---'}
            </div>
            <div className="text-xs text-muted-foreground">
              Event-driven
            </div>
            <div className="text-xs font-mono text-muted-foreground">
              Last: {lastWsUpdate 
                ? lastWsUpdate.toLocaleTimeString('pl-PL', { 
                    hour12: false, 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit'
                  }) + '.' + lastWsUpdate.getMilliseconds().toString().padStart(3, '0')
                : 'No events'
              }
            </div>
          </div>

          {/* Connected Clients */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Users className="w-4 h-4 text-success" />
              <span>WS Clients</span>
            </div>
            <div className="text-2xl font-mono font-bold text-success">
              {connectedClients}
            </div>
            <div className="text-xs text-muted-foreground">
              Connected
            </div>
          </div>
        </div>

        {/* Cache Age Indicators */}
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-border/50">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Positions cache:</div>
            <div className="text-sm font-mono text-primary">
              {cacheAgePositions > 0 ? `${cacheAgePositions}s ago` : 'N/A'}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Balance cache:</div>
            <div className="text-sm font-mono text-primary">
              {cacheAgeBalance > 0 ? `${cacheAgeBalance}s ago` : 'N/A'}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Trades cache:</div>
            <div className="text-sm font-mono text-primary">
              {cacheAgeTrades > 0 ? `${cacheAgeTrades}s ago` : 'N/A'}
            </div>
          </div>
        </div>

        {/* WS History bars */}
        <div className="space-y-1">
          <div className="text-xs text-muted-foreground">WS broadcast intervals (last 10):</div>
          <div className="flex gap-1 h-8 items-end">
            {wsFrequency.map((val, i) => (
              <div 
                key={i} 
                className="flex-1 bg-success/50 rounded-sm"
                style={{ height: `${Math.min((val / 5000) * 100, 100)}%` }}
                title={`${val}ms`}
              />
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
};

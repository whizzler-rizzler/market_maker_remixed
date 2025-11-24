import { useEffect, useState, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';

interface RawEvent {
  timestamp: string;
  rawData: string;
}

export const WebSocketDebugPanel = () => {
  const [events, setEvents] = useState<RawEvent[]>([]);
  const [eventCount, setEventCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const maxEvents = 100; // Keep last 100 events

  useEffect(() => {
    const PYTHON_PROXY_URL = import.meta.env.VITE_PYTHON_PROXY_URL || 'https://extended-account-stream.onrender.com';
    const wsUrl = PYTHON_PROXY_URL.replace(/^https/, 'wss').replace(/^http/, 'ws') + '/ws/account';
    
    console.log('🔍 Debug panel connecting to:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('🔍 Debug WebSocket connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const now = new Date();
      const timestamp = `${now.toLocaleTimeString('pl-PL')}:${now.getMilliseconds().toString().padStart(3, '0')}`;
      
      setEventCount(prev => prev + 1);
      
      setEvents(prev => {
        const newEvents = [{
          timestamp,
          rawData: event.data
        }, ...prev];
        
        return newEvents.slice(0, maxEvents);
      });
    };

    ws.onerror = (error) => {
      console.error('🔍 Debug WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('🔍 Debug WebSocket disconnected');
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <Card className="bg-black border-destructive/50 p-4">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-destructive">🔍 RAW WEBSOCKET DEBUG</h3>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success animate-pulse' : 'bg-destructive'}`} />
              <span className="text-muted-foreground">{isConnected ? 'Połączono' : 'Rozłączono'}</span>
            </div>
            <div className="text-primary font-mono">
              Łącznie eventów: {eventCount}
            </div>
          </div>
        </div>

        <ScrollArea className="h-[600px] rounded-md border border-destructive/30 bg-black/50 p-4">
          <div className="space-y-2 font-mono text-xs">
            {events.length === 0 ? (
              <div className="text-muted-foreground text-center py-8">
                Oczekiwanie na dane WebSocket...
              </div>
            ) : (
              events.map((event, index) => (
                <div 
                  key={index} 
                  className="border border-primary/20 rounded p-3 bg-primary/5 hover:bg-primary/10 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2 pb-2 border-b border-primary/20">
                    <span className="text-destructive font-bold">#{eventCount - index}</span>
                    <span className="text-success">{event.timestamp}</span>
                  </div>
                  <pre className="text-foreground whitespace-pre-wrap break-all">
                    {event.rawData}
                  </pre>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>
    </Card>
  );
};

import { useState, useEffect, useRef } from 'react';
import { getWebSocketUrl } from '@/lib/config';

interface BotLog {
  timestamp: string;
  level: string;
  message: string;
}

export const useBotLogs = () => {
  const [logs, setLogs] = useState<BotLog[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to live log streaming WebSocket
    const wsUrl = `${getWebSocketUrl('https://market-maker-remixed.onrender.com')}/ws/bot-logs`;
    console.log('🔌 [Bot Logs WS] Connecting to:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('✅ [Bot Logs WS] Connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'snapshot') {
          // Initial snapshot - replace all logs
          console.log(`📸 [Bot Logs WS] Received snapshot with ${data.logs.length} logs`);
          setLogs(data.logs);
        } else if (data.type === 'new_logs') {
          // New logs - prepend to existing (newest first)
          console.log(`📝 [Bot Logs WS] Received ${data.logs.length} new logs`);
          setLogs(prev => [...data.logs, ...prev].slice(0, 100)); // Keep max 100
        }
      } catch (err) {
        console.error('❌ [Bot Logs WS] Parse error:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('❌ [Bot Logs WS] Error:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('👋 [Bot Logs WS] Disconnected');
      setIsConnected(false);
    };

    return () => {
      console.log('🔌 [Bot Logs WS] Cleaning up connection');
      ws.close();
    };
  }, []);

  return { logs, isConnected };
};

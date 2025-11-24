import { useState, useEffect, useRef } from 'react';

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

interface BroadcasterStatsData {
  stats: BroadcasterStats | null;
  lastUpdate: Date;
  error: string | null;
}

const API_URL = 'https://extended-account-stream.onrender.com/api/broadcaster/stats';
const POLL_INTERVAL = 2000; // 2 seconds

export const useBroadcasterStats = () => {
  const [data, setData] = useState<BroadcasterStatsData>({
    stats: null,
    lastUpdate: new Date(),
    error: null,
  });
  const intervalRef = useRef<NodeJS.Timeout>();

  const fetchStats = async () => {
    try {
      const response = await fetch(API_URL);
      const result = await response.json();
      
      setData({
        stats: result,
        lastUpdate: new Date(),
        error: null,
      });
    } catch (error) {
      console.error('❌ [useBroadcasterStats] Error fetching broadcaster stats:', error);
      setData(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Unknown error',
      }));
    }
  };

  useEffect(() => {
    fetchStats();
    
    intervalRef.current = setInterval(fetchStats, POLL_INTERVAL);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return data;
};

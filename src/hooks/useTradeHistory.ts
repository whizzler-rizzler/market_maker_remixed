import { useState, useEffect, useRef } from 'react';
import { API_ENDPOINTS } from '@/lib/config';

interface Trade {
  id: string;
  accountId: number;
  market: string;
  orderId: string;
  side: string;
  price: string;
  qty: string;
  value: string;
  fee: string;
  tradeType: string;
  createdTime: number;
  isTaker: boolean;
}

interface TradeHistoryData {
  trades: Trade[];
  lastUpdate: Date;
}

const POLL_INTERVAL = 5000; // 5 seconds

export const useTradeHistory = () => {
  const [data, setData] = useState<TradeHistoryData>({
    trades: [],
    lastUpdate: new Date(),
  });
  const intervalRef = useRef<NodeJS.Timeout>();

  const fetchTradeHistory = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.cachedAccount);
      const result = await response.json();
      
      console.log('📜 [useTradeHistory] Cached response:', result);
      
      // Cached account returns trades nested in {status, data} structure
      const trades = result.trades?.data || [];
      
      setData({
        trades: trades,
        lastUpdate: new Date(),
      });
      console.log('✅ [useTradeHistory] Updated with', trades.length, 'trades from cache');
    } catch (error) {
      console.error('❌ [useTradeHistory] Error fetching trade history:', error);
    }
  };

  useEffect(() => {
    fetchTradeHistory();
    
    intervalRef.current = setInterval(fetchTradeHistory, POLL_INTERVAL);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return data;
};

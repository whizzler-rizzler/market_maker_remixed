import { useState, useEffect, useRef } from 'react';
import { API_ENDPOINTS } from '@/lib/config';

interface Order {
  id: string;
  accountId: number;
  market: string;
  side: string;
  price: string;
  size: string;
  orderType: string;
  status: string;
  createdTime: number;
  updatedTime: number;
  filledSize?: string;
  timeInForce?: string;
}

interface OpenOrdersData {
  orders: Order[];
  lastUpdate: Date;
}

const POLL_INTERVAL = 500; // 0.5 seconds = 2x per second

export const useOpenOrders = () => {
  const [data, setData] = useState<OpenOrdersData>({
    orders: [],
    lastUpdate: new Date(),
  });
  const intervalRef = useRef<NodeJS.Timeout>();

  const fetchOpenOrders = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.cachedAccount);
      const result = await response.json();
      
      console.log('📋 [useOpenOrders] Cached response:', result);
      
      // Extract orders from cached account data (backend returns flat array now)
      const orders = Array.isArray(result.orders) ? result.orders : [];
      
      setData({
        orders: orders,
        lastUpdate: new Date(),
      });
      console.log('✅ [useOpenOrders] Updated with', orders.length, 'open orders (polled 2x/s)');
    } catch (error) {
      console.error('❌ [useOpenOrders] Error fetching open orders:', error);
    }
  };

  useEffect(() => {
    fetchOpenOrders();
    
    intervalRef.current = setInterval(fetchOpenOrders, POLL_INTERVAL);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return data;
};

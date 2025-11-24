import { useState, useEffect, useRef } from 'react';
import { API_ENDPOINTS } from '@/lib/config';

interface Order {
  id: string;
  accountId: number;
  market: string;
  side: string;
  orderType: string;
  price: string;
  size: string;
  filledSize: string;
  status: string;
  timeInForce: string;
  createdTime: number;
  updatedTime: number;
}

interface OrdersData {
  orders: Order[];
  lastUpdate: Date;
}

const POLL_INTERVAL = 500; // 0.5 seconds = 2x per second

export const useOrders = () => {
  const [data, setData] = useState<OrdersData>({
    orders: [],
    lastUpdate: new Date(),
  });
  const intervalRef = useRef<NodeJS.Timeout>();

  const fetchOrders = async () => {
    try {
      const response = await fetch(`${API_ENDPOINTS.cachedAccount.replace('/cached-account', '')}/orders`);
      const result = await response.json();
      
      console.log('📋 [useOrders] Response:', result);
      
      const orders = result.data || [];
      
      setData({
        orders: orders,
        lastUpdate: new Date(),
      });
      console.log('✅ [useOrders] Updated with', orders.length, 'orders');
    } catch (error) {
      console.error('❌ [useOrders] Error fetching orders:', error);
    }
  };

  useEffect(() => {
    fetchOrders();
    
    intervalRef.current = setInterval(fetchOrders, POLL_INTERVAL);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return data;
};

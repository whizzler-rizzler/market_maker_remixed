import { useState, useEffect } from 'react';
import { API_ENDPOINTS } from '@/lib/config';
import { useToast } from '@/hooks/use-toast';

export interface BotConfig {
  market: string;
  spread_percentage: number;
  order_size: string;
  refresh_interval: number;
  price_move_threshold: number;
}

export interface BotStatus {
  running: boolean;
  config: BotConfig;
  active_orders: number;
  last_quote_price: number;
  current_quotes: {
    bid: number;
    ask: number;
  };
  order_ids: string[];
}

export const useBotStatus = () => {
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const fetchStatus = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.botStatus);
      if (!response.ok) {
        throw new Error('Failed to fetch bot status');
      }
      const data = await response.json();
      setBotStatus(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching bot status:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 2000); // Poll every 2 seconds
    return () => clearInterval(interval);
  }, []);

  const startBot = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.botStart, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to start bot');
      }
      const data = await response.json();
      toast({
        title: "Bot Started",
        description: `Market making bot is now running on ${data.config.market}`,
      });
      await fetchStatus();
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      toast({
        title: "Failed to Start Bot",
        description: message,
        variant: "destructive",
      });
      throw err;
    }
  };

  const stopBot = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.botStop, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to stop bot');
      }
      const data = await response.json();
      toast({
        title: "Bot Stopped",
        description: "Market making bot has been stopped and all orders cancelled",
      });
      await fetchStatus();
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      toast({
        title: "Failed to Stop Bot",
        description: message,
        variant: "destructive",
      });
      throw err;
    }
  };

  const updateConfig = async (config: Partial<BotConfig>) => {
    try {
      const response = await fetch(API_ENDPOINTS.botConfig, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update config');
      }
      const data = await response.json();
      toast({
        title: "Config Updated",
        description: "Bot configuration has been updated",
      });
      await fetchStatus();
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      toast({
        title: "Failed to Update Config",
        description: message,
        variant: "destructive",
      });
      throw err;
    }
  };

  return {
    botStatus,
    isLoading,
    error,
    startBot,
    stopBot,
    updateConfig,
    refreshStatus: fetchStatus,
  };
};

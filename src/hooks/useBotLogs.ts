import { useState, useEffect } from 'react';
import { API_ENDPOINTS } from '@/lib/config';

interface BotLog {
  timestamp: string;
  level: string;
  message: string;
}

export const useBotLogs = (autoRefresh = true) => {
  const [logs, setLogs] = useState<BotLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.botLogs);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch bot logs: ${response.statusText}`);
      }
      
      const data = await response.json();
      setLogs(data.logs || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      console.error('Error fetching bot logs:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    
    if (autoRefresh) {
      const interval = setInterval(fetchLogs, 2000); // Refresh every 2 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  return { logs, isLoading, error, refetch: fetchLogs };
};

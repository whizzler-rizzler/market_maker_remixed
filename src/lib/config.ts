/**
 * Configuration for backend services
 */

// Python proxy URL for Extended API
export const PYTHON_PROXY_URL = import.meta.env.VITE_PYTHON_PROXY_URL || 'https://market-maker-remixed.onrender.com';

// Convert HTTP URL to WebSocket URL
export const getWebSocketUrl = (httpUrl: string): string => {
  return httpUrl.replace(/^https/, 'wss').replace(/^http/, 'ws');
};

export const API_ENDPOINTS = {
  cachedAccount: `${PYTHON_PROXY_URL}/api/cached-account`,
  createOrder: `${PYTHON_PROXY_URL}/api/orders/create`,
  getOrders: `${PYTHON_PROXY_URL}/api/orders`,
  cancelOrder: (orderId: string) => `${PYTHON_PROXY_URL}/api/orders/${orderId}`,
  broadcasterStats: `${PYTHON_PROXY_URL}/api/broadcaster/stats`,
  websocketBroadcast: `${getWebSocketUrl(PYTHON_PROXY_URL)}/ws/broadcast`,
  botStart: `${PYTHON_PROXY_URL}/api/bot/start`,
  botStop: `${PYTHON_PROXY_URL}/api/bot/stop`,
  botStatus: `${PYTHON_PROXY_URL}/api/bot/status`,
  botConfig: `${PYTHON_PROXY_URL}/api/bot/config`,
    botLogs: `${PYTHON_PROXY_URL}/api/bot/logs`,
} as const;

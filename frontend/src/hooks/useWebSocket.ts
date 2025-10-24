import { useEffect, useRef, useState, useCallback } from 'react';

export const useWebSocket = (url: string) => {
  const [lastMessage, setLastMessage] = useState<MessageEvent | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'open' | 'closed'>('connecting');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus('open');
        
        // Send ping every 30 seconds to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);

        ws.onclose = () => {
          clearInterval(pingInterval);
        };
      };

      ws.onmessage = (event) => {
        setLastMessage(event);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setConnectionStatus('closed');
        
        // Attempt to reconnect after 5 seconds
        reconnectTimeoutRef.current = window.setTimeout(() => {
          console.log('Attempting to reconnect...');
          connect();
        }, 5000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnectionStatus('closed');
    }
  }, [url]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not open. Cannot send message.');
    }
  }, []);

  return {
    lastMessage,
    connectionStatus,
    sendMessage,
  };
};

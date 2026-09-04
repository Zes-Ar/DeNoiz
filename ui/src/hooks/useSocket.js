import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = 'ws://127.0.0.1:8000/ws';
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000]; // exponential backoff, capped

/**
 * WebSocket hook — follows WEBSOCKET_CONTRACT.md exactly.
 *
 * Returns:
 *  - status:       last `status` message from backend
 *  - waveform:     last `waveform` message (noisy[], clean[], t)
 *  - metrics:      last `metrics` message
 *  - error:        last `error` message (or null)
 *  - connState:    "connected" | "reconnecting" | "disconnected"
 *  - sendCommand:  fn(action, extras?) → sends { type: "command", action, ...extras }
 */
export function useSocket() {
  const [status, setStatus]       = useState(null);
  const [waveform, setWaveform]   = useState(null);
  const [metrics, setMetrics]     = useState(null);
  const [error, setError]         = useState(null);
  const [connState, setConnState] = useState('disconnected');

  const wsRef       = useRef(null);
  const retryRef    = useRef(0);
  const timerRef    = useRef(null);
  const unmountRef  = useRef(false);

  const connect = useCallback(() => {
    if (unmountRef.current) return;

    setConnState('reconnecting');
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      retryRef.current = 0;
      setConnState('connected');
      setError(null);
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        switch (msg.type) {
          case 'status':   setStatus(msg);   break;
          case 'waveform': setWaveform(msg); break;
          case 'metrics':  setMetrics(msg);  break;
          case 'error':    setError(msg);    break;
          default: break;
        }
      } catch { /* ignore bad JSON */ }
    };

    ws.onclose = () => {
      if (unmountRef.current) return;
      setConnState('reconnecting');
      const delay = RECONNECT_DELAYS[Math.min(retryRef.current, RECONNECT_DELAYS.length - 1)];
      retryRef.current++;
      timerRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close(); // triggers onclose → reconnect
    };
  }, []);

  useEffect(() => {
    unmountRef.current = false;
    connect();
    return () => {
      unmountRef.current = true;
      clearTimeout(timerRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  const sendCommand = useCallback((action, extras) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'command', action, ...extras }));
    }
  }, []);

  return { status, waveform, metrics, error, connState, sendCommand };
}

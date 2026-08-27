import { useEffect, useRef, useState } from "react";

const DEFAULT_WS_URL =
  import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8000/ws/simulation`;

/**
 * Conecta ao WebSocket do backend e mantém o snapshot mais recente da
 * simulação (veículos, cruzamentos, métricas, nível de caos e eventos).
 * Reconecta automaticamente caso a conexão caia.
 */
export function useSimulationSocket(url = DEFAULT_WS_URL) {
  const [data, setData] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const retryRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    function connect() {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!cancelled) setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (!cancelled) setData(parsed);
        } catch (err) {
          // ignora frames malformados (pode acontecer por causa das
          // mutações concorrentes do lado do backend)
        }
      };

      ws.onclose = () => {
        if (cancelled) return;
        setConnected(false);
        retryRef.current = setTimeout(connect, 1500);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, [url]);

  return { data, connected };
}

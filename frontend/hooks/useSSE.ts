"use client";

import { useEffect, useRef, useCallback } from "react";
import { useAppStore } from "./useAppStore";
import { RequestEvent } from "./useAppStore";

export function useSSE() {
  const { setConnected, addLiveEvent, setStats } = useAppStore();
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 10;

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource("/api/backend/events/stream");
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
      reconnectAttempts.current = 0;
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "heartbeat") {
          // Keep alive
          return;
        }
        if (data.type === "stats") {
          setStats(data);
          return;
        }
        if (data.type === "request" || data.request_id || data.decision) {
          addLiveEvent(data);
        }
      } catch (e) {
        console.warn("Failed to parse SSE event:", e);
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();

      if (reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
        reconnectAttempts.current++;
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      }
    };
  }, [setConnected, addLiveEvent, setStats]);

  useEffect(() => {
    connect();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  return { connected: useAppStore((s) => s.isConnected) };
}

export function useLiveEvents(limit = 100) {
  const events = useAppStore((s) => s.liveEvents);
  return events.slice(0, limit);
}
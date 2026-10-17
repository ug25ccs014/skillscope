import { useCallback, useEffect, useState } from 'react';

export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export type ApiStatus = 'checking' | 'connected' | 'disconnected';
export type HealthResponse = { status: string; service: string; version: string; environment?: string };

/** Checks the backend health endpoint once on mount and on demand. */
export function useApiStatus() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const checkApi = useCallback(async () => {
    setApiStatus('checking');
    try {
      const response = await fetch(`${apiBaseUrl}/api/health`, { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(4000) });
      if (!response.ok) throw new Error(`API returned HTTP ${response.status}`);
      const result = (await response.json()) as HealthResponse;
      if (result.status !== 'ok') throw new Error('API health status is not OK');
      setHealth(result); setApiStatus('connected');
    } catch { setHealth(null); setApiStatus('disconnected'); }
  }, []);
  useEffect(() => { void checkApi(); }, [checkApi]);
  return { apiStatus, health, checkApi };
}

import { useEffect, useState } from 'react';
import { CommandCenterState } from './types';
import { getApiBaseUrl, getCommandCenterState } from './api';

export function useCommandCenterState() {
  const [state, setState] = useState<CommandCenterState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let closed = false;
    let eventSource: EventSource | null = null;

    async function bootstrap() {
      try {
        const snapshot = await getCommandCenterState();
        if (!closed) {
          setState(snapshot);
          setLoading(false);
        }
      } catch (err) {
        if (!closed) {
          setError(err instanceof Error ? err.message : 'Failed to load command center state');
          setLoading(false);
        }
      }

      if (closed) return;
      eventSource = new EventSource(`${getApiBaseUrl()}/api/command-center/events`, { withCredentials: true });
      const apply = (event: MessageEvent<string>) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload && payload.app && payload.youtube && payload.stumps) {
            setState(payload);
            setError(null);
          } else {
            // For incremental events, refresh the full snapshot lazily.
            getCommandCenterState().then(setState).catch(() => undefined);
          }
        } catch {
          getCommandCenterState().then(setState).catch(() => undefined);
        }
      };

      eventSource.addEventListener('SNAPSHOT', apply as EventListener);
      eventSource.addEventListener('EVENT_DETECTED', apply as EventListener);
      eventSource.addEventListener('CLIP_READY', apply as EventListener);
      eventSource.addEventListener('PUBLISH_SUCCESS', apply as EventListener);
      eventSource.addEventListener('PUBLISH_FAILED', apply as EventListener);
      eventSource.addEventListener('STUMPS_SCORE_UPDATED', apply as EventListener);
      eventSource.addEventListener('YOUTUBE_LIVE_STARTED', apply as EventListener);
      eventSource.addEventListener('YOUTUBE_LIVE_STOPPED', apply as EventListener);
      eventSource.onerror = () => {
        setError((prev) => prev || 'Realtime connection lost. Showing last known state.');
      };
    }

    bootstrap();

    return () => {
      closed = true;
      eventSource?.close();
    };
  }, []);

  return { state, setState, loading, error };
}

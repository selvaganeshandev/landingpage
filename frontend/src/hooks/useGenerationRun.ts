import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "@/services/api";

/**
 * Tracks the AI prompt-generation run for a project.
 *
 * Generation happens in the engine, so the page owns no progress state of its
 * own — it asks the server what the current run is on mount and polls while
 * one is live. That is what lets someone start a run, navigate away, and come
 * back to find it still going or finished.
 *
 * Polling stops as soon as the run leaves a live state, so an idle page makes
 * no requests.
 */

export interface GenerationRun {
  id: number;
  status: "INIT" | "PROC" | "DONE" | "FAIL" | "ACPT" | "DISC";
  stage: string;
  stage_index: number;
  stage_total: number;
  stage_label: string;
  progress: number;
  error: string;
  target_count?: number;
  candidate_count: number;
  candidates?: any[];
}

const POLL_MS = 3000;

export function useGenerationRun(domainId?: number) {
  const [run, setRun] = useState<GenerationRun | null>(null);
  const [loading, setLoading] = useState(true);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clear = () => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
  };

  const refresh = useCallback(async () => {
    if (!domainId) {
      setRun(null);
      setLoading(false);
      return null;
    }
    try {
      const active: any = await apiClient.getActiveGenerationRun(domainId);
      // The endpoint returns {run: null} when there is nothing to show.
      const next = active && active.id ? (active as GenerationRun) : null;
      // Fetch candidates alongside the run once it is ready for review.
      if (next && next.status === "DONE" && !next.candidates) {
        const detail: any = await apiClient.getGenerationRun(next.id);
        setRun(detail);
        return detail;
      }
      setRun(next);
      return next;
    } catch {
      // A failed poll is not worth surfacing; the next tick retries.
      return null;
    } finally {
      setLoading(false);
    }
  }, [domainId]);

  // Poll only while the engine is actually working.
  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      const current = await refresh();
      if (cancelled) return;
      const live = current && (current.status === "INIT" || current.status === "PROC");
      if (live) {
        timer.current = setTimeout(tick, POLL_MS);
      }
    };

    setLoading(true);
    void tick();

    return () => {
      cancelled = true;
      clear();
    };
  }, [refresh]);

  const start = useCallback(
    async (config: any) => {
      if (!domainId) throw new Error("No project selected");
      const created: any = await apiClient.createGenerationRun({
        domain_id: domainId,
        config,
      });
      setRun(created);
      // Kick the poll immediately rather than waiting a full interval.
      clear();
      timer.current = setTimeout(async function tick() {
        const current = await refresh();
        if (current && (current.status === "INIT" || current.status === "PROC")) {
          timer.current = setTimeout(tick, POLL_MS);
        }
      }, 1200);
      return created;
    },
    [domainId, refresh],
  );

  const accept = useCallback(
    async (acceptedIds: number[], edits: Record<string, string>) => {
      if (!run) return null;
      const result = await apiClient.acceptGenerationRun(run.id, {
        accepted_ids: acceptedIds,
        edits,
      });
      setRun(null);
      return result;
    },
    [run],
  );

  const discard = useCallback(async () => {
    if (!run) return;
    await apiClient.discardGenerationRun(run.id);
    setRun(null);
  }, [run]);

  return { run, loading, start, accept, discard, refresh };
}

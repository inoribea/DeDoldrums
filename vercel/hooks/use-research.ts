"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type {
  ChallengeResult,
  FinalFinding,
  LiveFinding,
  ResearchComplete,
  ResearchStatus,
  StageId,
} from "@/lib/types";
import { normalizeStage, STAGES } from "@/lib/stages";
import { useLanguage } from "@/lib/i18n";

interface UseResearchState {
  status: ResearchStatus;
  currentStage: StageId | null;
  stageDescription: string | null;
  findings: LiveFinding[];
  challenge: ChallengeResult | null;
  brief: string | null;
  finalFindings: FinalFinding[] | null;
  confidence: ResearchComplete["confidence"] | null;
  error: string | null;
  statusMessage: string | null;
}

const INITIAL_STATE: UseResearchState = {
  status: "idle",
  currentStage: null,
  stageDescription: null,
  findings: [],
  challenge: null,
  brief: null,
  finalFindings: null,
  confidence: null,
  error: null,
  statusMessage: null,
};

interface UseResearchReturn extends UseResearchState {
  start: (question: string) => Promise<void>;
  cancel: () => Promise<void>;
  reset: () => void;
}

function truncate(text: string, max = 300): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max).trimEnd()}…`;
}

function summarizeFinding(data: {
  summary?: string;
  content?: string;
}): { summary: string; content: string | null } {
  const content = data.content ?? null;
  const summary = data.summary ?? (content ? truncate(content) : "");
  return { summary, content };
}

export function useResearch(): UseResearchReturn {
  const [state, setState] = useState<UseResearchState>(INITIAL_STATE);
  const eventSourceRef = useRef<EventSource | null>(null);
  const findingsCountRef = useRef(0);
  const sessionIdRef = useRef<string | null>(null);
  const { t } = useLanguage();

  const closeStream = useCallback(() => {
    const es = eventSourceRef.current;
    if (es) {
      es.close();
      eventSourceRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    closeStream();
    findingsCountRef.current = 0;
    sessionIdRef.current = null;
    setState(INITIAL_STATE);
  }, [closeStream]);

  const cancel = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    try {
      await fetch(`/api/session/${encodeURIComponent(sid)}/cancel`, { method: "POST" });
    } catch {
      // best-effort — close locally regardless
    }
    closeStream();
    setState((s) => ({ ...s, status: "complete" as const }));
  }, [closeStream]);

  const start = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;

      closeStream();
      findingsCountRef.current = 0;
      setState({
        ...INITIAL_STATE,
        status: "creating",
        currentStage: "-1",
        stageDescription: t(STAGES["-1"].descriptionKey),
      });

      try {
        const base = window.location.origin;
        const newResp = await fetch(`${base}/api/session/new`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: trimmed }),
        });
        if (!newResp.ok) {
          throw new Error(`Failed to create session (${newResp.status})`);
        }
        const { sessionId, bridgeUrl } = (await newResp.json()) as { sessionId: string; bridgeUrl?: string };
        if (!sessionId) throw new Error("Bridge returned no session id");
        sessionIdRef.current = sessionId;

        setState((s) => ({
          ...s,
          status: "starting",
        }));

        const startResp = await fetch(
          `${base}/api/session/${encodeURIComponent(sessionId)}/question`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: trimmed }),
          },
        );
        if (!startResp.ok) {
          throw new Error(`Failed to start research (${startResp.status})`);
        }

        // Connect SSE directly to bridge (bypasses Vercel 60s function timeout)
        const streamUrl = bridgeUrl
          ? `${bridgeUrl}/session/${encodeURIComponent(sessionId)}/stream`
          : `/api/research/stream?sid=${encodeURIComponent(sessionId)}`;
        const es = new EventSource(streamUrl);
        eventSourceRef.current = es;

        setState((s) => ({ ...s, status: "streaming" }));

        es.addEventListener("stage_change", (e: MessageEvent) => {
          try {
            const { stage, description } = JSON.parse(e.data) as {
              stage: number | string;
              description?: string;
            };
            const id = normalizeStage(stage);
            setState((s) => ({
              ...s,
              currentStage: id ?? s.currentStage,
              stageDescription:
                description ??
                (id ? t(STAGES[id].descriptionKey) : s.stageDescription),
            }));
          } catch {
            /* ignore malformed payloads */
          }
        });

        es.addEventListener("status", (e: MessageEvent) => {
          try {
            const { message } = JSON.parse(e.data) as { message: string };
            if (message) setState((s) => ({ ...s, statusMessage: message }));
          } catch { /* ignore */ }
        });

        es.addEventListener("finding", (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data) as {
              summary?: string;
              content?: string;
              stage?: string | number;
            };
            findingsCountRef.current += 1;
            const { summary, content } = summarizeFinding(data);
            const finding: LiveFinding = {
              index: findingsCountRef.current,
              stage: data.stage ?? null,
              summary,
              content,
            };
            setState((s) => ({ ...s, findings: [...s.findings, finding] }));
          } catch {
            /* ignore malformed payloads */
          }
        });

        es.addEventListener("challenge_result", (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data) as ChallengeResult;
            setState((s) => ({ ...s, challenge: data }));
          } catch {
            /* ignore malformed payloads */
          }
        });

        es.addEventListener("complete", (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data) as ResearchComplete;
            setState((s) => ({
              ...s,
              brief: data.brief ?? null,
              finalFindings: data.findings ?? null,
              confidence: data.confidence ?? null,
            }));
          } catch {
            /* ignore malformed payloads */
          }
        });

        es.addEventListener("error", (e: MessageEvent) => {
          // Bridge-sent error event (still inside the SSE stream).
          let message = "Research stream reported an error";
          if (e.data) {
            try {
              const data = JSON.parse(e.data) as { message?: string };
              if (data.message) message = data.message;
            } catch {
              /* keep default */
            }
          }
          setState((s) => ({ ...s, status: "error", error: message }));
          closeStream();
        });

        es.addEventListener("done", () => {
          setState((s) => ({
            ...s,
            status: "complete",
            currentStage: s.currentStage ?? "4",
          }));
          closeStream();
        });

        // Native onerror — fires on connection failure / unexpected close.
        es.onerror = () => {
          setState((s) => {
            // If we already reached a terminal state, don't clobber it.
            if (s.status === "complete" || s.status === "error") return s;
            return {
              ...s,
              status: "error",
              error: "SSE connection interrupted",
            };
          });
          closeStream();
        };
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Unexpected request failure";
        setState((s) => ({ ...s, status: "error", error: message }));
        closeStream();
      }
    },
    [closeStream, t],
  );

  useEffect(() => () => closeStream(), [closeStream]);

  return { ...state, start, cancel, reset };
}
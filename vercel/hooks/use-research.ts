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

const POLL_INTERVAL = 2000;
const LS_SESSION_KEY = "research-agent-session";

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
  savedQuestion: string | null;
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

function loadSession(): { sid: string; question: string } | null {
  try {
    const raw = localStorage.getItem(LS_SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed?.sid && parsed?.question) return { sid: parsed.sid, question: parsed.question };
  } catch { /* ignore */ }
  return null;
}

function saveSession(sid: string, question: string) {
  try { localStorage.setItem(LS_SESSION_KEY, JSON.stringify({ sid, question })); } catch { /* ignore */ }
}

function clearSession() {
  try { localStorage.removeItem(LS_SESSION_KEY); } catch { /* ignore */ }
}

export function useResearch(): UseResearchReturn {
  const [state, setState] = useState<UseResearchState>(INITIAL_STATE);
  const [savedQuestion, setSavedQuestion] = useState<string | null>(null);
  const pollingRef = useRef<number | null>(null);
  const findingsCountRef = useRef(0);
  const sessionIdRef = useRef<string | null>(null);
  const seenCountRef = useRef(0);
  const stoppedRef = useRef(false);
  const { t } = useLanguage();

  const stopPolling = useCallback(() => {
    stoppedRef.current = true;
    if (pollingRef.current !== null) {
      window.clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    stopPolling();
    findingsCountRef.current = 0;
    seenCountRef.current = 0;
    sessionIdRef.current = null;
    stoppedRef.current = false;
    clearSession();
    setState(INITIAL_STATE);
  }, [stopPolling]);

  const cancel = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    try {
      await fetch(`/api/session/${encodeURIComponent(sid)}/cancel`, { method: "POST" });
    } catch { /* best-effort */ }
    stopPolling();
    clearSession();
    setState((s) => ({ ...s, status: "complete" as const }));
  }, [stopPolling]);

  const processMessages = useCallback(
    (messages: string[]) => {
      for (let i = seenCountRef.current; i < messages.length; i++) {
        try {
          const event = JSON.parse(messages[i]) as Record<string, unknown>;

          if (event.type === "stage_change") {
            const stage = event.stage as number | string | undefined;
            const description = event.description as string | undefined;
            const id = stage != null ? normalizeStage(stage) : null;
            setState((s) => ({
              ...s,
              currentStage: id ?? s.currentStage,
              stageDescription: description ?? (id ? t(STAGES[id].descriptionKey) : s.stageDescription),
            }));
          } else if (event.type === "status") {
            const message = event.message as string | undefined;
            if (message) setState((s) => ({ ...s, statusMessage: message }));
          } else if (event.type === "finding") {
            findingsCountRef.current++;
            const { summary, content } = summarizeFinding(event as { summary?: string; content?: string });
            const finding: LiveFinding = {
              index: findingsCountRef.current,
              summary,
              content,
              stage: event.stage != null ? String(event.stage) : null,
            };
            setState((s) => ({ ...s, findings: [...s.findings, finding] }));
          } else if (event.type === "challenge_result") {
            setState((s) => ({
              ...s,
              challenge: {
                status: (event.status as string) || "completed",
                results: event.results as Record<string, unknown> | undefined,
              },
            }));
          } else if (event.type === "complete") {
            clearSession();
            setState((s) => ({
              ...s,
              status: "complete",
              brief: (event.brief as string) || s.brief || "",
              finalFindings: (event.findings as FinalFinding[]) || [],
              confidence: event.confidence as ResearchComplete["confidence"] || null,
              currentStage: "4",
              statusMessage: null,
            }));
          } else if (event.type === "error") {
            clearSession();
            setState((s) => ({
              ...s,
              status: "error",
              error: (event.message as string) || "Unknown error",
            }));
          }
        } catch { /* skip malformed */ }
      }
      seenCountRef.current = messages.length;
    },
    [t],
  );

  const setupPolling = useCallback(
    (sid: string, question: string) => {
      stoppedRef.current = false;
      sessionIdRef.current = sid;
      saveSession(sid, question);

      let pollCount = 0;
      const base = window.location.origin;
      const poll = () => {
        if (stoppedRef.current) return;
        pollCount++;
        fetch(`${base}/api/session/${encodeURIComponent(sid)}/history`)
          .then((r) => {
            if (!r.ok || stoppedRef.current) return null;
            return r.json() as Promise<{ done: boolean; messages: string[] }>;
          })
          .then((data) => {
            if (!data || stoppedRef.current) return;
            const msgCount = data.messages?.length || 0;
            if (msgCount > seenCountRef.current) {
              console.log(`[poll #${pollCount}] new messages: ${seenCountRef.current} → ${msgCount}, done=${data.done}`);
            }
            processMessages(data.messages || []);
            if (data.done) {
              stopPolling();
              setState((s) => {
                if (s.status !== "complete" && s.status !== "error") return { ...s, status: "complete" };
                return s;
              });
              return;
            }
            if (!stoppedRef.current) {
              pollingRef.current = window.setTimeout(poll, POLL_INTERVAL);
            }
          })
          .catch((e) => {
            console.warn("[poll] error:", e);
            if (!stoppedRef.current) {
              pollingRef.current = window.setTimeout(poll, POLL_INTERVAL);
            }
          });
      };
      pollingRef.current = window.setTimeout(poll, 0);
    },
    [stopPolling, processMessages],
  );

  const start = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;

      stopPolling();
      findingsCountRef.current = 0;
      seenCountRef.current = 0;
      setState({ ...INITIAL_STATE, status: "creating", currentStage: "-1", stageDescription: t(STAGES["-1"].descriptionKey) });

      try {
        const base = window.location.origin;
        const newResp = await fetch(`${base}/api/session/new`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: trimmed }),
        });
        if (!newResp.ok) throw new Error(`Failed to create session (${newResp.status})`);

        const { sessionId } = (await newResp.json()) as { sessionId: string };
        if (!sessionId) throw new Error("Bridge returned no session id");

        setState((s) => ({ ...s, status: "starting" }));

        const startResp = await fetch(
          `${base}/api/session/${encodeURIComponent(sessionId)}/question`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: trimmed }),
          },
        );
        if (!startResp.ok) throw new Error(`Failed to start research (${startResp.status})`);

        setState((s) => ({ ...s, status: "streaming" }));
        setSavedQuestion(trimmed);
        setupPolling(sessionId, trimmed);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unexpected request failure";
        setState((s) => ({ ...s, status: "error", error: message }));
      }
    },
    [stopPolling, setupPolling, t],
  );

  // On mount: reconnect to saved session if exists
  useEffect(() => {
    const saved = loadSession();
    if (!saved?.sid) return;
    // Check if session still exists on bridge
    const base = window.location.origin;
    fetch(`${base}/api/session/${encodeURIComponent(saved.sid)}/history`)
      .then((r) => {
        if (!r.ok) { clearSession(); return; }
        return r.json();
      })
      .then((data: { done: boolean; messages: string[] } | undefined) => {
        if (!data) return;
        processMessages(data.messages || []);
        if (data.done) {
          setState((s) => ({
            ...s,
            status: "complete",
            currentStage: "4",
          }));
          clearSession();
        } else {
          setState((s) => ({ ...s, status: "streaming" }));
          setSavedQuestion(saved.question);
          setupPolling(saved.sid, saved.question);
        }
      })
      .catch(() => clearSession());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  return { ...state, start, cancel, reset, savedQuestion };
}

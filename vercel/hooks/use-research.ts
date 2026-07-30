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
const LS_SESSION_KEY = "dedoldrums-session";

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
  statusLog: string[];
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
  statusLog: [],
};

interface UseResearchReturn extends UseResearchState {
  start: (question: string) => Promise<void>;
  cancel: () => Promise<void>;
  reset: () => void;
  savedQuestion: string | null;
  latestStatus: string | null;
  elapsedSeconds: number;
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
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const pollingRef = useRef<number | null>(null);
  const startedAtRef = useRef<number | null>(null);
  const completedAtRef = useRef<number | null>(null);
  const findingsCountRef = useRef(0);
  const sessionIdRef = useRef<string | null>(null);
  const seenCountRef = useRef(0);
  const stoppedRef = useRef(false);
  const startingRef = useRef(false);
  const { t } = useLanguage();

  // ── Timer: single useEffect, driven by status ──
  const isBusy = state.status === "creating" || state.status === "starting" || state.status === "streaming";
  useEffect(() => {
    if (!isBusy || !startedAtRef.current) return;
    const id = window.setInterval(() => {
      const end = completedAtRef.current ?? Date.now();
      if (startedAtRef.current) {
        setElapsedSeconds(Math.floor((end - startedAtRef.current) / 1000));
      }
    }, 250);
    return () => window.clearInterval(id);
  }, [isBusy]);

  const stopPolling = useCallback(() => {
    stoppedRef.current = true;
    if (pollingRef.current !== null) {
      window.clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    stopPolling();
    startingRef.current = false;
    findingsCountRef.current = 0;
    seenCountRef.current = 0;
    sessionIdRef.current = null;
    startedAtRef.current = null;
    completedAtRef.current = null;
    stoppedRef.current = false;
    clearSession();
    setElapsedSeconds(0);
    setState(INITIAL_STATE);
  }, [stopPolling]);

  const cancel = useCallback(async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    try {
      await fetch(`/api/session/${encodeURIComponent(sid)}/cancel`, { method: "POST" });
    } catch { /* best-effort */ }
    stopPolling();
    startingRef.current = false;
    clearSession();
    setState((s) => ({ ...s, status: "cancelled" as const }));
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
            if (message) setState((s) => ({ ...s, statusLog: [...s.statusLog, message] }));
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
            completedAtRef.current = Date.now();
            clearSession();
            setState((s) => ({
              ...s,
              status: "complete",
              brief: (event.brief as string) || s.brief || "",
              finalFindings: (event.findings as FinalFinding[]) || [],
              confidence: event.confidence as ResearchComplete["confidence"] || null,
              currentStage: "4",
              statusLog: [],
            }));
          } else if (event.type === "error") {
            completedAtRef.current = Date.now();
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
        fetch(`${base}/api/session/${encodeURIComponent(sid)}/history?_=${Date.now()}`, { method: "POST" })
          .then((r) => {
            if (stoppedRef.current) return null;
            if (!r.ok) {
              throw new Error(`History request failed with ${r.status}`);
            }
            return r.json() as Promise<{ done: boolean; messages: string[]; startedAt?: number }>;
          })
          .then((data) => {
            if (!data || stoppedRef.current) return;
            // On reconnect: adopt server timestamp if we don't have one yet
            if (!startedAtRef.current && data.startedAt) {
              startedAtRef.current = data.startedAt;
            }
            const msgCount = data.messages?.length || 0;
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
      if (startingRef.current) return;
      startingRef.current = true;

      stopPolling();
      findingsCountRef.current = 0;
      seenCountRef.current = 0;
      setState({ ...INITIAL_STATE, status: "creating", currentStage: "-1", stageDescription: t(STAGES["-1"].descriptionKey) });
      startedAtRef.current = Date.now();
      completedAtRef.current = null;
      setElapsedSeconds(0);

      try {
        const base = window.location.origin;
        // Read language from localStorage to pass to the bridge
        let lang: string | undefined;
        try { lang = window.localStorage.getItem("dedoldrums-lang") || undefined; } catch { /* ignore */ }

        const newResp = await fetch(`${base}/api/session/new`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: trimmed, language: lang }),
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
        startingRef.current = false;
      } catch (err) {
        startingRef.current = false;
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
    fetch(`${base}/api/session/${encodeURIComponent(saved.sid)}/history?_=${Date.now()}`, { method: "POST" })
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

  const latestStatus = state.statusLog.length > 0 ? state.statusLog[state.statusLog.length - 1] : null;

  return { ...state, start, cancel, reset, savedQuestion, latestStatus, elapsedSeconds };
}

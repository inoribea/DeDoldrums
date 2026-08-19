export type StageId = "-1" | "0" | "1" | "2" | "3" | "3.5" | "4";

export interface LiveFinding {
  /** Sequential index assigned as findings arrive. */
  index: number;
  /** Stage this finding was produced at, when available. */
  stage: string | number | null;
  /** Short summary if provided by the bridge, otherwise truncated content. */
  summary: string;
  /** Full raw content if provided. */
  content: string | null;
}

export interface FinalFinding {
  content?: string;
  summary?: string;
  confidence?: number;
  stage?: string | number;
  [key: string]: unknown;
}

export interface ChallengeResult {
  results: unknown;
  status: string;
}

export interface ResearchComplete {
  brief?: string;
  findings?: FinalFinding[];
  confidence?: number | Record<string, unknown>;
}

export interface HumanCheckpoint {
  /** Short hex id issued by the bridge for this pause. */
  checkpointId: string;
  /** The research question under review. */
  question: string;
  /** Stage 2 contradiction map as markdown text; may be empty. */
  contradictionMap: string;
  /** Stage 3 synthesis as markdown text; may be empty. */
  synthesis: string;
  /** Document audit outcome, or an empty object when the audit did not run. */
  audit: { passed: boolean; gaps: string[] } | Record<string, never>;
  /** Questions the pipeline still considers unresolved. */
  openQuestions: string[];
}

/** Operator decision sent back to the bridge to release a checkpoint. */
export type CheckpointAction = "continue" | "exit" | "feedback";

export type ResearchStatus =
  | "idle"
  | "creating"
  | "starting"
  | "streaming"
  | "checkpoint"
  | "complete"
  | "cancelled"
  | "error";
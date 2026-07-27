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

export type ResearchStatus =
  | "idle"
  | "creating"
  | "starting"
  | "streaming"
  | "complete"
  | "error";
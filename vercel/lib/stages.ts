import type { StageId, StageMeta } from "@/lib/types";

export const STAGE_ORDER: StageId[] = [
  "-1",
  "0",
  "1",
  "2",
  "3",
  "3.5",
  "4",
];

export const STAGES: Record<StageId, StageMeta> = {
  "-1": {
    id: "-1",
    label: "Initializing",
    description: "Spinning up the research session",
  },
  "0": {
    id: "0",
    label: "Discovering Perspectives",
    description: "Dynamic lens discovery from search results",
  },
  "1": {
    id: "1",
    label: "Multi-Perspective Scan",
    description: "Independent exploration across lenses",
  },
  "2": {
    id: "2",
    label: "Contradiction Mapping",
    description: "Conflicts, consensus, blind spots",
  },
  "3": {
    id: "3",
    label: "Synthesis",
    description: "Cross-lens connections into a structured brief",
  },
  "3.5": {
    id: "3.5",
    label: "Adversarial Gate",
    description: "Generator-Verifier pressure test on every finding",
  },
  "4": {
    id: "4",
    label: "Peer Review",
    description: "Confidence scores, bias check, missing angles",
  },
};

/** Normalize a numeric or string stage into the canonical StageId string. */
export function normalizeStage(stage: number | string): StageId | null {
  const key = String(stage);
  return key in STAGES ? (key as StageId) : null;
}

/** Index of a stage in the pipeline order, or -1 if unknown. */
export function stageIndex(stage: number | string): number {
  const id = normalizeStage(stage);
  return id ? STAGE_ORDER.indexOf(id) : -1;
}
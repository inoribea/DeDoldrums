import type { StageId } from "@/lib/types";
import type { Translations } from "@/lib/i18n";

export const STAGE_ORDER: StageId[] = [
  "-1",
  "0",
  "1",
  "2",
  "3",
  "3.5",
  "4",
];

/**
 * Stage metadata is fully driven by the i18n dictionary — no hardcoded
 * English strings here. Consumers look up labels/descriptions via the
 * translation keys returned by these helpers.
 */
export const STAGES: Record<
  StageId,
  { id: StageId; labelKey: keyof Translations; descriptionKey: keyof Translations }
> = {
  "-1": {
    id: "-1",
    labelKey: "stage.-1.label",
    descriptionKey: "stage.-1.description",
  },
  "0": {
    id: "0",
    labelKey: "stage.0.label",
    descriptionKey: "stage.0.description",
  },
  "1": {
    id: "1",
    labelKey: "stage.1.label",
    descriptionKey: "stage.1.description",
  },
  "2": {
    id: "2",
    labelKey: "stage.2.label",
    descriptionKey: "stage.2.description",
  },
  "3": {
    id: "3",
    labelKey: "stage.3.label",
    descriptionKey: "stage.3.description",
  },
  "3.5": {
    id: "3.5",
    labelKey: "stage.3.5.label",
    descriptionKey: "stage.3.5.description",
  },
  "4": {
    id: "4",
    labelKey: "stage.4.label",
    descriptionKey: "stage.4.description",
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
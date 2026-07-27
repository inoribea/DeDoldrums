"use client";

import { Check } from "lucide-react";

import { cn } from "@/lib/utils";
import { STAGE_ORDER, STAGES, stageIndex } from "@/lib/stages";
import type { StageId } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

interface StageStepperProps {
  currentStage: StageId | null;
  isComplete: boolean;
}

export function StageStepper({ currentStage, isComplete }: StageStepperProps) {
  const { t } = useLanguage();
  const currentIdx = currentStage ? stageIndex(currentStage) : -1;

  return (
    <ol className="relative flex flex-col gap-0">
      {STAGE_ORDER.map((id, idx) => {
        const meta = STAGES[id];
        const isDone = isComplete ? true : currentIdx > idx;
        const isActive = !isComplete && currentIdx === idx;
        const isPending = !isDone && !isActive;
        const isLast = idx === STAGE_ORDER.length - 1;

        return (
          <li
            key={id}
            className={cn("relative flex gap-3", !isLast && "pb-4")}
          >
            {/* connector line */}
            {!isLast && (
              <span
                aria-hidden
                className={cn(
                  "absolute left-[11px] top-6 bottom-0 w-px",
                  isDone ? "bg-success/40" : "bg-border",
                )}
              />
            )}
            {/* indicator */}
            <span
              className={cn(
                "relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[10px] font-medium transition-colors",
                isDone &&
                  "border-success/50 bg-success/15 text-success",
                isActive &&
                  "border-primary bg-primary/15 text-primary",
                isPending &&
                  "border-border bg-card text-muted-foreground",
              )}
            >
              {isDone ? (
                <Check className="h-3.5 w-3.5" strokeWidth={3} />
              ) : (
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    isActive && "bg-primary animate-pulse-soft",
                    isPending && "bg-muted-foreground/50",
                  )}
                />
              )}
            </span>
            {/* label */}
            <div className="flex min-w-0 flex-col pt-0.5">
              <span
                className={cn(
                  "text-sm font-medium leading-tight",
                  isActive && "text-foreground",
                  isDone && "text-foreground/80",
                  isPending && "text-muted-foreground",
                )}
              >
                {t(meta.labelKey)}
              </span>
              <span className="mt-0.5 text-xs text-muted-foreground">
                {t(meta.descriptionKey)}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
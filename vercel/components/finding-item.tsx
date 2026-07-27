"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { LiveFinding } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

interface FindingItemProps {
  finding: LiveFinding;
}

export function FindingItem({ finding }: FindingItemProps) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const hasFull = finding.content !== null && finding.content !== finding.summary;
  const display = expanded && finding.content ? finding.content : finding.summary;

  return (
    <div className="animate-fade-in-up rounded-md border border-border/60 bg-secondary/30 p-3">
      <div className="mb-1.5 flex items-center gap-2">
        <Badge variant="muted" className="font-mono">
          #{finding.index}
        </Badge>
        {finding.stage !== null && finding.stage !== undefined && (
          <Badge variant="outline" className="font-mono text-[10px]">
            stage {String(finding.stage)}
          </Badge>
        )}
      </div>
      <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap break-words">
        {display}
      </p>
      {hasFull && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className={cn(
            "mt-2 text-xs font-medium text-primary",
            "transition-colors hover:text-primary/80",
          )}
        >
          {expanded ? t("finding.showLess") : t("finding.showMore")}
        </button>
      )}
    </div>
  );
}
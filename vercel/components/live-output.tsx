"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Loader2, ShieldCheck, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { FindingItem } from "@/components/finding-item";
import { Button } from "@/components/ui/button";
import type { ChallengeResult, LiveFinding, ResearchStatus } from "@/lib/types";
import { useLanguage } from "@/lib/i18n";

interface LiveOutputProps {
  status: ResearchStatus;
  findings: LiveFinding[];
  challenge: ChallengeResult | null;
  statusLog: string[];
  latestStatus: string | null;
}

export function LiveOutput({ status, findings, challenge, statusLog, latestStatus }: LiveOutputProps) {
  const { t } = useLanguage();
  const viewportRef = useRef<HTMLDivElement>(null);
  const [thinkingOpen, setThinkingOpen] = useState(true);

  // Auto-scroll to bottom on new content.
  useEffect(() => {
    viewportRef.current?.scrollIntoView({ block: "end", behavior: "auto" });
  }, [findings, challenge, statusLog]);

  const isStreaming = status === "streaming" || status === "starting";
  const isEmpty = findings.length === 0 && !challenge;
  const latestMsg = latestStatus || (statusLog.length > 0 ? statusLog[statusLog.length - 1] : null);

  return (
    <Card className="flex h-[360px] flex-col">
      <CardHeader className="shrink-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          {t("live.title")}
          {isStreaming && (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          )}
          {latestMsg && (
            <span className="ml-2 text-xs font-normal text-muted-foreground truncate">
              {latestMsg}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <Separator />
      <CardContent className="flex-1 overflow-hidden p-0">
        <ScrollArea className="h-full">
          <div className="flex flex-col gap-2.5 p-4">
            {/* Thinking process — collapsible status log */}
            {isStreaming && statusLog.length > 0 && (
              <div className="rounded-md border border-border/60 bg-secondary/20">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start gap-1.5 px-3 py-2 text-xs font-normal text-muted-foreground hover:bg-secondary/40"
                  onClick={() => setThinkingOpen(!thinkingOpen)}
                >
                  {thinkingOpen ? (
                    <ChevronDown className="h-3 w-3" />
                  ) : (
                    <ChevronRight className="h-3 w-3" />
                  )}
                  {t("live.thinking")} ({statusLog.length})
                </Button>
                {thinkingOpen && (
                  <div className="border-t border-border/40 px-3 py-2">
                    <ol className="flex flex-col gap-1 text-[11px] text-muted-foreground">
                      {statusLog.map((msg, i) => (
                        <li key={i} className="flex gap-2">
                          <span className="shrink-0 text-primary/50 tabular-nums">{i + 1}.</span>
                          <span className="break-all">{msg}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            )}

            {/* Findings */}
            {findings.map((f) => (
              <FindingItem key={f.index} finding={f} />
            ))}

            {/* Challenge result */}
            {challenge && (
              <div className="animate-fade-in-up rounded-md border border-border/60 bg-secondary/30 p-3">
                <div className="flex items-center gap-2">
                  {challenge.status === "verified" ||
                  challenge.status === "completed" ? (
                    <ShieldCheck className="h-4 w-4 text-success" />
                  ) : (
                    <ShieldAlert className="h-4 w-4 text-warning" />
                  )}
                  <span className="text-sm font-medium">
                    {t("live.adversarialGate")}
                  </span>
                  <Badge
                    variant={
                      challenge.status === "verified" ||
                      challenge.status === "completed"
                        ? "success"
                        : "warning"
                    }
                    className="ml-auto font-mono text-[10px]"
                  >
                    {challenge.status}
                  </Badge>
                </div>
              </div>
            )}

            {/* Idle state */}
            {!isStreaming && isEmpty && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                {t("live.idle")}
              </p>
            )}
            {/* Sentinel for auto-scroll */}
            <div ref={viewportRef} />
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

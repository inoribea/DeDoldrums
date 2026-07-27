"use client";

import { useEffect, useRef } from "react";
import { Loader2, ShieldCheck, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { FindingItem } from "@/components/finding-item";
import type { ChallengeResult, LiveFinding, ResearchStatus } from "@/lib/types";

interface LiveOutputProps {
  status: ResearchStatus;
  findings: LiveFinding[];
  challenge: ChallengeResult | null;
}

export function LiveOutput({ status, findings, challenge }: LiveOutputProps) {
  const viewportRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest finding.
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [findings, challenge]);

  const isStreaming = status === "streaming" || status === "starting";
  const isEmpty = findings.length === 0 && !challenge;

  return (
    <Card className="flex h-[360px] flex-col">
      <CardHeader className="shrink-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          Live output
          {isStreaming && (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          )}
        </CardTitle>
      </CardHeader>
      <Separator />
      <CardContent className="flex-1 overflow-hidden p-0">
        <ScrollArea className="h-full">
          <div ref={viewportRef} className="flex flex-col gap-2.5 p-4">
            {isEmpty && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                {isStreaming
                  ? "Waiting for the first finding…"
                  : "Findings will appear here as the agent researches."}
              </p>
            )}
            {findings.map((f) => (
              <FindingItem key={f.index} finding={f} />
            ))}
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
                    Adversarial gate
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
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  PauseCircle,
  Send,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  Square,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { useLanguage } from "@/lib/i18n";
import type { CheckpointAction, HumanCheckpoint } from "@/lib/types";
import type { Translations } from "@/lib/i18n";

const MAX_GAPS = 5;

interface CheckpointCardProps {
  checkpoint: HumanCheckpoint;
  onResolve: (action: CheckpointAction, note?: string) => Promise<void>;
}

interface CollapsibleSectionProps {
  titleKey: keyof Translations;
  body: string;
  defaultOpen?: boolean;
}

function CollapsibleSection({
  titleKey,
  body,
  defaultOpen = false,
}: CollapsibleSectionProps) {
  const { t } = useLanguage();
  const [open, setOpen] = useState(defaultOpen);
  const text = body.trim();

  return (
    <div className="rounded-md border border-border/60 bg-secondary/20">
      <Button
        variant="ghost"
        size="sm"
        className="w-full justify-start gap-1.5 px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-secondary/40"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {open ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        {t(titleKey)}
      </Button>
      {open && (
        <div className="border-t border-border/40">
          {text ? (
            <ScrollArea className="max-h-[220px]">
              <p className="whitespace-pre-wrap break-words px-3 py-2 font-mono text-[11px] leading-relaxed text-foreground/90">
                {text}
              </p>
            </ScrollArea>
          ) : (
            <p className="px-3 py-3 text-xs italic text-muted-foreground">
              {t("checkpoint.empty")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function auditState(
  audit: HumanCheckpoint["audit"],
): { passed: boolean; gaps: string[] } | null {
  return "passed" in audit ? audit : null;
}

export function CheckpointCard({ checkpoint, onResolve }: CheckpointCardProps) {
  const { t } = useLanguage();
  const [note, setNote] = useState("");
  const [pending, setPending] = useState<CheckpointAction | null>(null);
  const audit = auditState(checkpoint.audit);
  const gaps = audit?.gaps?.slice(0, MAX_GAPS) ?? [];
  const busy = pending !== null;

  async function handle(action: CheckpointAction) {
    if (busy) return;
    setPending(action);
    try {
      await onResolve(action, action === "feedback" ? note.trim() : "");
    } catch {
      /* hook already logged; keep the card so the operator can retry */
    } finally {
      setPending(null);
    }
  }

  return (
    <Card className="animate-fade-in-up border-warning/40 bg-warning/[0.03]">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          <PauseCircle className="h-4 w-4 text-warning" />
          {t("checkpoint.title")}
          {checkpoint.checkpointId && (
            <Badge variant="outline" className="font-mono text-[10px]">
              {checkpoint.checkpointId}
            </Badge>
          )}
        </CardTitle>
        <p className="text-xs leading-relaxed text-muted-foreground">
          {t("checkpoint.description")}
        </p>
      </CardHeader>
      <Separator />
      <CardContent className="space-y-4 pt-5">
        {checkpoint.question && (
          <p className="text-sm font-medium leading-relaxed text-foreground/90">
            {checkpoint.question}
          </p>
        )}

        {/* Evidence — collapsed by default, plain text (no markdown parsing) */}
        <div className="space-y-2">
          <CollapsibleSection
            titleKey="checkpoint.contradictionMap"
            body={checkpoint.contradictionMap}
          />
          <CollapsibleSection
            titleKey="checkpoint.synthesis"
            body={checkpoint.synthesis}
          />
        </div>

        {/* Document audit */}
        <div className="rounded-md border border-border/60 bg-secondary/30 p-3">
          <div className="flex items-center gap-2">
            {audit === null ? (
              <ShieldQuestion className="h-4 w-4 text-muted-foreground" />
            ) : audit.passed ? (
              <ShieldCheck className="h-4 w-4 text-success" />
            ) : (
              <ShieldAlert className="h-4 w-4 text-destructive" />
            )}
            <span className="text-sm font-medium">{t("checkpoint.audit")}</span>
            <Badge
              variant={
                audit === null ? "muted" : audit.passed ? "success" : "danger"
              }
              className="ml-auto font-mono text-[10px]"
            >
              {audit === null
                ? t("checkpoint.notRun")
                : audit.passed
                  ? t("checkpoint.pass")
                  : t("checkpoint.fail")}
            </Badge>
          </div>
          {gaps.length > 0 && (
            <div className="mt-2.5 border-t border-border/40 pt-2.5">
              <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                {t("checkpoint.gaps")}
              </h3>
              <ul className="flex flex-col gap-1">
                {gaps.map((gap, i) => (
                  <li key={i} className="flex gap-2 text-xs text-foreground/90">
                    <span className="shrink-0 text-warning">•</span>
                    <span className="break-words leading-relaxed">{gap}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Open questions */}
        {checkpoint.openQuestions.length > 0 && (
          <div className="space-y-1.5">
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              {t("checkpoint.openQuestions")}
            </h3>
            <ul className="flex flex-col gap-1">
              {checkpoint.openQuestions.map((q, i) => (
                <li key={i} className="flex gap-2 text-xs text-foreground/90">
                  <span className="shrink-0 tabular-nums text-primary/60">
                    {i + 1}.
                  </span>
                  <span className="break-words leading-relaxed">{q}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <Separator />

        {/* Operator decision */}
        <div className="space-y-3">
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={t("checkpoint.feedbackPlaceholder")}
            disabled={busy}
            className="min-h-[72px] resize-y border-border/70 bg-background/60 text-sm"
            aria-label={t("checkpoint.feedback")}
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button
              onClick={() => handle("continue")}
              disabled={busy}
              className="gap-2"
            >
              {pending === "continue" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ShieldCheck className="h-4 w-4" />
              )}
              {t("checkpoint.continue")}
            </Button>
            <Button
              variant="outline"
              onClick={() => handle("feedback")}
              disabled={busy || note.trim().length === 0}
              className="gap-2"
            >
              {pending === "feedback" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              {t("checkpoint.feedback")}
            </Button>
            <Button
              variant="ghost"
              onClick={() => handle("exit")}
              disabled={busy}
              className="ml-auto gap-2 text-muted-foreground hover:text-destructive"
            >
              {pending === "exit" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Square className="h-4 w-4" />
              )}
              {t("checkpoint.stop")}
            </Button>
          </div>
          {busy && (
            <p className="text-xs text-muted-foreground">
              {t("checkpoint.updated")}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

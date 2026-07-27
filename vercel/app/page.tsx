"use client";

import { useState } from "react";
import { AlertCircle, Loader2, RotateCcw, Search, Square } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { FinalResults } from "@/components/final-results";
import { Header } from "@/components/header";
import { LiveOutput } from "@/components/live-output";
import { StageStepper } from "@/components/stage-stepper";
import { useResearch } from "@/hooks/use-research";
import { useLanguage } from "@/lib/i18n";

export default function Home() {
  const { t } = useLanguage();
  const [question, setQuestion] = useState("");
  const research = useResearch();

  const {
    status,
    currentStage,
    stageDescription,
    findings,
    challenge,
    brief,
    finalFindings,
    confidence,
    error,
    start,
    cancel,
    reset,
    statusMessage,
    savedQuestion,
  } = research;

  // Restore saved question on reconnect
  const displayQuestion = question || savedQuestion || "";

  const isBusy =
    status === "creating" || status === "starting" || status === "streaming";
  const isComplete = status === "complete";
  const showError = status === "error";

  const canSubmit = question.trim().length > 0 && !isBusy;

  async function handleSubmit() {
    if (!canSubmit) return;
    await start(question);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <main className="flex flex-col gap-8">
      {/* Header (brand + toggles) */}
      <Header />

      {/* Input */}
      <Card>
        <CardContent className="p-4 sm:p-5">
          <div className="flex flex-col gap-3">
            <Textarea
              value={displayQuestion}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("input.example")}
              disabled={isBusy}
              className="min-h-[96px] resize-y border-border/70 bg-background/60 text-base"
              aria-label={t("input.placeholder")}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button
                onClick={handleSubmit}
                disabled={!canSubmit}
                className="gap-2"
              >
                {isBusy ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t("input.researching")}
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    {t("input.start")}
                  </>
                )}
              </Button>
              {isBusy && (
                <Button variant="outline" onClick={cancel} className="gap-2">
                  <Square className="h-4 w-4" />
                  {t("input.cancel")}
                </Button>
              )}
              <span className="text-xs text-muted-foreground">
                {t("input.press")}{" "}
                <kbd className="rounded border border-border bg-secondary px-1 py-0.5 font-mono text-[10px]">
                  ⌘/Ctrl
                </kbd>{" "}
                +{" "}
                <kbd className="rounded border border-border bg-secondary px-1 py-0.5 font-mono text-[10px]">
                  Enter
                </kbd>
              </span>
              {(isComplete || showError) && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={reset}
                  className="ml-auto gap-1.5"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  {t("input.newResearch")}
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {showError && error && (
        <div className="flex items-start gap-2.5 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-medium">{t("error.failed")}</p>
            <p className="mt-0.5 text-destructive/80">{error}</p>
          </div>
        </div>
      )}

      {/* Stage progress — visible after submitting */}
      {currentStage !== null && (
        <Card>
          <CardContent className="p-4 sm:p-5">
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">{t("pipeline.label")}</span>
              <Badge variant="outline" className="font-mono text-[10px]">
                {t("pipeline.stage")} {currentStage}
              </Badge>
              {stageDescription && (
                <span className="text-xs text-muted-foreground">
                  {stageDescription}
                </span>
              )}
            </div>
            <StageStepper
              currentStage={currentStage}
              isComplete={isComplete}
            />
          </CardContent>
        </Card>
      )}

      {/* Live output — visible while streaming or once complete */}
      {(isBusy || isComplete) && !showError && (
        <LiveOutput
          status={status}
          findings={findings}
          challenge={challenge}
          statusMessage={statusMessage}
        />
      )}

      {/* Final results */}
      {isComplete && (
        <FinalResults
          brief={brief}
          finalFindings={finalFindings}
          confidence={confidence}
        />
      )}

      {/* Footer */}
      <footer className="mt-2 border-t border-border/60 pt-4 text-center text-xs text-muted-foreground">
        <p>
          {t("brand.title")} · {t("footer.builtOn")}{" "}
          <a
            href="https://github.com/lsdefine/GenericAgent"
            target="_blank"
            rel="noreferrer"
            className="text-primary hover:underline"
          >
            GenericAgent
          </a>{" "}
          +{" "}
          <a
            href="https://arxiv.org/abs/2402.14207"
            target="_blank"
            rel="noreferrer"
            className="text-primary hover:underline"
          >
            STORM
          </a>
        </p>
      </footer>
    </main>
  );
}
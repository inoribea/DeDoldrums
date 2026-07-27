"use client";

import { useState } from "react";
import { AlertCircle, Loader2, RotateCcw, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { FinalResults } from "@/components/final-results";
import { LiveOutput } from "@/components/live-output";
import { StageStepper } from "@/components/stage-stepper";
import { useResearch } from "@/hooks/use-research";

const EXAMPLE_PLACEHOLDER =
  "What is the real timeline for quantum computing to break RSA?";

export default function Home() {
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
    reset,
  } = research;

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
      {/* Hero */}
      <header className="flex flex-col gap-2 pt-2">
        <div className="flex items-center gap-2">
          <span className="inline-block h-2 w-2 rounded-full bg-primary" />
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
            hybrid STORM
          </span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          ResearchAgent
        </h1>
        <p className="max-w-xl text-sm text-muted-foreground sm:text-base">
          Multi-perspective research powered by hybrid STORM methodology.
          Dynamic lens discovery, contradiction mapping, adversarial gate,
          peer review.
        </p>
      </header>

      {/* Input */}
      <Card>
        <CardContent className="p-4 sm:p-5">
          <div className="flex flex-col gap-3">
            <Textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={EXAMPLE_PLACEHOLDER}
              disabled={isBusy}
              className="min-h-[96px] resize-y border-border/70 bg-background/60 text-base"
              aria-label="Research question"
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
                    Researching…
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    Start research
                  </>
                )}
              </Button>
              <span className="text-xs text-muted-foreground">
                Press{" "}
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
                  New research
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
            <p className="font-medium">Research failed</p>
            <p className="mt-0.5 text-destructive/80">{error}</p>
          </div>
        </div>
      )}

      {/* Stage progress — visible after submitting */}
      {currentStage !== null && (
        <Card>
          <CardContent className="p-4 sm:p-5">
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">Pipeline</span>
              <Badge variant="outline" className="font-mono text-[10px]">
                stage {currentStage}
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
          ResearchAgent · Built on{" "}
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
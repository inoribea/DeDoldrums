"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { FinalFinding, ResearchComplete } from "@/lib/types";

interface FinalResultsProps {
  brief: string | null;
  finalFindings: FinalFinding[] | null;
  confidence: ResearchComplete["confidence"] | null;
}

function confidenceVariant(
  c: number,
): "success" | "warning" | "danger" {
  if (c >= 7) return "success";
  if (c >= 4) return "warning";
  return "danger";
}

function numericConfidence(c: unknown): number | null {
  if (typeof c === "number" && Number.isFinite(c)) return c;
  return null;
}

function findingText(f: FinalFinding): string {
  return f.content ?? f.summary ?? "";
}

export function FinalResults({
  brief,
  finalFindings,
  confidence,
}: FinalResultsProps) {
  if (!brief && (!finalFindings || finalFindings.length === 0)) return null;

  const overall = numericConfidence(confidence);

  return (
    <Card className="animate-fade-in-up">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          Research brief
          {overall !== null && (
            <Badge
              variant={confidenceVariant(overall)}
              className="ml-1 font-mono"
            >
              confidence {overall}/10
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <Separator />
      <CardContent className="space-y-5 pt-5">
        {brief && (
          <div className="prose prose-invert max-w-none prose-headings:font-semibold prose-headings:tracking-tight prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg prose-p:leading-relaxed prose-p:text-foreground/90 prose-strong:text-foreground prose-code:rounded prose-code:bg-secondary prose-code:px-1.5 prose-code:py-0.5 prose-code:text-[0.85em] prose-code:font-mono prose-code:text-primary prose-pre:bg-secondary prose-pre:text-foreground/90 prose-a:text-primary prose-li:text-foreground/90 prose-blockquote:border-primary prose-blockquote:text-muted-foreground">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {brief}
            </ReactMarkdown>
          </div>
        )}

        {finalFindings && finalFindings.length > 0 && (
          <div className="space-y-2.5">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              Key findings
            </h3>
            <ul className="space-y-2">
              {finalFindings.map((f, i) => {
                const text = findingText(f);
                const fc = numericConfidence(f.confidence);
                return (
                  <li
                    key={i}
                    className={cn(
                      "rounded-md border border-border/60 bg-secondary/30 p-3",
                    )}
                  >
                    <div className="mb-1.5 flex items-center gap-2">
                      <Badge variant="muted" className="font-mono">
                        #{i + 1}
                      </Badge>
                      {fc !== null && (
                        <Badge
                          variant={confidenceVariant(fc)}
                          className="font-mono"
                        >
                          {fc}/10
                        </Badge>
                      )}
                      {f.stage !== undefined && (
                        <Badge variant="outline" className="font-mono text-[10px]">
                          stage {String(f.stage)}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap break-words">
                      {text}
                    </p>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
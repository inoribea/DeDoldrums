"use client";

import { LanguageToggle } from "@/components/language-toggle";
import { ThemeToggle } from "@/components/theme-toggle";
import { useLanguage } from "@/lib/i18n";

/**
 * Top-of-page header: brand block on the left, language + theme
 * toggles on the right. Matches the existing minimal header style.
 */
export function Header() {
  const { t } = useLanguage();

  return (
    <header className="flex flex-col gap-4 pt-2 sm:flex-row sm:items-start sm:justify-between">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-block h-2 w-2 rounded-full bg-primary" />
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
            {t("brand.tag")}
          </span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          {t("brand.title")}
        </h1>
        <p className="max-w-xl text-sm text-muted-foreground sm:text-base">
          {t("brand.subtitle")}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-2 sm:pt-1">
        <LanguageToggle />
        <ThemeToggle />
      </div>
    </header>
  );
}
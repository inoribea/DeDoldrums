"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/i18n";

/**
 * Cycles auto → light → dark → auto.
 * Renders a stable placeholder until mounted to avoid hydration mismatch
 * (next-themes resolves the theme on the client only).
 */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const { t } = useLanguage();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <Button
        variant="outline"
        size="icon"
        aria-label={t("toggle.theme.auto")}
        title={t("toggle.theme.auto")}
        // Reserve layout space; no icon flash.
        className="h-9 w-9"
      />
    );
  }

  const isAuto = theme === "system" || theme === undefined;
  const isLight = theme === "light";
  const isDark = theme === "dark";

  const next = isAuto ? "light" : isLight ? "dark" : "system";
  const label = isAuto
    ? t("toggle.theme.auto")
    : isLight
      ? t("toggle.theme.light")
      : t("toggle.theme.dark");

  return (
    <Button
      variant="outline"
      size="icon"
      onClick={() => setTheme(next)}
      aria-label={label}
      title={label}
      className="h-9 w-9"
    >
      {isAuto && <Monitor className="h-4 w-4" />}
      {isLight && <Sun className="h-4 w-4" />}
      {isDark && <Moon className="h-4 w-4" />}
    </Button>
  );
}
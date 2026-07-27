"use client";

import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/i18n";

/**
 * Toggles between zh and en. Shows "中" when current is English
 * (i.e. "switch to Chinese"), "EN" when current is Chinese.
 */
export function LanguageToggle() {
  const { language, toggleLanguage, t } = useLanguage();

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={toggleLanguage}
      aria-label={t("toggle.language")}
      title={t("toggle.language")}
      className="h-9 min-w-9 px-2 font-mono text-xs"
    >
      {language === "en" ? "中" : "EN"}
    </Button>
  );
}
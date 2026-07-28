"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Language = "zh" | "en";

/**
 * All UI strings keyed by a stable identifier.
 * Add new keys here in BOTH dictionaries — the type enforces completeness.
 */
export interface Translations {
  // Brand / hero
  "brand.tag": string;
  "brand.title": string;
  "brand.subtitle": string;

  // Input card
  "input.placeholder": string;
  "input.example": string;
  "input.start": string;
  "input.researching": string;
"input.cancel": string;
  "input.press": string;
  "input.newResearch": string;

  // Error
  "error.failed": string;

  // Pipeline
  "pipeline.label": string;
  "pipeline.stage": string;

  // Stage labels & descriptions
  "stage.-1.label": string;
  "stage.-1.description": string;
  "stage.0.label": string;
  "stage.0.description": string;
  "stage.1.label": string;
  "stage.1.description": string;
  "stage.2.label": string;
  "stage.2.description": string;
  "stage.3.label": string;
  "stage.3.description": string;
  "stage.3.5.label": string;
  "stage.3.5.description": string;
  "stage.3.5.gate": string;
  "stage.4.label": string;
  "stage.4.description": string;

  // Live output
  "live.title": string;
  "live.waiting": string;
"live.thinking": string;
  "live.idle": string;
  "live.adversarialGate": string;

  // Final results
  "results.title": string;
  "results.confidence": string;
  "results.keyFindings": string;

  // Finding item
  "finding.showMore": string;
  "finding.showLess": string;

  // Footer
  "footer.builtOn": string;

  // Toggles
  "toggle.language": string;
  "toggle.theme.auto": string;
  "toggle.theme.light": string;
  "toggle.theme.dark": string;
}

const en: Translations = {
  "brand.tag": "Break the doldrums.",
  "brand.title": "DeDoldrums",
  "brand.subtitle":
    "Multi-perspective research powered by hybrid STORM methodology. Dynamic lens discovery, contradiction mapping, adversarial gate, peer review.",

  "input.placeholder": "Ask a research question...",
  "input.example":
    "What is the real timeline for quantum computing to break RSA?",
  "input.start": "Start research",
  "input.researching": "Researching…",
"input.cancel": "Stop",
  "input.press": "Press",
  "input.newResearch": "New research",

  "error.failed": "Research failed",

  "pipeline.label": "Pipeline",
  "pipeline.stage": "stage",

  "stage.-1.label": "Initializing",
  "stage.-1.description": "Spinning up the research session",
  "stage.0.label": "Discovering Perspectives",
  "stage.0.description": "Dynamic lens discovery from search results",
  "stage.1.label": "Multi-Perspective Scan",
  "stage.1.description": "Independent exploration across lenses",
  "stage.2.label": "Contradiction Mapping",
  "stage.2.description": "Conflicts, consensus, blind spots",
  "stage.3.label": "Synthesis",
  "stage.3.description": "Cross-lens connections into a structured brief",
  "stage.3.5.label": "Adversarial Gate",
  "stage.3.5.description":
    "Generator-Verifier pressure test on every finding",
  "stage.3.5.gate": "gate",
  "stage.4.label": "Peer Review",
  "stage.4.description": "Confidence scores, bias check, missing angles",

"live.title": "Live output",
"live.waiting": "Waiting for the first finding…",
"live.thinking": "Thinking",
"live.idle": "Findings will appear here as the agent researches.",
  "live.adversarialGate": "Adversarial gate",

  "results.title": "Research brief",
  "results.confidence": "confidence",
  "results.keyFindings": "Key findings",

  "finding.showMore": "Show more",
  "finding.showLess": "Show less",

  "footer.builtOn": "Built on",

  "toggle.language": "Switch language",
  "toggle.theme.auto": "Auto",
  "toggle.theme.light": "Light",
  "toggle.theme.dark": "Dark",
};

const zh: Translations = {
  "brand.tag": "Break the doldrums.",
  "brand.title": "DeDoldrums",
  "brand.subtitle":
    "基于混合 STORM 方法论的多视角研究。动态视角发现、矛盾映射、对抗验证闸门、同行评审。",

  "input.placeholder": "输入研究问题...",
  "input.example": "量子计算对 RSA 的真实威胁时间线是什么？",
  "input.start": "开始研究",
  "input.researching": "研究进行中…",
"input.cancel": "停止",
  "input.press": "按",
  "input.newResearch": "重新研究",

  "error.failed": "研究失败",

  "pipeline.label": "流水线",
  "pipeline.stage": "阶段",

  "stage.-1.label": "初始化",
  "stage.-1.description": "正在启动研究会话",
  "stage.0.label": "发现视角",
  "stage.0.description": "从搜索结果中动态发现研究视角",
  "stage.1.label": "多视角扫描",
  "stage.1.description": "跨视角的独立探索",
  "stage.2.label": "矛盾映射",
  "stage.2.description": "冲突、共识、盲点",
  "stage.3.label": "综合合成",
  "stage.3.description": "跨视角连接形成结构化简报",
  "stage.3.5.label": "对抗验证闸门",
  "stage.3.5.description": "对每条发现进行生成器-验证器压力测试",
  "stage.3.5.gate": "闸门",
  "stage.4.label": "同行评审",
  "stage.4.description": "置信度评分、偏差检查、遗漏角度",

"live.title": "实时输出",
"live.waiting": "等待第一条发现…",
"live.thinking": "思考中",
"live.idle": "发现将在此处显示，随研究进行实时更新。",
  "live.adversarialGate": "对抗验证闸门",

  "results.title": "研究简报",
  "results.confidence": "置信度",
  "results.keyFindings": "关键发现",

  "finding.showMore": "展开",
  "finding.showLess": "收起",

  "footer.builtOn": "基于",

  "toggle.language": "切换语言",
  "toggle.theme.auto": "自动",
  "toggle.theme.light": "浅色",
  "toggle.theme.dark": "深色",
};

const DICTIONARIES: Record<Language, Translations> = { en, zh };

const STORAGE_KEY = "dedoldrums-lang";

interface LanguageContextValue {
  language: Language;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
  t: (key: keyof Translations) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

function readStoredLanguage(): Language | null {
  if (typeof window === "undefined") return null;
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    if (v === "zh" || v === "en") return v;
  } catch {
    /* ignore */
  }
  return null;
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  // Default to English on the server; sync from localStorage on mount.
  const [language, setLanguageState] = useState<Language>("en");

  useEffect(() => {
    const stored = readStoredLanguage();
    if (stored) setLanguageState(stored);
  }, []);

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang);
    try {
      window.localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      /* ignore */
    }
  }, []);

  const toggleLanguage = useCallback(() => {
    setLanguageState((prev) => {
      const next: Language = prev === "en" ? "zh" : "en";
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const t = useCallback(
    (key: keyof Translations) => DICTIONARIES[language][key] ?? key,
    [language],
  );

  const value = useMemo<LanguageContextValue>(
    () => ({ language, setLanguage, toggleLanguage, t }),
    [language, setLanguage, toggleLanguage, t],
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return ctx;
}

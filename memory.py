"""Flat-file L0-L4 layered memory for research sessions."""

import json
import os
import re
import threading
from datetime import datetime
from typing import Any, Optional


class MemoryStore:
    """L0-L4 layered memory store adapted for research context."""

    _lock_guard = threading.Lock()
    _path_locks: dict[str, threading.RLock] = {}

    def __init__(self, base_path: str):
        self.base = base_path
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for directory in ("", "L2_domain", "L3_thinking_sops", "L4_archive"):
            os.makedirs(os.path.join(self.base, directory), exist_ok=True)

    @classmethod
    def _lock_for(cls, path: str) -> threading.RLock:
        """Return one lock per shared storage path within this process."""
        normalized_path = os.path.abspath(path)
        with cls._lock_guard:
            if normalized_path not in cls._path_locks:
                cls._path_locks[normalized_path] = threading.RLock()
            return cls._path_locks[normalized_path]

    @staticmethod
    def _read_json(path: str, default: Any) -> Any:
        """Read JSON storage, treating missing or malformed files as empty."""
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return default

    # ── L0: Meta rules ──
    def load_principles(self) -> str:
        path = os.path.join(self.base, "L0_principles.md")
        try:
            with open(path, "r", encoding="utf-8") as file:
                return file.read()
        except OSError:
            return self._default_principles()

    @staticmethod
    def _default_principles() -> str:
        return """# 研究元规则

## 好研究的标准
- 至少从 3 个不同透镜审视同一问题
- 对每个重要断言进行对抗性挑战
- 区分「事实」（有可靠来源）和「推断」（基于事实的推理）
- 标注每个结论的置信度（1-10）

## 何时停止探索
- 3 个以上透镜给出高度一致的结论
- 新探索不再产生与已有发现实质性不同的信息
- 已达到分配的时间/轮次预算

## 判断置信度
- 8-10: 多个独立来源 + 多个透镜一致确认
- 5-7: 有来源但未交叉验证，或透镜间有细微分歧
- 1-4: 基于类推或单一来源，或透镜间存在显著矛盾
"""

    # ── L1: Pattern index ──
    def update_index(self, category: str, insight: str, trigger: str) -> None:
        path = os.path.join(self.base, "L1_pattern_index.json")
        with self._lock_for(path):
            index = self._read_json(path, {})
            if not isinstance(index, dict):
                index = {}

            key = " ".join(self._extract_keywords(trigger))
            if key not in index:
                index[key] = []
            index[key].append(
                {
                    "category": category,
                    "trigger": trigger,
                    "insight_summary": insight[:200],
                    "timestamp": datetime.now().isoformat(),
                }
            )

            with open(path, "w", encoding="utf-8") as file:
                json.dump(index, file, ensure_ascii=False, indent=2)

    def query_index(self, question: str) -> list[dict[str, Any]]:
        """Match relevant thinking patterns against a research question."""
        path = os.path.join(self.base, "L1_pattern_index.json")
        with self._lock_for(path):
            index = self._read_json(path, {})
        if not isinstance(index, dict):
            return []

        keywords = self._extract_keywords(question)
        matches: list[dict[str, Any]] = []
        for key, entries in index.items():
            if any(keyword in key for keyword in keywords) and isinstance(entries, list):
                matches.extend(entry for entry in entries if isinstance(entry, dict))
        return matches[:5]

    # ── L2: Domain knowledge ──
    def save_domain_knowledge(self, insight: str) -> None:
        topic = self._extract_topic(insight)
        path = os.path.join(self.base, "L2_domain", f"{self._safe_filename(topic)}.md")
        entry = f"\n\n---\n## {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{insight}\n"
        with self._lock_for(path):
            with open(path, "a", encoding="utf-8") as file:
                file.write(entry)

    # ── L3: Thinking SOPs ──
    def save_sop(self, insight: str, trigger: str) -> None:
        path = os.path.join(self.base, "L3_thinking_sops", "patterns.md")
        entry = f"""\n\n## {datetime.now().strftime('%Y-%m-%d')}

**触发条件**: {trigger}

**思维模式**:
{insight}

**使用记录**: 0 次
"""
        with self._lock_for(path):
            with open(path, "a", encoding="utf-8") as file:
                file.write(entry)

    def save_pitfall(self, insight: str) -> None:
        path = os.path.join(self.base, "L3_thinking_sops", "pitfalls.md")
        entry = f"""\n\n## {datetime.now().strftime('%Y-%m-%d')}

**常见陷阱**:
{insight}
"""
        with self._lock_for(path):
            with open(path, "a", encoding="utf-8") as file:
                file.write(entry)

    # ── L4: Session archive ──
    def archive_session(self, question: str, findings: list[Any]) -> None:
        session_dir = os.path.join(
            self.base,
            "L4_archive",
            f"{datetime.now().strftime('%Y-%m-%d')}_{self._safe_filename(question[:50])}",
        )
        os.makedirs(session_dir, exist_ok=True)
        path = os.path.join(session_dir, "findings.json")
        with self._lock_for(path):
            with open(path, "w", encoding="utf-8") as file:
                json.dump(findings, file, ensure_ascii=False, indent=2)

    def _session_dir(self, question: str) -> str:
        """Return the L4 archive directory used by this session's artifacts."""
        return os.path.join(
            self.base,
            "L4_archive",
            f"{datetime.now().strftime('%Y-%m-%d')}_{self._safe_filename(question[:50])}",
        )

    def save_stage_artifact(self, question: str, stage_name: str, content: str) -> str:
        """Persist a stage artifact (contradiction map, synthesis, …) to disk.

        P6: artifacts must be on disk BEFORE any context truncation, so a
        crash/interrupt can recover the full stage outputs without re-running
        completed stages. Returns the written path.
        """
        stage_dir = os.path.join(self._session_dir(question), "stages")
        os.makedirs(stage_dir, exist_ok=True)
        path = os.path.join(stage_dir, f"{self._safe_filename(stage_name)}.md")
        with self._lock_for(path):
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)
        return path

    def load_stage_artifacts(self, question: str) -> dict[str, str]:
        """Recover persisted stage artifacts for a session (crash recovery)."""
        stage_dir = os.path.join(self._session_dir(question), "stages")
        artifacts: dict[str, str] = {}
        if not os.path.isdir(stage_dir):
            return artifacts
        for filename in sorted(os.listdir(stage_dir)):
            if not filename.endswith(".md"):
                continue
            path = os.path.join(stage_dir, filename)
            try:
                with self._lock_for(path):
                    with open(path, "r", encoding="utf-8") as file:
                        artifacts[filename[:-3]] = file.read()
            except OSError:
                continue
        return artifacts

    # ── Cross-layer search ──
    def search(
        self,
        query: str,
        layers: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """Search layered memory by keyword, returning no more than ten results."""
        results: list[dict[str, Any]] = []

        index_matches = self.query_index(query)
        if index_matches:
            results.append({"layer": "L1", "type": "pattern_index", "matches": index_matches})

        keywords = self._extract_keywords(query)
        for layer in layers or ["L2_domain", "L3_thinking_sops", "L4_archive"]:
            layer_path = os.path.join(self.base, layer)
            if not os.path.isdir(layer_path):
                continue
            for root, _, files in os.walk(layer_path):
                for filename in files:
                    if not filename.endswith((".md", ".json")):
                        continue
                    path = os.path.join(root, filename)
                    try:
                        with self._lock_for(path):
                            with open(path, "r", encoding="utf-8") as file:
                                content = file.read()
                    except OSError:
                        continue
                    if any(keyword.lower() in content.lower() for keyword in keywords):
                        results.append(
                            {"layer": layer, "file": filename, "snippet": content[:500]}
                        )
                        if len(results) >= 10:
                            return results
        return results[:10]

    def get_path(self, category: str) -> str:
        paths = {
            "domain_knowledge": os.path.join(self.base, "L2_domain"),
            "thinking_pattern": os.path.join(self.base, "L3_thinking_sops"),
            "pitfall": os.path.join(self.base, "L3_thinking_sops", "pitfalls.md"),
        }
        return paths.get(category, self.base)

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Extract keywords longer than two characters for simple matching."""
        words = re.findall(r"\w+", text.lower())
        return [word for word in words if len(word) > 2]

    @staticmethod
    def _extract_topic(text: str) -> str:
        return " ".join(text.split()[:5])[:50]

    @staticmethod
    def _safe_filename(text: str) -> str:
        return re.sub(r"[^\w\s-]", "", text)[:80].strip().replace(" ", "_")

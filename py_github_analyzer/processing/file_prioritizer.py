# py_github_analyzer/processing/file_prioritizer.py
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import Config
from ..logger import AnalyzerLogger
from .language_detector import LanguageDetector


class FilePrioritizer:
    def __init__(self, logger: Optional[AnalyzerLogger] = None):
        self._logger = logger or AnalyzerLogger()
        self._language_detector = LanguageDetector()
        self._weights = {
            "language_match": 200,
            "importance_score": 100,
            "complexity": 50,
            "size_factor": 30,
            "depth_penalty": 25,
            "framework_bonus": 150,
            "special_file_bonus": 100,
        }

    def prioritize_files(
        self,
        files: List[Dict[str, Any]],
        target_language: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not files:
            return []
        context = context or {}
        if not target_language:
            target_language = self._language_detector.detect_primary_language(files)
        prioritized = []
        for file_info in files:
            try:
                prioritized.append(self._calculate_priority_score(file_info, target_language, context))
            except Exception as e:
                self._logger.warning(f"Error prioritizing {file_info.get('path', 'unknown')}: {e}")
                file_info["priority"] = 100
                prioritized.append(file_info)
        prioritized.sort(key=lambda x: x.get("priority", 100), reverse=True)
        return prioritized

    def _calculate_priority_score(
        self, file_info: Dict[str, Any], target_language: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        path = file_info.get("path", "")
        size = file_info.get("size", 0)
        content = file_info.get("content", "")
        enhanced = file_info.copy()
        if not path:
            enhanced["priority"] = 50
            return enhanced
        filename = Path(path).name.lower()
        file_ext = Path(path).suffix.lower()
        depth = len(Path(path).parts) - 1
        category = Config.get_file_category(filename)
        base_priority = self._base_priority_by_category(category)
        detected_lang = self._language_detector.detect_language_by_extension(filename)
        if detected_lang == "unknown" and content:
            detected_lang = self._language_detector.detect_language_by_content(content, filename)
        lang_bonus = self._weights["language_match"] if detected_lang == target_language else (
            self._weights["language_match"] // 2 if detected_lang in ("python", "javascript", "typescript", "java") else 0
        )
        importance_bonus = self._importance_bonus(filename, path)
        framework_bonus = self._framework_bonus(content, detected_lang)
        complexity_bonus = 0
        if content and detected_lang in ("python", "javascript", "typescript", "java", "cpp"):
            complexity_score = self._language_detector.calculate_complexity(content, detected_lang)
            enhanced["complexity"] = complexity_score
            complexity_bonus = min(int(complexity_score * self._weights["complexity"]), 200)
        size_factor = self._size_factor(size)
        depth_penalty = min(depth * self._weights["depth_penalty"], 150)
        content_bonus = self._content_quality_bonus(content, file_ext)
        final_priority = max(
            base_priority + lang_bonus + importance_bonus + framework_bonus
            + complexity_bonus + size_factor + content_bonus - depth_penalty,
            10,
        )
        enhanced["priority"] = int(final_priority)
        enhanced["language"] = detected_lang
        enhanced["priority_breakdown"] = {
            "base": base_priority, "language": lang_bonus, "importance": importance_bonus,
            "framework": framework_bonus, "complexity": complexity_bonus, "size": size_factor,
            "content": content_bonus, "depth_penalty": -depth_penalty,
        }
        return enhanced

    def _base_priority_by_category(self, category: str) -> int:
        return {
            "python": 800, "javascript": 750, "typescript": 750, "java": 700,
            "cpp": 650, "csharp": 650, "go": 650, "rust": 650,
            "php": 600, "ruby": 600, "swift": 580, "kotlin": 580, "scala": 570,
            "dockerfile": 900, "makefile": 800, "config": 550, "yaml": 500,
            "json": 500, "xml": 400, "markdown": 400, "text": 300, "binary": 0, "skip": 0,
        }.get(category, 200)

    def _importance_bonus(self, filename: str, full_path: str) -> int:
        importance_patterns = {
            "readme.md": 300, "readme.txt": 250, "changelog.md": 150, "license": 100,
            "contributing.md": 100, "dockerfile": 400, "docker-compose.yml": 350,
            "makefile": 300, "package.json": 250, "requirements.txt": 200,
            "setup.py": 200, "pyproject.toml": 200, "cargo.toml": 200, "go.mod": 200,
            "pom.xml": 180, "build.gradle": 180, ".gitignore": 100,
            "main.py": 300, "main.js": 300, "index.js": 300, "index.html": 250,
            "app.py": 300, "server.py": 250, "manage.py": 200, "config.py": 180,
            "settings.py": 200, "wsgi.py": 150, "asgi.py": 150,
        }
        if filename in importance_patterns:
            return importance_patterns[filename]
        bonus = 0
        if re.search(r"\b(main|index|app|server)\b", filename):
            bonus += 200
        if re.search(r"\b(test|spec)s?\b", filename) and "node_modules" not in full_path:
            bonus += 50
        if re.search(r"\b(config|settings|env)\b", filename):
            bonus += 100
        if re.search(r"\b(api|endpoint|route|view)s?\b", filename):
            bonus += 150
        if re.search(r"\b(model|schema|entity)s?\b", filename):
            bonus += 120
        return bonus

    def _framework_bonus(self, content: str, language: str) -> int:
        if not content:
            return 0
        content_sample = content[:2000]
        patterns = {
            r"\bfrom django\b|\bimport django\b": 150,
            r"\bfrom flask\b|\bFlask\(": 150,
            r"\bfrom fastapi\b|\bFastAPI\(": 150,
            r"\bfrom ['\"]react['\"]|\bimport.*react": 150,
            r"\bfrom ['\"]vue['\"]|\bVue\.": 150,
            r"\b@angular\b|\bAngular": 150,
            r"\bexpress\(\)|\brequire.*express": 120,
            r"\bnext/|\bgetStaticProps": 130,
            r"\bwebpack\b|\brollup\b|\bvite\b": 100,
            r"\bbabel\b|\b@babel": 80,
            r"\bjest\b|\bcypress\b": 70,
            r"\bsqlalchemy\b|\bdjango\.db": 100,
            r"\bmongoose\b|\bmongodb": 90,
            r"\bexport default\b|\bmodule\.exports": 50,
            r"\bclass\s+\w+.*Component": 100,
        }
        bonus = sum(v for p, v in patterns.items() if re.search(p, content_sample, re.IGNORECASE))
        return min(bonus, 300)

    def _size_factor(self, size: int) -> int:
        if size == 0:
            return -50
        if size > Config.MAX_FILE_SIZE:
            return -200
        if size < 100:
            return -30
        if size <= 5000:
            return 30
        if size <= 20000:
            return 10
        if size <= 50000:
            return -10
        return -30

    def _content_quality_bonus(self, content: str, file_ext: str) -> int:
        if not content:
            return 0
        bonus = 20 if len(content.strip()) > 50 else 0
        if file_ext in (".py", ".js", ".ts", ".java", ".cpp"):
            total = len(content.splitlines())
            if total > 0:
                comment_lines = len(re.findall(r"^\s*#|^\s*//|/\*.*?\*/", content, re.MULTILINE))
                if comment_lines / total > 0.1:
                    bonus += 30
        if re.search(r"\b(class|function|def|interface|struct)\s+\w+", content, re.IGNORECASE):
            bonus += 40
        if re.search(r"\b(import|include|require|from)\s+", content, re.IGNORECASE):
            bonus += 20
        return bonus

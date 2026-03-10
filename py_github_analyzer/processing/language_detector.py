# py_github_analyzer/processing/language_detector.py
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


class LanguageDetector:
    def __init__(self):
        self.framework_patterns = {
            "python": {
                "django": [r"from django", r"import django", r"DJANGO_SETTINGS_MODULE", r"manage\.py", r"settings\.py"],
                "flask": [r"from flask", r"import flask", r"Flask\(__name__\)", r"@app\.route"],
                "fastapi": [r"from fastapi", r"import fastapi", r"FastAPI\(", r"@app\.(get|post|put|delete)"],
                "pytest": [r"import pytest", r"def test_", r"@pytest\.", r"conftest\.py"],
            },
            "javascript": {
                "react": [r"import.*react", r"from.*react", r"React\.", r"jsx|tsx", r"useState|useEffect"],
                "vue": [r"import.*vue", r"from.*vue", r"Vue\.", r"<template>", r"\.vue"],
                "angular": [r"@angular", r"@Component", r"@Injectable", r"@NgModule"],
                "express": [r"require.*express", r"import.*express", r"app\.get|app\.post", r"express\(\)"],
                "nextjs": [r"next/", r"getStaticProps", r"getServerSideProps", r"next\.config"],
            },
            "typescript": {
                "angular": [r"@angular", r"@Component", r"@Injectable"],
                "nestjs": [r"@nestjs", r"@Controller", r"@Injectable", r"@Module"],
            },
        }

        self.code_extensions = {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".h", ".hpp",
            ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".scala", ".clj",
            ".hs", ".ml", ".elm", ".dart", ".lua", ".r", ".m", ".sh", ".ps1", ".bat",
        }
        self.data_extensions = {
            ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg",
            ".csv", ".tsv", ".sql", ".log", ".txt",
        }
        self.markup_extensions = {".html", ".htm", ".xhtml", ".xml", ".svg", ".md", ".rst", ".tex"}

    def detect_language_by_extension(self, filename: str) -> str:
        if not filename:
            return "unknown"
        ext = Path(filename).suffix.lower()
        extension_map = {
            ".py": "python", ".pyx": "python", ".pyi": "python",
            ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
            ".ts": "typescript", ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp", ".cxx": "cpp", ".cc": "cpp", ".c": "cpp",
            ".hpp": "cpp", ".h": "cpp", ".hxx": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".php": "php", ".phtml": "php",
            ".rb": "ruby", ".rake": "ruby",
            ".swift": "swift",
            ".kt": "kotlin", ".kts": "kotlin",
            ".scala": "scala",
            ".sh": "shell", ".bash": "shell", ".zsh": "shell",
            ".ps1": "powershell", ".psm1": "powershell",
            ".html": "html", ".htm": "html", ".xhtml": "html",
            ".css": "css", ".scss": "css", ".sass": "css", ".less": "css",
            ".json": "json",
            ".xml": "xml",
            ".yml": "yaml", ".yaml": "yaml",
            ".md": "markdown", ".markdown": "markdown",
            ".txt": "text",
            ".sql": "sql",
            ".dockerfile": "dockerfile",
        }
        return extension_map.get(ext, "unknown")

    def detect_language_by_content(self, content: str, filename: str = "") -> str:
        if not content:
            return "unknown"
        if filename:
            ext_lang = self.detect_language_by_extension(filename)
            if ext_lang != "unknown":
                return ext_lang
        content_sample = content[:1000]
        if re.search(r"^#!/usr/bin/env python|^#!/usr/bin/python|^#.*python", content):
            return "python"
        elif re.search(r"^#!/bin/bash|^#!/bin/sh", content):
            return "shell"
        elif re.search(r"^#!/usr/bin/env node", content):
            return "javascript"
        patterns = {
            "python": [r"def\s+\w+\s*\(", r"import\s+\w+", r"from\s+\w+\s+import", r"class\s+\w+"],
            "javascript": [r"function\s+\w+\s*\(", r"var\s+\w+\s*=", r"let\s+\w+\s*=", r"const\s+\w+\s*=", r"require\s*\("],
            "typescript": [r"interface\s+\w+", r"type\s+\w+\s*=", r"enum\s+\w+", r":\s*(string|number|boolean)"],
            "java": [r"public\s+class\s+\w+", r"public\s+static\s+void\s+main", r"import\s+java\."],
            "cpp": [r"#include\s*<\w+>", r"using\s+namespace", r"std::", r"int\s+main\s*\("],
            "csharp": [r"using\s+System", r"namespace\s+\w+", r"public\s+class\s+\w+", r"Console\.WriteLine"],
            "go": [r"package\s+\w+", r"import\s*\(", r"func\s+\w+\s*\(", r"var\s+\w+\s+\w+"],
            "rust": [r"fn\s+\w+\s*\(", r"use\s+\w+", r"struct\s+\w+", r"impl\s+\w+"],
            "php": [r"<\?php", r"\$\w+\s*=", r"function\s+\w+\s*\(", r"class\s+\w+"],
            "ruby": [r"def\s+\w+", r"class\s+\w+", r"require\s+", r"puts\s+"],
            "html": [r"<[^>]+>.*</\w+>"],
            "css": [r"[\w-]+\s*:\s*[^;]+\s*;", r"@media", r"\.[\w-]+\s*\{", r"#[\w-]+\s*\{"],
            "json": [r"^\s*{.*}\s*$", r"^\s*\[.*\]\s*$"],
            "yaml": [r"^\s*\w+\s*:", r"^\s*-\s+\w+"],
            "xml": [r"<\?xml", r"<\w+.*?>.*</\w+>"],
            "sql": [r"SELECT\s+", r"INSERT\s+INTO", r"UPDATE\s+", r"DELETE\s+FROM"],
            "dockerfile": [r"FROM\s+", r"RUN\s+", r"COPY\s+", r"WORKDIR\s+"],
        }
        scores: Dict[str, int] = {}
        for language, lang_patterns in patterns.items():
            score = sum(len(re.findall(p, content_sample, re.IGNORECASE | re.MULTILINE)) for p in lang_patterns)
            if score > 0:
                scores[language] = score
        return max(scores.items(), key=lambda x: x[1])[0] if scores else "text"

    def is_code_file(self, filename: str, content: str = "") -> bool:
        if not filename:
            return False
        ext = Path(filename).suffix.lower()
        if ext in self.code_extensions:
            return True
        if ext in self.data_extensions or ext in self.markup_extensions:
            return False
        if content:
            language = self.detect_language_by_content(content, filename)
            return language not in ("json", "xml", "yaml", "text", "markdown", "unknown")
        return True

    def calculate_complexity(self, content: str, language: str) -> float:
        if not content or not content.strip():
            return 1.0
        lines = content.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            return 1.0
        complexity_indicators = {
            "python": [r"\bif\b", r"\belse\b", r"\belif\b", r"\bfor\b", r"\bwhile\b", r"\btry\b", r"\bexcept\b", r"\bwith\b", r"\bclass\b", r"\bdef\b"],
            "javascript": [r"\bif\b", r"\belse\b", r"\bfor\b", r"\bwhile\b", r"\bswitch\b", r"\bcatch\b", r"\bfunction\b", r"\bclass\b", r"=>", r"\?.*:"],
            "typescript": [r"\bif\b", r"\belse\b", r"\bfor\b", r"\bwhile\b", r"\bswitch\b", r"\bcatch\b", r"\bfunction\b", r"\bclass\b", r"=>", r"\?.*:"],
            "java": [r"\bif\b", r"\belse\b", r"\bfor\b", r"\bwhile\b", r"\bswitch\b", r"\bcatch\b", r"\bclass\b", r"\bpublic\b", r"\bprivate\b"],
            "cpp": [r"\bif\b", r"\belse\b", r"\bfor\b", r"\bwhile\b", r"\bswitch\b", r"\bcatch\b", r"\bclass\b", r"\bstruct\b", r"\btemplate\b"],
        }
        patterns = complexity_indicators.get(language, complexity_indicators["python"])
        complexity_count = sum(len(re.findall(p, content, re.IGNORECASE)) for p in patterns)
        complexity_ratio = complexity_count / total_lines
        return min(1.0 + (complexity_ratio * 9.0), 10.0)

    def detect_languages(self, files: List[Dict[str, Any]]) -> Dict[str, float]:
        if not isinstance(files, list):
            return {}
        language_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"size": 0, "count": 0, "code_size": 0, "code_count": 0}
        )
        total_size = total_count = total_code_size = total_code_count = 0
        for file_item in files:
            if not isinstance(file_item, dict):
                continue
            path = file_item.get("path", "")
            size = file_item.get("size", 0)
            content = file_item.get("content", "")
            if size < 10:
                continue
            language = self.detect_language_by_extension(path)
            if language == "unknown" and content:
                language = self.detect_language_by_content(content, path)
            ext = Path(path).suffix.lower()
            is_code = ext in self.code_extensions
            language_stats[language]["size"] += size
            language_stats[language]["count"] += 1
            total_size += size
            total_count += 1
            if is_code:
                language_stats[language]["code_size"] += size
                language_stats[language]["code_count"] += 1
                total_code_size += size
                total_code_count += 1
        language_percentages: Dict[str, float] = {}
        for language, stats in language_stats.items():
            size_pct = (stats["size"] / total_size * 100) if total_size > 0 else 0
            count_pct = (stats["count"] / total_count * 100) if total_count > 0 else 0
            if total_code_size > 0 and stats["code_size"] > 0:
                code_size_pct = stats["code_size"] / total_code_size * 100
                code_count_pct = (stats["code_count"] / total_code_count * 100) if total_code_count > 0 else 0
                weighted = size_pct * 0.4 + count_pct * 0.2 + code_size_pct * 0.3 + code_count_pct * 0.1
            else:
                weighted = size_pct * 0.6 + count_pct * 0.4
            if weighted >= 3.0:
                if stats["code_count"] == 0 and stats["count"] > 0:
                    if self._get_primary_extension_for_language(language) in self.data_extensions:
                        weighted *= 0.7
                language_percentages[language] = round(weighted, 1)
        sorted_langs = dict(sorted(language_percentages.items(), key=lambda x: x[1], reverse=True))
        if sorted_langs:
            top_lang = next(iter(sorted_langs))
            top_pct = sorted_langs[top_lang]
            if top_pct > 70 and language_stats[top_lang]["code_count"] == 0:
                redistribution = min(top_pct - 50, 20)
                sorted_langs[top_lang] = top_pct - redistribution
                code_langs = [l for l, s in language_stats.items() if s["code_count"] > 0 and l in sorted_langs]
                if code_langs:
                    boost = redistribution / len(code_langs)
                    for l in code_langs:
                        sorted_langs[l] = sorted_langs[l] + boost
        return dict(sorted({k: round(v, 1) for k, v in sorted_langs.items()}.items(), key=lambda x: x[1], reverse=True))

    def _get_primary_extension_for_language(self, language: str) -> str:
        mapping = {
            "python": ".py", "javascript": ".js", "typescript": ".ts", "java": ".java",
            "cpp": ".cpp", "csharp": ".cs", "go": ".go", "rust": ".rs", "php": ".php",
            "ruby": ".rb", "json": ".json", "xml": ".xml", "yaml": ".yml",
            "html": ".html", "css": ".css", "markdown": ".md",
        }
        return mapping.get(language, ".txt")

    def detect_primary_language(self, files: List[Dict[str, Any]]) -> str:
        languages = self.detect_languages(files)
        return next(iter(languages.keys())) if languages else "unknown"

    def detect_frameworks(self, files: List[Dict[str, Any]], primary_language: Optional[str] = None) -> List[str]:
        if not primary_language:
            primary_language = self.detect_primary_language(files)
        if primary_language not in self.framework_patterns:
            return []
        framework_scores: Dict[str, int] = defaultdict(int)
        framework_patterns = self.framework_patterns[primary_language]
        for file_info in files:
            path = file_info.get("path", "")
            content = file_info.get("content", "")
            if not content:
                continue
            filename = Path(path).name.lower()
            content_sample = content[:5000]
            for framework, patterns in framework_patterns.items():
                score = 0
                for pattern in patterns:
                    if re.search(pattern, filename, re.IGNORECASE):
                        score += 2
                    score += len(re.findall(pattern, content_sample, re.IGNORECASE | re.MULTILINE))
                if score > 0:
                    framework_scores[framework] += score
        detected = [fw for fw, score in framework_scores.items() if score >= 3]
        detected.sort(key=lambda x: framework_scores[x], reverse=True)
        return detected[:3]

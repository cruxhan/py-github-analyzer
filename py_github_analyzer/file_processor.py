"""

File processing and analysis module for py-github-analyzer

Enhanced language detection, dependency extraction, and file prioritization

"""

import json
import re
import time
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .config import Config
from .logger import AnalyzerLogger


class LanguageDetector:
    """Language and framework detection utilities with enhanced scoring"""

    def __init__(self):
        # Framework detection patterns
        self.framework_patterns = {
            "python": {
                "django": [
                    r"from django",
                    r"import django",
                    r"DJANGO_SETTINGS_MODULE",
                    r"manage\.py",
                    r"settings\.py",
                ],
                "flask": [
                    r"from flask",
                    r"import flask",
                    r"Flask\(__name__\)",
                    r"@app\.route",
                ],
                "fastapi": [
                    r"from fastapi",
                    r"import fastapi",
                    r"FastAPI\(",
                    r"@app\.(get|post|put|delete)",
                ],
                "pytest": [
                    r"import pytest",
                    r"def test_",
                    r"@pytest\.",
                    r"conftest\.py",
                ],
            },
            "javascript": {
                "react": [
                    r"import.*react",
                    r"from.*react",
                    r"React\.",
                    r"jsx|tsx",
                    r"useState|useEffect",
                ],
                "vue": [
                    r"import.*vue",
                    r"from.*vue",
                    r"Vue\.",
                    r"<template>",
                    r"\.vue",
                ],
                "angular": [r"@angular", r"@Component", r"@Injectable", r"@NgModule"],
                "express": [
                    r"require.*express",
                    r"import.*express",
                    r"app\.get|app\.post",
                    r"express\(\)",
                ],
                "nextjs": [
                    r"next/",
                    r"getStaticProps",
                    r"getServerSideProps",
                    r"next\.config",
                ],
            },
            "typescript": {
                "angular": [r"@angular", r"@Component", r"@Injectable"],
                "nestjs": [r"@nestjs", r"@Controller", r"@Injectable", r"@Module"],
            },
        }

        # Define code vs data file categories for weighted scoring
        self.code_extensions = {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".cpp", ".c", ".h", ".hpp",
            ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".scala", ".clj",
            ".hs", ".ml", ".elm", ".dart", ".lua", ".r", ".m", ".sh", ".ps1", ".bat"
        }

        self.data_extensions = {
            ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".conf", ".cfg",
            ".csv", ".tsv", ".sql", ".log", ".txt"
        }

        self.markup_extensions = {
            ".html", ".htm", ".xhtml", ".xml", ".svg", ".md", ".rst", ".tex"
        }

    def detect_language_by_extension(self, filename: str) -> str:
        """Detect language by file extension"""
        if not filename:
            return "unknown"
        
        ext = Path(filename).suffix.lower()
        
        # Map extensions to languages
        extension_map = {
            ".py": "python",
            ".pyx": "python",
            ".pyi": "python",
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
            ".dockerfile": "dockerfile"
        }
        
        return extension_map.get(ext, "unknown")

    def detect_language_by_content(self, content: str, filename: str = "") -> str:
        """Detect language by analyzing file content"""
        if not content:
            return "unknown"
        
        # First try extension-based detection
        if filename:
            ext_lang = self.detect_language_by_extension(filename)
            if ext_lang != "unknown":
                return ext_lang
        
        # Content-based patterns
        content_sample = content[:1000]  # Check first 1000 chars
        
        # Strong indicators
        if re.search(r'^#!/usr/bin/env python|^#!/usr/bin/python|^#.*python', content):
            return "python"
        elif re.search(r'^#!/bin/bash|^#!/bin/sh', content):
            return "shell"
        elif re.search(r'^#!/usr/bin/env node', content):
            return "javascript"
        
        # Language-specific keywords and patterns
        patterns = {
            "python": [r'def\s+\w+\s*\(', r'import\s+\w+', r'from\s+\w+\s+import', r'class\s+\w+'],
            "javascript": [r'function\s+\w+\s*\(', r'var\s+\w+\s*=', r'let\s+\w+\s*=', r'const\s+\w+\s*=', r'require\s*\('],
            "typescript": [r'interface\s+\w+', r'type\s+\w+\s*=', r'enum\s+\w+', r':\s*(string|number|boolean)'],
            "java": [r'public\s+class\s+\w+', r'public\s+static\s+void\s+main', r'import\s+java\.'],
            "cpp": [r'#include\s*<\w+>', r'using\s+namespace', r'std::', r'int\s+main\s*\('],
            "csharp": [r'using\s+System', r'namespace\s+\w+', r'public\s+class\s+\w+', r'Console\.WriteLine'],
            "go": [r'package\s+\w+', r'import\s*\(', r'func\s+\w+\s*\(', r'var\s+\w+\s+\w+'],
            "rust": [r'fn\s+\w+\s*\(', r'use\s+\w+', r'struct\s+\w+', r'impl\s+\w+'],
            "php": [r'<\?php', r'\$\w+\s*=', r'function\s+\w+\s*\(', r'class\s+\w+'],
            "ruby": [r'def\s+\w+', r'class\s+\w+', r'require\s+', r'puts\s+'],
            "html": [r'<[^>]+>.*</\w+>'],
            "css": [r'[\w-]+\s*:\s*[^;]+\s*;', r'@media', r'\.[\w-]+\s*\{', r'#[\w-]+\s*\{'],
            "json": [r'^\s*{.*}\s*$', r'^\s*\[.*\]\s*$'],
            "yaml": [r'^\s*\w+\s*:', r'^\s*-\s+\w+'],
            "xml": [r'<\?xml', r'<\w+.*?>.*</\w+>'],
            "sql": [r'SELECT\s+', r'INSERT\s+INTO', r'UPDATE\s+', r'DELETE\s+FROM'],
            "dockerfile": [r'FROM\s+', r'RUN\s+', r'COPY\s+', r'WORKDIR\s+'],
        }
        
        scores = {}
        for language, lang_patterns in patterns.items():
            score = 0
            for pattern in lang_patterns:
                matches = len(re.findall(pattern, content_sample, re.IGNORECASE | re.MULTILINE))
                score += matches
            if score > 0:
                scores[language] = score
        
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return "text"  # Default fallback

    def is_code_file(self, filename: str, content: str = "") -> bool:
        """Determine if a file is a code file"""
        if not filename:
            return False
        
        ext = Path(filename).suffix.lower()
        
        # Check by extension first
        if ext in self.code_extensions:
            return True
        elif ext in self.data_extensions or ext in self.markup_extensions:
            return False
        
        # If no extension or unknown extension, check content
        if content:
            language = self.detect_language_by_content(content, filename)
            return language not in ["json", "xml", "yaml", "text", "markdown", "unknown"]
        
        # Default to considering it code if uncertain
        return True

    def calculate_complexity(self, content: str, language: str) -> float:
        """Calculate code complexity score"""
        if not content or not content.strip():
            return 1.0
        
        lines = content.splitlines()
        total_lines = len(lines)
        
        if total_lines == 0:
            return 1.0
        
        complexity_indicators = {
            "python": [
                r'\bif\b', r'\belse\b', r'\belif\b', r'\bfor\b', r'\bwhile\b',
                r'\btry\b', r'\bexcept\b', r'\bwith\b', r'\bclass\b', r'\bdef\b'
            ],
            "javascript": [
                r'\bif\b', r'\belse\b', r'\bfor\b', r'\bwhile\b', r'\bswitch\b',
                r'\bcatch\b', r'\bfunction\b', r'\bclass\b', r'=>', r'\?.*:'
            ],
            "typescript": [
                r'\bif\b', r'\belse\b', r'\bfor\b', r'\bwhile\b', r'\bswitch\b',
                r'\bcatch\b', r'\bfunction\b', r'\bclass\b', r'=>', r'\?.*:'
            ],
            "java": [
                r'\bif\b', r'\belse\b', r'\bfor\b', r'\bwhile\b', r'\bswitch\b',
                r'\bcatch\b', r'\bclass\b', r'\bpublic\b', r'\bprivate\b'
            ],
            "cpp": [
                r'\bif\b', r'\belse\b', r'\bfor\b', r'\bwhile\b', r'\bswitch\b',
                r'\bcatch\b', r'\bclass\b', r'\bstruct\b', r'\btemplate\b'
            ]
        }
        
        patterns = complexity_indicators.get(language, complexity_indicators.get("python", []))
        
        complexity_count = 0
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            complexity_count += len(matches)
        
        # Calculate complexity score (1.0 to 10.0)
        if total_lines == 0:
            return 1.0
        
        complexity_ratio = complexity_count / total_lines
        base_complexity = 1.0 + (complexity_ratio * 9.0)
        
        # Cap at reasonable maximum
        return min(base_complexity, 10.0)

    def detect_languages(self, files: List[Dict[str, Any]]) -> Dict[str, float]:
        """Enhanced language detection with balanced scoring between size and file count"""
        language_stats = defaultdict(
            lambda: {"size": 0, "count": 0, "code_size": 0, "code_count": 0}
        )

        total_size = 0
        total_count = 0
        total_code_size = 0
        total_code_count = 0

        # Ensure files is a list
        if not isinstance(files, list):
            return {}

        for file_item in files:
            # Ensure each item is a dictionary
            if not isinstance(file_item, dict):
                continue

            path = file_item.get("path", "")
            size = file_item.get("size", 0)
            content = file_item.get("content", "")

            # Skip very small files
            if size < 10:
                continue

            language = self.detect_language_by_extension(path)
            if language == "unknown" and content:
                language = self.detect_language_by_content(content, path)

            # Get file extension
            ext = Path(path).suffix.lower()

            # Determine if this is a code file
            is_code_file = ext in self.code_extensions
            is_data_file = (
                ext in self.data_extensions or ext in self.markup_extensions
            )

            # Basic stats
            language_stats[language]["size"] += size
            language_stats[language]["count"] += 1
            total_size += size
            total_count += 1

            # Enhanced stats for code files
            if is_code_file:
                language_stats[language]["code_size"] += size
                language_stats[language]["code_count"] += 1
                total_code_size += size
                total_code_count += 1

        # Calculate enhanced percentages with balanced scoring
        language_percentages = {}
        for language, stats in language_stats.items():
            # Base calculations
            size_percentage = (
                (stats["size"] / total_size * 100) if total_size > 0 else 0
            )
            count_percentage = (
                (stats["count"] / total_count * 100) if total_count > 0 else 0
            )

            # Enhanced scoring for code files
            if total_code_size > 0 and stats["code_size"] > 0:
                code_size_percentage = stats["code_size"] / total_code_size * 100
                code_count_percentage = (
                    (stats["code_count"] / total_code_count * 100)
                    if total_code_count > 0
                    else 0
                )

                # Weighted average: prioritize code files
                # 40% size-based, 20% count-based, 30% code-size-based, 10% code-count-based
                weighted_percentage = (
                    size_percentage * 0.4
                    + count_percentage * 0.2
                    + code_size_percentage * 0.3
                    + code_count_percentage * 0.1
                )
            else:
                # Fallback for non-code languages (markup, data, etc.)
                # 60% size-based, 40% count-based
                weighted_percentage = size_percentage * 0.6 + count_percentage * 0.4

            # Apply minimum threshold and data file penalty
            if weighted_percentage >= 3.0:  # Lower threshold
                # Penalize pure data files if they dominate
                if stats["code_count"] == 0 and stats["count"] > 0:
                    # This language has no code files, apply penalty
                    ext_for_lang = self._get_primary_extension_for_language(language)
                    if ext_for_lang in self.data_extensions:
                        weighted_percentage *= 0.7  # Reduce by 30%

                language_percentages[language] = round(weighted_percentage, 1)

        # Sort by percentage and ensure no single data language dominates
        sorted_languages = dict(
            sorted(language_percentages.items(), key=lambda x: x[1], reverse=True)
        )

        # Final balancing: if top language is pure data and > 70%, redistribute
        if sorted_languages:
            top_lang = list(sorted_languages.keys())[0]
            top_percentage = sorted_languages[top_lang]
            top_stats = language_stats[top_lang]

            if top_percentage > 70 and top_stats["code_count"] == 0:
                # Redistribute some percentage to code languages
                redistribution = min(top_percentage - 50, 20)  # Max 20% redistribution
                sorted_languages[top_lang] = top_percentage - redistribution

                # Find code languages to boost
                code_languages = [
                    lang
                    for lang, stats in language_stats.items()
                    if stats["code_count"] > 0 and lang in sorted_languages
                ]

                if code_languages:
                    boost_per_lang = redistribution / len(code_languages)
                    for lang in code_languages:
                        sorted_languages[lang] = sorted_languages[lang] + boost_per_lang

        # Re-round and re-sort
        sorted_languages = {k: round(v, 1) for k, v in sorted_languages.items()}
        sorted_languages = dict(
            sorted(sorted_languages.items(), key=lambda x: x[1], reverse=True)
        )

        return sorted_languages

    def _get_primary_extension_for_language(self, language: str) -> str:
        """Get the primary file extension for a language"""
        # Simple mapping - could be enhanced
        mapping = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "cpp": ".cpp",
            "csharp": ".cs",
            "go": ".go",
            "rust": ".rs",
            "php": ".php",
            "ruby": ".rb",
            "json": ".json",
            "xml": ".xml",
            "yaml": ".yml",
            "html": ".html",
            "css": ".css",
            "markdown": ".md",
        }

        return mapping.get(language, ".txt")

    def detect_primary_language(self, files: List[Dict[str, Any]]) -> str:
        """Detect the primary programming language"""
        languages = self.detect_languages(files)
        if not languages:
            return "unknown"
        return next(iter(languages.keys()))  # First (highest percentage) language

    def detect_frameworks(
        self, files: List[Dict[str, Any]], primary_language: str = None
    ) -> List[str]:
        """Detect frameworks based on file contents and patterns (fixed signature)"""
        if not primary_language:
            primary_language = self.detect_primary_language(files)
            
        if primary_language not in self.framework_patterns:
            return []

        framework_scores = defaultdict(int)
        framework_patterns = self.framework_patterns[primary_language]

        for file_info in files:
            path = file_info.get("path", "")
            content = file_info.get("content", "")

            if not content:
                continue

            # Check filename patterns
            filename = Path(path).name.lower()

            # Check each framework
            for framework, patterns in framework_patterns.items():
                score = 0

                for pattern in patterns:
                    # Check in filename
                    if re.search(pattern, filename, re.IGNORECASE):
                        score += 2

                    # Check in file content (sample first 5000 chars for performance)
                    content_sample = content[:5000]
                    matches = len(
                        re.findall(
                            pattern, content_sample, re.IGNORECASE | re.MULTILINE
                        )
                    )
                    score += matches

                if score > 0:
                    framework_scores[framework] += score

        # Return frameworks with significant scores
        detected_frameworks = []
        for framework, score in framework_scores.items():
            if score >= 3:  # Threshold for detection
                detected_frameworks.append(framework)

        # Sort by score
        detected_frameworks.sort(key=lambda x: framework_scores[x], reverse=True)
        return detected_frameworks[:3]  # Return top 3 frameworks


class DependencyExtractor:
    """Extract dependencies from various file types"""

    def __init__(self):
        self.extractors = {
            "python": self._extract_python_deps,
            "javascript": self._extract_js_deps,
            "typescript": self._extract_js_deps,  # Same as JS
            "java": self._extract_java_deps,
            "go": self._extract_go_deps,
            "rust": self._extract_rust_deps,
            "csharp": self._extract_csharp_deps,
        }

    def extract_dependencies(
        self, files: List[Dict[str, Any]], primary_language: str
    ) -> List[str]:
        """Extract dependencies for the primary language"""
        if primary_language not in self.extractors:
            return []

        extractor = self.extractors[primary_language]
        all_deps = set()

        for file_info in files:
            try:
                deps = extractor(file_info)
                all_deps.update(deps)
                # Limit to prevent excessive memory usage
                if len(all_deps) > 100:
                    break
            except Exception:
                continue  # Skip problematic files

        # Filter and clean dependencies
        filtered_deps = []
        for dep in all_deps:
            if len(dep) > 1 and len(dep) < 50 and not dep.startswith("."):
                filtered_deps.append(dep)

        return sorted(filtered_deps)[:30]  # Return top 30

    def _extract_python_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract Python dependencies"""
        deps = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()

        # Handle requirements files
        if filename in [
            "requirements.txt",
            "requirements-dev.txt",
            "dev-requirements.txt",
        ]:
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    # Extract package name (before any version specifiers)
                    match = re.match(r"^([a-zA-Z0-9_-]+)", line)
                    if match:
                        deps.add(match.group(1))

        # Handle setup.py
        elif filename == "setup.py":
            # Look for install_requires
            requires_match = re.search(
                r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL
            )
            if requires_match:
                requires_content = requires_match.group(1)
                for match in re.findall(r'["\']([a-zA-Z0-9_-]+)', requires_content):
                    deps.add(match)

        # Handle pyproject.toml
        elif filename == "pyproject.toml":
            # Simple regex-based extraction (not full TOML parsing)
            deps_match = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if deps_match:
                deps_content = deps_match.group(1)
                for match in re.findall(r'["\']([a-zA-Z0-9_-]+)', deps_content):
                    deps.add(match)

        # Handle import statements in regular Python files
        elif filename.endswith(".py"):
            # Extract from import statements
            import_pattern = r"(?:^from\s+([a-zA-Z0-9_]+)|^import\s+([a-zA-Z0-9_]+))"
            for match in re.findall(import_pattern, content, re.MULTILINE):
                dep = match[0] or match[1]
                if dep and not dep.startswith("_"):
                    deps.add(dep)

        return deps

    def _extract_js_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract JavaScript/TypeScript dependencies"""
        deps = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()

        # Handle package.json
        if filename == "package.json":
            try:
                package_data = json.loads(content)
                for dep_type in ["dependencies", "devDependencies", "peerDependencies"]:
                    if dep_type in package_data:
                        deps.update(package_data[dep_type].keys())
            except json.JSONDecodeError:
                pass

        # Handle JavaScript/TypeScript files
        elif filename.endswith((".js", ".ts", ".jsx", ".tsx")):
            # Extract from import/require statements
            patterns = [
                r'import.*?from\s+[\'"]([^\'"]+)[\'"]',
                r'require\([\'"]([^\'"]+)[\'"]\)',
                r'import\([\'"]([^\'"]+)[\'"]\)',
                r'import\s+[\'"]([^\'"]+)[\'"]',
            ]

            for pattern in patterns:
                for match in re.findall(pattern, content):
                    # Skip relative imports
                    if not match.startswith("."):
                        # Extract base package name
                        base_pkg = match.split("/")[0]
                        if base_pkg.startswith("@"):  # Scoped package
                            parts = match.split("/")
                            if len(parts) >= 2:
                                base_pkg = f"{parts[0]}/{parts[1]}"
                        deps.add(base_pkg)

        return deps

    def _extract_java_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract Java dependencies"""
        deps = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()

        # Handle Maven pom.xml
        if filename == "pom.xml":
            # Extract groupId and artifactId
            artifact_pattern = r"<artifactId>(.*?)</artifactId>"
            for match in re.findall(artifact_pattern, content):
                deps.add(match)

        # Handle Gradle build files
        elif filename in ["build.gradle", "build.gradle.kts"]:
            # Extract implementation/compile dependencies
            dep_pattern = r'(?:implementation|compile|api)\s+[\'"]([^:]+):([^:\'"]+)'
            for match in re.findall(dep_pattern, content):
                deps.add(match[1])  # artifactId

        return deps

    def _extract_go_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract Go dependencies"""
        deps = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()

        if filename == "go.mod":
            # Extract require statements
            require_pattern = r"require\s+([^\s]+)"
            for match in re.findall(require_pattern, content):
                deps.add(match)

        elif filename.endswith(".go"):
            # Extract import statements
            import_pattern = r'import\s+(?:"([^"]+)"|`([^`]+)`)'
            for match in re.findall(import_pattern, content):
                dep = match[0] or match[1]
                deps.add(dep)

        return deps

    def _extract_rust_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract Rust dependencies"""
        deps = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()

        if filename == "cargo.toml":
            # Extract dependencies section
            deps_match = re.search(r"\[dependencies\](.*?)(?:\[|$)", content, re.DOTALL)
            if deps_match:
                deps_content = deps_match.group(1)
                for line in deps_content.split("\n"):
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        dep_name = line.split("=")[0].strip()
                        deps.add(dep_name)

        return deps

    def _extract_csharp_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        """Extract C# dependencies"""
        deps = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()

        # Handle .csproj files
        if filename.endswith(".csproj"):
            # Extract PackageReference
            package_pattern = r'<PackageReference\s+Include="([^"]+)"'
            for match in re.findall(package_pattern, content):
                deps.add(match)

        return deps

class FilePrioritizer:
    """Advanced file prioritization with context awareness and smart scoring"""

    def __init__(self, logger: Optional[AnalyzerLogger] = None):
        self.logger = logger or AnalyzerLogger()
        self.language_detector = LanguageDetector()

        # Priority weights for different factors
        self.weights = {
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
        """
        Prioritize files based on multiple factors:
        - Language relevance
        - File importance (README, config files, etc.)
        - Code complexity
        - File size and depth
        - Framework detection
        """
        if not files:
            return []

        self.logger.debug(f"Prioritizing {len(files)} files...")

        prioritized_files = []
        context = context or {}

        # Auto-detect target language if not provided
        if not target_language:
            target_language = self.language_detector.detect_primary_language(files)
            self.logger.debug(f"Auto-detected primary language: {target_language}")

        for file_info in files:
            try:
                enhanced_file = self._calculate_priority_score(
                    file_info, target_language, context
                )
                prioritized_files.append(enhanced_file)
            except Exception as e:
                self.logger.warning(
                    f"Error prioritizing {file_info.get('path', 'unknown')}: {e}"
                )
                # Assign default priority
                file_info["priority"] = 100
                prioritized_files.append(file_info)

        # Sort by priority score (higher = more important)
        prioritized_files.sort(key=lambda x: x.get("priority", 100), reverse=True)

        self.logger.debug(
            f"Top 5 prioritized files: {[f.get('path', 'unknown') for f in prioritized_files[:5]]}"
        )

        return prioritized_files

    def _calculate_priority_score(
        self, file_info: Dict[str, Any], target_language: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate comprehensive priority score for a single file"""
        path = file_info.get("path", "")
        size = file_info.get("size", 0)
        content = file_info.get("content", "")

        # Create a copy to avoid modifying original
        enhanced_file = file_info.copy()

        if not path:
            enhanced_file["priority"] = 50
            return enhanced_file

        filename = Path(path).name.lower()
        file_ext = Path(path).suffix.lower()
        directory_depth = len(Path(path).parts) - 1

        # Base priority from file category
        category = Config.get_file_category(filename)
        base_priority = self._get_base_priority_by_category(category)

        # Factor 1: Language matching
        detected_language = self.language_detector.detect_language_by_extension(filename)
        if detected_language == "unknown" and content:
            detected_language = self.language_detector.detect_language_by_content(
                content, filename
            )

        language_bonus = 0
        if detected_language == target_language:
            language_bonus = self.weights["language_match"]
        elif detected_language in ["python", "javascript", "typescript", "java"]:
            language_bonus = self.weights["language_match"] // 2

        # Factor 2: Special file importance
        importance_bonus = self._calculate_importance_bonus(filename, path)

        # Factor 3: Framework detection bonus
        framework_bonus = self._calculate_framework_bonus(content, detected_language)

        # Factor 4: Complexity bonus for code files
        complexity_bonus = 0
        if content and detected_language in [
            "python",
            "javascript",
            "typescript",
            "java",
            "cpp",
        ]:
            complexity_score = self.language_detector.calculate_complexity(
                content, detected_language
            )
            enhanced_file["complexity"] = complexity_score
            complexity_bonus = min(
                int(complexity_score * self.weights["complexity"]), 200
            )

        # Factor 5: Size considerations
        size_factor = self._calculate_size_factor(size)

        # Factor 6: Directory depth penalty
        depth_penalty = min(directory_depth * self.weights["depth_penalty"], 150)

        # Factor 7: Content quality bonus
        content_bonus = self._calculate_content_quality_bonus(content, file_ext)

        # Calculate final priority
        final_priority = (
            base_priority
            + language_bonus
            + importance_bonus
            + framework_bonus
            + complexity_bonus
            + size_factor
            + content_bonus
            - depth_penalty
        )

        # Ensure minimum priority
        final_priority = max(final_priority, 10)

        enhanced_file["priority"] = int(final_priority)
        enhanced_file["language"] = detected_language
        enhanced_file["priority_breakdown"] = {
            "base": base_priority,
            "language": language_bonus,
            "importance": importance_bonus,
            "framework": framework_bonus,
            "complexity": complexity_bonus,
            "size": size_factor,
            "content": content_bonus,
            "depth_penalty": -depth_penalty,
        }

        return enhanced_file

    def _get_base_priority_by_category(self, category: str) -> int:
        """Get base priority by file category"""
        category_priorities = {
            "python": 800,
            "javascript": 750,
            "typescript": 750,
            "java": 700,
            "cpp": 650,
            "csharp": 650,
            "go": 650,
            "rust": 650,
            "php": 600,
            "ruby": 600,
            "swift": 580,
            "kotlin": 580,
            "scala": 570,
            "dockerfile": 900,  # Very important for understanding deployment
            "makefile": 800,  # Important for build process
            "config": 550,
            "yaml": 500,
            "json": 500,
            "xml": 400,
            "markdown": 400,
            "text": 300,
            "binary": 0,
            "skip": 0,
        }

        return category_priorities.get(category, 200)

    def _calculate_importance_bonus(self, filename: str, full_path: str) -> int:
        """Calculate bonus for important files"""
        importance_patterns = {
            # Documentation
            "readme.md": 300,
            "readme.txt": 250,
            "changelog.md": 150,
            "license": 100,
            "contributing.md": 100,
            # Build and deployment
            "dockerfile": 400,
            "docker-compose.yml": 350,
            "makefile": 300,
            "package.json": 250,
            "requirements.txt": 200,
            "setup.py": 200,
            "pyproject.toml": 200,
            "cargo.toml": 200,
            "go.mod": 200,
            "pom.xml": 180,
            "build.gradle": 180,
            ".gitignore": 100,
            # Application entry points
            "main.py": 300,
            "main.js": 300,
            "index.js": 300,
            "index.html": 250,
            "app.py": 300,
            "server.py": 250,
            "manage.py": 200,  # Django
            # Configuration files
            "config.py": 180,
            "settings.py": 200,
            "wsgi.py": 150,
            "asgi.py": 150,
        }

        # Direct filename match
        if filename in importance_patterns:
            return importance_patterns[filename]

        # Pattern-based matching
        bonus = 0

        # Main/entry files
        if re.search(r"\b(main|index|app|server)\b", filename):
            bonus += 200

        # Test files (moderate importance)
        if re.search(r"\b(test|spec)s?\b", filename) and not "node_modules" in full_path:
            bonus += 50

        # Config files
        if re.search(r"\b(config|settings|env)\b", filename):
            bonus += 100

        # API/endpoint files
        if re.search(r"\b(api|endpoint|route|view)s?\b", filename):
            bonus += 150

        # Model/schema files
        if re.search(r"\b(model|schema|entity)s?\b", filename):
            bonus += 120

        return bonus

    def _calculate_framework_bonus(self, content: str, language: str) -> int:
        """Calculate bonus for framework-specific files"""
        if not content:
            return 0

        bonus = 0
        content_sample = content[:2000]  # Check first 2000 chars

        # Framework patterns and their bonuses
        framework_patterns = {
            # Python frameworks
            r"\bfrom django\b|\bimport django\b": 150,
            r"\bfrom flask\b|\bFlask\(": 150,
            r"\bfrom fastapi\b|\bFastAPI\(": 150,
            r"\bfastapi\b.*\bApp": 100,
            # JavaScript frameworks
            r"\bfrom ['\"]react['\"]|\bimport.*react": 150,
            r"\bfrom ['\"]vue['\"]|\bVue\.": 150,
            r"\b@angular\b|\bAngular": 150,
            r"\bexpress\(\)|\brequire.*express": 120,
            r"\bnext/|\bgetStaticProps": 130,
            # Build tools
            r"\bwebpack\b|\brollup\b|\bvite\b": 100,
            r"\bbabel\b|\b@babel": 80,
            r"\bjest\b|\bcypress\b": 70,
            # Database
            r"\bsqlalchemy\b|\bdjango\.db": 100,
            r"\bmongoose\b|\bmongodb": 90,
            # Other important patterns
            r"\bexport default\b|\bmodule\.exports": 50,
            r"\bclass\s+\w+.*Component": 100,  # React/Vue components
        }

        for pattern, pattern_bonus in framework_patterns.items():
            if re.search(pattern, content_sample, re.IGNORECASE):
                bonus += pattern_bonus

        return min(bonus, 300)  # Cap framework bonus

    def _calculate_size_factor(self, size: int) -> int:
        """Calculate size-based priority factor"""
        if size == 0:
            return -50  # Empty files get penalty

        if size > Config.MAX_FILE_SIZE:
            return -200  # Oversized files get penalty

        if size < 100:  # Very small files
            return -30

        if 100 <= size <= 5000:  # Sweet spot
            return 30

        if 5000 < size <= 20000:  # Good size
            return 10

        if 20000 < size <= 50000:  # Large but manageable
            return -10

        return -30  # Very large files

    def _calculate_content_quality_bonus(self, content: str, file_ext: str) -> int:
        """Calculate bonus based on content quality indicators"""
        if not content:
            return 0

        bonus = 0

        # Has meaningful content
        if len(content.strip()) > 50:
            bonus += 20

        # Has documentation/comments
        if file_ext in [".py", ".js", ".ts", ".java", ".cpp"]:
            comment_ratio = self._calculate_comment_ratio(content, file_ext)
            if comment_ratio > 0.1:  # More than 10% comments
                bonus += 30

        # Has structured content (classes, functions, etc.)
        if re.search(
            r"\b(class|function|def|interface|struct)\s+\w+", content, re.IGNORECASE
        ):
            bonus += 40

        # Has imports/includes (indicates it's a real code file)
        if re.search(
            r"\b(import|include|require|from)\s+", content, re.IGNORECASE
        ):
            bonus += 20

        return bonus

    def _calculate_comment_ratio(self, content: str, file_ext: str) -> float:
        """Calculate ratio of comments to total content"""
        if not content:
            return 0.0

        total_lines = len(content.splitlines())
        if total_lines == 0:
            return 0.0

        comment_patterns = {
            ".py": r"^\s*#",
            ".js": r"^\s*//|/\*.*?\*/",
            ".ts": r"^\s*//|/\*.*?\*/",
            ".java": r"^\s*//|/\*.*?\*/",
            ".cpp": r"^\s*//|/\*.*?\*/",
            ".c": r"^\s*//|/\*.*?\*/",
        }

        pattern = comment_patterns.get(file_ext)
        if not pattern:
            return 0.0

        comment_lines = len(re.findall(pattern, content, re.MULTILINE))
        return comment_lines / total_lines


class FileProcessor:
    """Main file processing orchestrator with enhanced analysis capabilities"""

    def __init__(self, logger: Optional[AnalyzerLogger] = None):
        self.logger = logger or AnalyzerLogger()
        self.language_detector = LanguageDetector()
        self.dependency_extractor = DependencyExtractor()
        self.file_prioritizer = FilePrioritizer(logger)

        # Add backward compatibility alias
        self.detector = self.language_detector
        self.prioritizer = self.file_prioritizer

        # Processing statistics
        self.stats = {
            "total_files_processed": 0,
            "files_filtered": 0,
            "files_selected": 0,
            "processing_time": 0.0,
            "languages_detected": 0,
            "frameworks_detected": 0,
        }

    def process_files(
        self, files: List[Dict[str, Any]], context: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Main processing pipeline:
        1. Basic validation and filtering
        2. Language detection and analysis
        3. Framework detection
        4. Dependency extraction
        5. File prioritization
        6. Smart selection within limits
        """
        start_time = time.time()
        context = context or {}

        self.logger.info(f"Processing {len(files)} files...")
        self.stats["total_files_processed"] = len(files)

        # Step 1: Basic filtering
        valid_files = self._apply_basic_filtering(files)
        self.logger.info(f"After basic filtering: {len(valid_files)} files")
        self.stats["files_filtered"] = len(files) - len(valid_files)

        if not valid_files:
            return [], {"error": "No valid files to process"}

        # Step 2: Language analysis
        self.logger.info("Analyzing languages...")
        languages = self.language_detector.detect_languages(valid_files)
        primary_language = (
            next(iter(languages.keys())) if languages else "unknown"
        )
        self.stats["languages_detected"] = len(languages)

        self.logger.info(f"Primary language: {primary_language}")
        self.logger.debug(f"Language distribution: {languages}")

        # Step 3: Framework detection
        self.logger.info("Detecting frameworks...")
        frameworks = self.language_detector.detect_frameworks(
            valid_files, primary_language
        )
        self.stats["frameworks_detected"] = len(frameworks)

        if frameworks:
            self.logger.info(f"Detected frameworks: {frameworks}")

        # Step 4: Dependency extraction
        self.logger.info("Extracting dependencies...")
        dependencies = self.dependency_extractor.extract_dependencies(
            valid_files, primary_language
        )

        if dependencies:
            self.logger.info(f"Found {len(dependencies)} dependencies")
            self.logger.debug(f"Top dependencies: {dependencies[:10]}")

        # Step 5: File prioritization
        self.logger.info("Prioritizing files...")
        prioritized_files = self.file_prioritizer.prioritize_files(
            valid_files, primary_language, context
        )

        # Step 6: Smart selection
        selected_files = self._perform_smart_selection(prioritized_files, context)
        self.stats["files_selected"] = len(selected_files)

        # Processing complete
        processing_time = time.time() - start_time
        self.stats["processing_time"] = processing_time

        self.logger.info(
            f"Processing complete: {len(selected_files)} files selected in {processing_time:.2f}s"
        )

        # Generate analysis metadata
        analysis_info = self._generate_analysis_info(
            selected_files, languages, frameworks, dependencies, primary_language
        )

        return selected_files, analysis_info

    def _apply_basic_filtering(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply basic filtering rules"""
        valid_files = []

        for file_info in files:
            path = file_info.get("path", "")
            size = file_info.get("size", 0)
            content = file_info.get("content", "")

            # Skip files with invalid paths
            if not self._is_valid_path(path):
                continue

            # Skip oversized files
            if size > Config.MAX_FILE_SIZE:
                self.logger.debug(f"Skipping oversized file: {path} ({size} bytes)")
                continue

            # Skip files that should be ignored
            if Config.should_skip_file(path):
                continue

            # Skip binary files (basic check)
            if self._is_likely_binary(path, content):
                continue

            # Skip empty files (with some exceptions)
            if size == 0 and not self._is_important_empty_file(path):
                continue

            valid_files.append(file_info)

        return valid_files

    def _is_valid_path(self, path: str) -> bool:
        """Check if file path is valid and safe"""
        from .utils import ValidationUtils

        return ValidationUtils.validate_file_path(path)

    def _is_likely_binary(self, path: str, content: str) -> bool:
        """Check if file is likely binary"""
        if not path:
            return False

        # Check extension
        binary_extensions = {
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".bin",
            ".img",
            ".iso",
            ".zip",
            ".tar",
            ".gz",
            ".rar",
            ".7z",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".svg",
            ".ico",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
        }

        ext = Path(path).suffix.lower()
        if ext in binary_extensions:
            return True

        # Check content for binary indicators
        if content:
            # Check for null bytes (common in binary files)
            if "\x00" in content:
                return True

            # Check for high percentage of non-printable characters
            try:
                # Try to encode as UTF-8
                content.encode("utf-8")
                non_printable = sum(
                    1 for char in content[:1000] if ord(char) < 32 and char not in "\n\r\t"
                )
                if non_printable > len(content[:1000]) * 0.3:
                    return True
            except UnicodeEncodeError:
                return True

        return False

    def _is_important_empty_file(self, path: str) -> bool:
        """Check if empty file should be kept (like __init__.py)"""
        important_empty_files = {"__init__.py", ".gitkeep", ".keep"}
        filename = Path(path).name.lower()
        return filename in important_empty_files

    def _perform_smart_selection(
        self, prioritized_files: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Intelligent file selection within size and count limits"""
        if not prioritized_files:
            return []

        selected_files = []
        total_size = 0
        size_limit = context.get("max_total_size", Config.MAX_TOTAL_SIZE_BYTES)
        count_limit = context.get("max_files", Config.MAX_FILES_COUNT)

        # Group files by priority tiers for balanced selection
        priority_tiers = self._group_by_priority_tiers(prioritized_files)

        # Select from each tier proportionally
        for tier_name, tier_files in priority_tiers.items():
            for file_info in tier_files:
                file_size = file_info.get("size", 0)

                # Check size limit
                if total_size + file_size > size_limit:
                    # Try to fit smaller files
                    if file_size < size_limit * 0.1:  # Less than 10% of total limit
                        continue
                    else:
                        break

                # Check count limit
                if len(selected_files) >= count_limit:
                    break

                selected_files.append(file_info)
                total_size += file_size

            # Stop if limits reached
            if len(selected_files) >= count_limit or total_size >= size_limit * 0.9:
                break

        self.logger.info(
            f"Selected {len(selected_files)} files, total size: {total_size:,} bytes"
        )

        return selected_files

    def _group_by_priority_tiers(
        self, files: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group files into priority tiers"""
        tiers = {"critical": [], "high": [], "medium": [], "low": []}

        for file_info in files:
            priority = file_info.get("priority", 100)

            if priority >= 800:
                tiers["critical"].append(file_info)
            elif priority >= 600:
                tiers["high"].append(file_info)
            elif priority >= 400:
                tiers["medium"].append(file_info)
            else:
                tiers["low"].append(file_info)

        return tiers

    def _generate_analysis_info(
        self,
        selected_files: List[Dict[str, Any]],
        languages: Dict[str, float],
        frameworks: List[str],
        dependencies: List[str],
        primary_language: str,
    ) -> Dict[str, Any]:
        """Generate comprehensive analysis information"""
        # Calculate statistics
        total_size = sum(f.get("size", 0) for f in selected_files)
        total_lines = sum(
            len(f.get("content", "").splitlines()) for f in selected_files
        )

        # Complexity analysis
        complexity_scores = []
        for file_info in selected_files:
            complexity = file_info.get("complexity")
            if complexity:
                complexity_scores.append(complexity)

        avg_complexity = (
            sum(complexity_scores) / len(complexity_scores) if complexity_scores else 1.0
        )

        return {
            "primary_language": primary_language,
            "languages": languages,
            "detected_frameworks": frameworks,
            "dependencies": dependencies,
            "total_files_processed": self.stats["total_files_processed"],
            "files_filtered": self.stats["files_filtered"],
            "selected_files_count": len(selected_files),
            "total_size": total_size,
            "total_lines": total_lines,
            "average_complexity": round(avg_complexity, 2),
            "complexity_distribution": self._analyze_complexity_distribution(
                complexity_scores
            ),
            "processing_stats": self.stats,
            "language_breakdown": self._generate_language_breakdown(selected_files),
            "file_type_distribution": self._analyze_file_types(selected_files),
        }

    def _analyze_complexity_distribution(
        self, complexity_scores: List[float]
    ) -> Dict[str, int]:
        """Analyze distribution of complexity scores"""
        if not complexity_scores:
            return {}

        distribution = {"simple": 0, "moderate": 0, "complex": 0, "very_complex": 0}

        for score in complexity_scores:
            if score <= 2.0:
                distribution["simple"] += 1
            elif score <= 4.0:
                distribution["moderate"] += 1
            elif score <= 7.0:
                distribution["complex"] += 1
            else:
                distribution["very_complex"] += 1

        return distribution

    def _generate_language_breakdown(
        self, files: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Generate detailed breakdown by language"""
        breakdown = defaultdict(lambda: {"files": 0, "size": 0, "lines": 0})

        for file_info in files:
            language = file_info.get("language", "unknown")
            size = file_info.get("size", 0)
            content = file_info.get("content", "")
            lines = len(content.splitlines()) if content else 0

            breakdown[language]["files"] += 1
            breakdown[language]["size"] += size
            breakdown[language]["lines"] += lines

        return dict(breakdown)

    def _analyze_file_types(self, files: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze distribution of file types"""
        type_counts = defaultdict(int)

        for file_info in files:
            path = file_info.get("path", "")
            if path:
                ext = Path(path).suffix.lower()
                type_counts[ext if ext else "no_extension"] += 1

        return dict(type_counts)

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of processing statistics"""
        return {
            "total_processed": self.stats["total_files_processed"],
            "filtered_out": self.stats["files_filtered"],
            "selected": self.stats["files_selected"],
            "languages_found": self.stats["languages_detected"],
            "frameworks_found": self.stats["frameworks_detected"],
            "processing_time": round(self.stats["processing_time"], 2),
            "filter_rate": (
                round(
                    (self.stats["files_filtered"] / self.stats["total_files_processed"])
                    * 100,
                    1,
                )
                if self.stats["total_files_processed"] > 0
                else 0
            ),
        }

    def reset_stats(self):
        """Reset processing statistics"""
        self.stats = {
            "total_files_processed": 0,
            "files_filtered": 0,
            "files_selected": 0,
            "processing_time": 0.0,
            "languages_detected": 0,
            "frameworks_detected": 0,
        }

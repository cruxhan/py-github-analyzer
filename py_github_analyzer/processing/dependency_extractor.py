# py_github_analyzer/processing/dependency_extractor.py
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set


class DependencyExtractor:
    def __init__(self):
        self.extractors = {
            "python": self._extract_python_deps,
            "javascript": self._extract_js_deps,
            "typescript": self._extract_js_deps,
            "java": self._extract_java_deps,
            "go": self._extract_go_deps,
            "rust": self._extract_rust_deps,
            "csharp": self._extract_csharp_deps,
        }

    def extract_dependencies(self, files: List[Dict[str, Any]], primary_language: str) -> List[str]:
        if primary_language not in self.extractors:
            return []
        extractor = self.extractors[primary_language]
        all_deps: Set[str] = set()
        for file_info in files:
            try:
                all_deps.update(extractor(file_info))
                if len(all_deps) > 100:
                    break
            except Exception:
                continue
        filtered = [d for d in all_deps if 1 < len(d) < 50 and not d.startswith(".")]
        return sorted(filtered)[:30]

    def _extract_python_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        deps: Set[str] = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()
        if filename in ("requirements.txt", "requirements-dev.txt", "dev-requirements.txt"):
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    m = re.match(r"^([a-zA-Z0-9_-]+)", line)
                    if m:
                        deps.add(m.group(1))
        elif filename == "setup.py":
            m = re.search(r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if m:
                for d in re.findall(r'["\']([a-zA-Z0-9_-]+)', m.group(1)):
                    deps.add(d)
        elif filename == "pyproject.toml":
            m = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if m:
                for d in re.findall(r'["\']([a-zA-Z0-9_-]+)', m.group(1)):
                    deps.add(d)
        elif filename.endswith(".py"):
            for match in re.findall(r"(?:^from\s+([a-zA-Z0-9_]+)|^import\s+([a-zA-Z0-9_]+))", content, re.MULTILINE):
                dep = match[0] or match[1]
                if dep and not dep.startswith("_"):
                    deps.add(dep)
        return deps

    def _extract_js_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        deps: Set[str] = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()
        if filename == "package.json":
            try:
                package_data = json.loads(content)
                for dep_type in ("dependencies", "devDependencies", "peerDependencies"):
                    if dep_type in package_data:
                        deps.update(package_data[dep_type].keys())
            except json.JSONDecodeError:
                pass
        elif filename.endswith((".js", ".ts", ".jsx", ".tsx")):
            patterns = [
                r'import.*?from\s+[\'"]([^\'"]+)[\'"]',
                r'require\([\'"]([^\'"]+)[\'"]\)',
                r'import\([\'"]([^\'"]+)[\'"]\)',
                r'import\s+[\'"]([^\'"]+)[\'"]',
            ]
            for pattern in patterns:
                for match in re.findall(pattern, content):
                    if not match.startswith("."):
                        base = match.split("/")[0]
                        if base.startswith("@"):
                            parts = match.split("/")
                            base = f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else base
                        deps.add(base)
        return deps

    def _extract_java_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        deps: Set[str] = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()
        if filename == "pom.xml":
            for m in re.findall(r"<artifactId>(.*?)</artifactId>", content):
                deps.add(m)
        elif filename in ("build.gradle", "build.gradle.kts"):
            for m in re.findall(r'(?:implementation|compile|api)\s+[\'"]([^:]+):([^:\'"]+)', content):
                deps.add(m[1])
        return deps

    def _extract_go_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        deps: Set[str] = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()
        if filename == "go.mod":
            for m in re.findall(r"require\s+([^\s]+)", content):
                deps.add(m)
        elif filename.endswith(".go"):
            for m in re.findall(r'import\s+(?:"([^"]+)"|`([^`]+)`)', content):
                deps.add(m[0] or m[1])
        return deps

    def _extract_rust_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        deps: Set[str] = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()
        if filename == "cargo.toml":
            m = re.search(r"\[dependencies\](.*?)(?:\[|$)", content, re.DOTALL)
            if m:
                for line in m.group(1).split("\n"):
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        deps.add(line.split("=")[0].strip())
        return deps

    def _extract_csharp_deps(self, file_info: Dict[str, Any]) -> Set[str]:
        deps: Set[str] = set()
        path = file_info.get("path", "")
        content = file_info.get("content", "")
        filename = Path(path).name.lower()
        if filename.endswith(".csproj"):
            for m in re.findall(r'<PackageReference\s+Include="([^"]+)"', content):
                deps.add(m)
        return deps

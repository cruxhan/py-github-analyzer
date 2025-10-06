"""

Metadata Generator for py-github-analyzer v1.0.0

Enhanced metadata generation with AI-optimized structure and comprehensive analysis

"""

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import Config
from .logger import AnalyzerLogger


def safe_size_calculation(size_value: Any) -> int:
    """Safely convert size value to integer, preventing TypeError"""
    try:
        if isinstance(size_value, str):
            # Handle string formats like "123KB", "45MB", or pure numbers
            import re

            numbers = re.findall(r"\d+\.?\d*", size_value)
            if numbers:
                return int(float(numbers[0]))
            return 0
        elif isinstance(size_value, (int, float)):
            return int(size_value)
        else:
            return 0
    except (ValueError, TypeError, IndexError):
        return 0


def safe_percentage_calculation(part: Any, total: Any) -> float:
    """Safely calculate percentage, preventing division errors"""
    try:
        part_num = safe_size_calculation(part)
        total_num = safe_size_calculation(total)
        if total_num > 0:
            return round((part_num / total_num) * 100, 1)
        return 0.0
    except:
        return 0.0


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


class MetadataGenerator:
    """Generate metadata for repository analysis - v1.0.0"""

    def __init__(self, logger: Optional[AnalyzerLogger] = None):
        self.logger = logger or AnalyzerLogger()

    def generate_metadata(
        self,
        files: List[Dict[str, Any]],
        processing_metadata: Dict[str, Any],
        repo_info: Dict[str, Any],
        repo_url: str,
    ) -> Dict[str, Any]:
        """Generate comprehensive metadata for repository analysis"""
        self.logger.debug("Generating comprehensive metadata...")

        # Ensure inputs are proper types
        if not isinstance(files, list):
            files = []
        if not isinstance(processing_metadata, dict):
            processing_metadata = {}
        if not isinstance(repo_info, dict):
            repo_info = {}

        # Extract repository name from URL or repo_info
        repo_name = self._extract_repo_name(repo_url, repo_info)

        # Calculate size information with clear distinction
        size_info = self._calculate_detailed_size_info(files, repo_info)

        # Generate metadata components
        metadata = {
            "repo": repo_name,
            "desc": self._extract_description(files, repo_info),
            "lang": self._detect_language_distribution(files, processing_metadata),
            "size": size_info,  # Enhanced size information
            "files": len(files),
            "main": self._extract_main_files(files, processing_metadata),
            "deps": self._extract_dependencies(files, processing_metadata),
            "created": int(time.time()),
            "version": Config.VERSION,
            "analysis_mode": "full" if files else "fallback",
        }

        # Add optional fields if available
        frameworks = processing_metadata.get("frameworks", [])
        if isinstance(frameworks, list) and frameworks:
            metadata["frameworks"] = frameworks[:5]  # Top 5 frameworks

        entry_points = processing_metadata.get("entry_points", [])
        if isinstance(entry_points, list) and entry_points:
            metadata["entry_points"] = entry_points[:5]  # Top 5 entry points

        if repo_info.get("license"):
            metadata["license"] = repo_info["license"]

        if repo_info.get("topics"):
            topics = repo_info["topics"]
            if isinstance(topics, list):
                metadata["topics"] = topics[:10]  # Top 10 topics

        self.logger.debug(f"Generated metadata with {len(metadata)} fields")
        return metadata

    def generate_compact_metadata(
        self,
        files: List[Dict[str, Any]],
        processing_metadata: Dict[str, Any],
        repo_info: Dict[str, Any],
        repo_url: str,
    ) -> Dict[str, Any]:
        """Generate compact metadata for efficient storage"""
        # Ensure inputs are proper types
        if not isinstance(files, list):
            files = []
        if not isinstance(processing_metadata, dict):
            processing_metadata = {}
        if not isinstance(repo_info, dict):
            repo_info = {}

        repo_name = self._extract_repo_name(repo_url, repo_info)
        size_info = self._calculate_detailed_size_info(files, repo_info)

        compact = {
            "repo": repo_name,
            "lang": self._detect_language_distribution(files, processing_metadata),
            "size": size_info["display_size"],  # Use display size for compact version
            "files": len(files),
            "main": self._extract_main_files(files, processing_metadata)[
                :3
            ],  # Top 3 only
            "deps": self._extract_dependencies(files, processing_metadata)[
                :10
            ],  # Top 10 only
        }

        # Add repository metadata if available
        if repo_info.get("private") is not None:
            compact["private"] = repo_info["private"]

        return compact

    def _extract_repo_name(self, repo_url: str, repo_info: Dict[str, Any]) -> str:
        """Extract repository name from URL or info"""
        # Try from repo_info first
        if isinstance(repo_info, dict):
            full_name = repo_info.get("full_name")
            if full_name and isinstance(full_name, str):
                return full_name

            name = repo_info.get("name")
            owner_info = repo_info.get("owner", {})
            if name and isinstance(owner_info, dict):
                owner_login = owner_info.get("login")
                if owner_login:
                    return f"{owner_login}/{name}"

        # Fallback: extract from URL
        try:
            from .utils import URLParser

            parsed = URLParser.parse_github_url(repo_url)
            return f"{parsed['owner']}/{parsed['repo']}"
        except:
            # Last resort: use URL as is
            return repo_url.replace("https://github.com/", "").replace(".git", "")

    def _extract_description(self, files: List[Dict[str, Any]], repo_info: Dict[str, Any]) -> str:
        """Extract repository description from README or repo info"""
        
        # 🔧 FIX: Safe description extraction with None handling
        if isinstance(repo_info, dict):
            repo_desc = repo_info.get('description', '')
            # 🔧 FIX: Ensure repo_desc is not None before calling strip()
            if repo_desc and isinstance(repo_desc, str):
                repo_desc = repo_desc.strip()
                if repo_desc:  # Only return if non-empty after stripping
                    return repo_desc
        
        # Look for README files...
        readme_patterns = ['readme', 'readme.md', 'readme.txt', 'readme.rst']
        readme_files = []
        
        if isinstance(files, list):
            for file_info in files:
                if not isinstance(file_info, dict):
                    continue
                path = file_info.get('path', '')
                if not path:
                    continue
                    
                # 🔧 FIX: Safe path handling
                try:
                    filename = Path(path).name.lower()
                    if any(filename.startswith(pattern) for pattern in readme_patterns):
                        readme_files.append(file_info)
                except Exception:
                    continue
        
        if readme_files:
            # If we found README files, use the first one...
            first_readme = readme_files[0]
            if isinstance(first_readme, dict):
                readme_content = first_readme.get('content', '')
                # 🔧 FIX: Ensure readme_content is not None before calling strip()
                if readme_content and isinstance(readme_content, str):
                    try:
                        lines = readme_content.strip().split('\n')
                        description_lines = []
                        
                        for line in lines:
                            line = line.strip()
                            
                            # Skip empty lines, titles starting with '#', and horizontal rules...
                            if (not line or line.startswith('#') or 
                                line.startswith('---') or line.startswith('===')):
                                continue
                                
                            description_lines.append(line)
                            
                            # Stop after collecting enough content...
                            if len(' '.join(description_lines)) > 150:
                                break
                        
                        if description_lines:
                            description = ' '.join(description_lines)
                            
                            # Truncate to reasonable length...
                            if len(description) > 200:
                                description = description[:197] + '...'
                            return description
                    except Exception:
                        pass  # Fall through to fallback
        
        # Fallback to generic description...
        return "GitHub repository analysis"


    def _detect_language_distribution(
        self, files: List[Dict[str, Any]], processing_metadata: Dict[str, Any]
    ) -> List[str]:
        """Detect and return language distribution"""
        languages = {}

        # Try to get languages from processing metadata first
        if isinstance(processing_metadata, dict):
            proc_languages = processing_metadata.get("languages", {})
            if isinstance(proc_languages, dict):
                languages = proc_languages

        # Fallback: detect from files directly
        if not languages and isinstance(files, list):
            language_sizes = {}
            total_size = 0

            for file_info in files:
                if not isinstance(file_info, dict):
                    continue

                path = file_info.get("path", "")
                size = safe_size_calculation(file_info.get("size", 0))

                if not path or size <= 0:
                    continue

                language = Config.get_language_from_extension(path)
                if language != "unknown":
                    language_sizes[language] = language_sizes.get(language, 0) + size
                    total_size += size

            # Convert to percentages
            if total_size > 0:
                for lang, size in language_sizes.items():
                    percentage = safe_percentage_calculation(size, total_size)
                    if percentage >= 5.0:  # Only include languages with ≥5%
                        languages[lang] = round(percentage, 1)

        # Convert to list format with proper capitalization
        language_list = []
        if isinstance(languages, dict):
            for lang, percentage in sorted(
                languages.items(), key=lambda x: x[1], reverse=True
            ):
                # Capitalize language names properly
                proper_name = {
                    "python": "Python",
                    "javascript": "JavaScript",
                    "typescript": "TypeScript",
                    "java": "Java",
                    "cpp": "C++",
                    "c": "C",
                    "csharp": "C#",
                    "go": "Go",
                    "rust": "Rust",
                    "php": "PHP",
                    "ruby": "Ruby",
                    "swift": "Swift",
                    "kotlin": "Kotlin",
                    "dart": "Dart",
                    "html": "HTML",
                    "css": "CSS",
                    "scss": "SCSS",
                    "less": "Less",
                    "sass": "Sass",
                    "markdown": "Markdown",
                    "yaml": "YAML",
                    "json": "JSON",
                    "xml": "XML",
                    "sql": "SQL",
                    "shell": "Shell",
                    "dockerfile": "Dockerfile",
                }.get(lang.lower(), lang.title())

                language_list.append(proper_name)

        # Fallback if no languages detected
        if not language_list:
            language_list = ["Unknown"]

        return language_list[:5]  # Top 5 languages

    def _calculate_detailed_size_info(
        self, files: List[Dict[str, Any]], repo_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive size information with clear distinction between
        repository size and analyzed source files size
        """
        size_info = {
            "repo_size": None,  # Full repository size (from GitHub API)
            "repo_size_kb": 0,  # Repository size in KB
            "source_size": None,  # Analyzed source files size
            "source_size_bytes": 0,  # Source files size in bytes
            "display_size": "0KB",  # Primary size for display
            "size_note": "source",  # Which size is being displayed
        }

        # Step 1: Get repository size from GitHub API (includes .git directory, binaries, etc.)
        if isinstance(repo_info, dict):
            repo_size_kb = safe_size_calculation(repo_info.get("size", 0))
            if repo_size_kb > 0:
                size_info["repo_size_kb"] = repo_size_kb
                if repo_size_kb < 1024:
                    size_info["repo_size"] = f"{repo_size_kb}KB"
                else:
                    size_info["repo_size"] = f"{repo_size_kb / 1024:.1f}MB"

        # Step 2: Calculate analyzed source files size
        if isinstance(files, list):
            total_bytes = 0
            for file_info in files:
                if isinstance(file_info, dict):
                    size = safe_size_calculation(file_info.get("size", 0))
                    total_bytes += size

            size_info["source_size_bytes"] = total_bytes
            if total_bytes > 0:
                size_info["source_size"] = format_size(total_bytes)

        # Step 3: Determine which size to display as primary
        if size_info["repo_size"] and size_info["source_size"]:
            # Both available - use repository size for display but note the difference
            size_info["display_size"] = size_info["repo_size"]
            size_info["size_note"] = "repo"

            # Add helpful note about the difference
            repo_mb = (
                size_info["repo_size_kb"] / 1024
                if size_info["repo_size_kb"] >= 1024
                else 0
            )
            source_mb = size_info["source_size_bytes"] / (1024 * 1024)

            if repo_mb > 0 and source_mb > 0 and repo_mb > source_mb * 2:
                # Significant difference - add explanation
                size_info["size_breakdown"] = {
                    "total_repo": size_info["repo_size"],
                    "analyzed_source": size_info["source_size"],
                    "note": "Total repository size includes .git history, binaries, and other files",
                }

        elif size_info["source_size"]:
            # Only source size available
            size_info["display_size"] = size_info["source_size"]
            size_info["size_note"] = "source"

        elif size_info["repo_size"]:
            # Only repository size available
            size_info["display_size"] = size_info["repo_size"]
            size_info["size_note"] = "repo"

        else:
            # No size information available
            size_info["display_size"] = "0KB"
            size_info["size_note"] = "unknown"

        return size_info

    def _extract_main_files(
        self, files: List[Dict[str, Any]], processing_metadata: Dict[str, Any]
    ) -> List[str]:
        """Extract main/entry point files"""
        main_files = []

        # Get entry points from processing metadata
        if isinstance(processing_metadata, dict):
            entry_points = processing_metadata.get("entry_points", [])
            if isinstance(entry_points, list):
                main_files.extend(entry_points)

        # Look for additional main files
        main_patterns = ["main", "index", "app", "__main__", "run", "start"]

        if isinstance(files, list):
            for file_info in files:
                if not isinstance(file_info, dict):
                    continue

                path = file_info.get("path", "")
                if not path:
                    continue

                filename = Path(path).stem.lower()

                # Check if filename matches main patterns
                if any(pattern in filename for pattern in main_patterns):
                    if path not in main_files:  # Avoid duplicates
                        main_files.append(path)

        # Sort by priority
        main_files_with_priority = []
        for file_path in main_files:
            priority = Config.get_file_priority(file_path)
            main_files_with_priority.append((file_path, priority))

        # Sort by priority (highest first) and return paths only
        main_files_with_priority.sort(key=lambda x: x[1], reverse=True)
        return [path for path, _ in main_files_with_priority[:10]]  # Top 10 main files

    def _extract_dependencies(
        self, files: List[Dict[str, Any]], processing_metadata: Dict[str, Any]
    ) -> List[str]:
        """Extract dependencies from processing metadata and files"""
        dependencies = set()

        # Get dependencies from processing metadata
        if isinstance(processing_metadata, dict):
            proc_deps = processing_metadata.get("dependencies", [])
            if isinstance(proc_deps, list):
                dependencies.update(proc_deps)

        # Extract additional dependencies from specific files
        if isinstance(files, list):
            for file_info in files:
                if not isinstance(file_info, dict):
                    continue

                path = file_info.get("path", "")
                content = file_info.get("content", "")

                if not path or not content:
                    continue

                filename = Path(path).name.lower()

                # Check package files
                if filename in [
                    "requirements.txt",
                    "package.json",
                    "composer.json",
                    "pubspec.yaml",
                    "cargo.toml",
                    "go.mod",
                    "pom.xml",
                    "build.gradle",
                ]:
                    file_deps = self._extract_dependencies_from_file(content, filename)
                    dependencies.update(file_deps)

        # Clean and limit dependencies
        cleaned_deps = []
        for dep in dependencies:
            if isinstance(dep, str) and len(dep) > 1 and not dep.startswith("#"):
                # Remove version specifiers and clean up
                clean_dep = re.split(r"[>=<!~^]", dep)[0].strip()
                if len(clean_dep) > 1:
                    cleaned_deps.append(clean_dep)

        return sorted(list(set(cleaned_deps)))[:20]  # Top 20 unique dependencies

    def _extract_dependencies_from_file(self, content: str, filename: str) -> List[str]:
        """Extract dependencies from specific package files"""
        dependencies = []

        try:
            if filename == "package.json":
                data = json.loads(content)
                deps = {}
                deps.update(data.get("dependencies", {}))
                deps.update(data.get("devDependencies", {}))
                deps.update(data.get("peerDependencies", {}))
                dependencies.extend(deps.keys())

            elif filename == "requirements.txt":
                lines = content.split("\n")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        # Extract package name before ==, >=, etc.
                        package = re.split(r"[>=<!~]", line)[0].strip()
                        if package:
                            dependencies.append(package)

            elif filename == "composer.json":
                data = json.loads(content)
                deps = {}
                deps.update(data.get("require", {}))
                deps.update(data.get("require-dev", {}))
                dependencies.extend(deps.keys())

            elif filename == "cargo.toml":
                # Simple TOML parsing for Rust dependencies
                lines = content.split("\n")
                in_dependencies = False

                for line in lines:
                    line = line.strip()
                    if line == "[dependencies]":
                        in_dependencies = True
                        continue
                    elif line.startswith("[") and in_dependencies:
                        in_dependencies = False
                        continue

                    if in_dependencies and "=" in line:
                        dep_name = line.split("=")[0].strip()
                        dependencies.append(dep_name)

            elif filename == "go.mod":
                # Parse Go modules
                lines = content.split("\n")
                in_require = False

                for line in lines:
                    line = line.strip()
                    if line.startswith("require ("):
                        in_require = True
                        continue
                    elif line.startswith("require "):
                        parts = line.split()
                        if len(parts) >= 2:
                            dependencies.append(parts[1])
                        continue
                    elif in_require and line == ")":
                        in_require = False
                    elif in_require:
                        parts = line.split()
                        if parts:
                            dependencies.append(parts[0])

            elif filename in ["pom.xml"]:
                # Basic XML parsing for Maven dependencies
                import re

                artifact_pattern = r"<artifactId>(.*?)</artifactId>"
                matches = re.findall(artifact_pattern, content)
                dependencies.extend(matches)

            elif filename in ["build.gradle"]:
                # Basic Gradle parsing
                lines = content.split("\n")
                for line in lines:
                    line = line.strip()
                    if any(
                        keyword in line
                        for keyword in [
                            "implementation",
                            "compile",
                            "api",
                            "testImplementation",
                        ]
                    ):
                        if '"' in line:
                            # Extract dependency name
                            parts = line.split('"')
                            if len(parts) >= 2:
                                dep = parts[1]
                                if ":" in dep:
                                    # Format: group:name:version
                                    dep_parts = dep.split(":")
                                    if len(dep_parts) >= 2:
                                        dependencies.append(
                                            f"{dep_parts[0]}:{dep_parts[1]}"
                                        )

        except (json.JSONDecodeError, Exception) as e:
            self.logger.debug(f"Error parsing {filename}: {e}")

        return dependencies

    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate metadata structure and content"""
        required_fields = ["repo", "desc", "lang", "size", "files", "main", "deps"]

        for field in required_fields:
            if field not in metadata:
                self.logger.warning(f"Missing required metadata field: {field}")
                return False

        # Validate field types
        if not isinstance(metadata["repo"], str):
            self.logger.warning("Invalid repo field type")
            return False

        if not isinstance(metadata["lang"], list):
            self.logger.warning("Invalid lang field type")
            return False

        if not isinstance(metadata["files"], int):
            self.logger.warning("Invalid files field type")
            return False

        if not isinstance(metadata["main"], list):
            self.logger.warning("Invalid main field type")
            return False

        if not isinstance(metadata["deps"], list):
            self.logger.warning("Invalid deps field type")
            return False

        return True

    def optimize_metadata_size(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize metadata for minimal size"""
        # Keep essential fields only
        essential_fields = ["repo", "desc", "lang", "size", "files", "main", "deps"]
        optimized = {}

        for field in essential_fields:
            if field in metadata:
                value = metadata[field]

                # Optimize specific fields
                if field == "desc" and isinstance(value, str) and len(value) > 100:
                    # Truncate description
                    optimized[field] = value[:97] + "..."
                elif field == "main" and isinstance(value, list) and len(value) > 3:
                    # Limit main files to top 3
                    optimized[field] = value[:3]
                elif field == "deps" and isinstance(value, list) and len(value) > 10:
                    # Limit dependencies to top 10
                    optimized[field] = value[:10]
                else:
                    optimized[field] = value

        return optimized

    def get_size_summary(self, metadata: Dict[str, Any]) -> str:
        """Get a human-readable summary of repository size information"""
        size_info = metadata.get("size", {})

        if isinstance(size_info, dict):
            if "size_breakdown" in size_info:
                return (
                    f"Repository: {size_info['size_breakdown']['total_repo']}, "
                    f"Source files analyzed: {size_info['size_breakdown']['analyzed_source']}"
                )
            else:
                display_size = size_info.get("display_size", "Unknown")
                note = size_info.get("size_note", "unknown")

                if note == "repo":
                    return f"Total repository size: {display_size}"
                elif note == "source":
                    return f"Analyzed source files: {display_size}"
                else:
                    return f"Size: {display_size}"

        # Fallback for old format
        return f"Size: {size_info}" if isinstance(size_info, str) else "Size: Unknown"

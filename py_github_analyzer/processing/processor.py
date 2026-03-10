# py_github_analyzer/processing/processor.py
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..config import Config
from ..logger import AnalyzerLogger
from .dependency_extractor import DependencyExtractor
from .file_prioritizer import FilePrioritizer
from .language_detector import LanguageDetector


class FileProcessor:
    def __init__(self, logger: Optional[AnalyzerLogger] = None):
        self._logger = logger or AnalyzerLogger()
        self.language_detector = LanguageDetector()
        self.dependency_extractor = DependencyExtractor()
        self.file_prioritizer = FilePrioritizer(self._logger)
        self.detector = self.language_detector
        self.prioritizer = self.file_prioritizer
        self.stats: Dict[str, Any] = {
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
        start_time = time.time()
        context = context or {}
        self._logger.info(f"Processing {len(files)} files...")
        self.stats["total_files_processed"] = len(files)

        valid_files = self._apply_basic_filtering(files)
        self._logger.info(f"After basic filtering: {len(valid_files)} files")
        self.stats["files_filtered"] = len(files) - len(valid_files)

        if not valid_files:
            return [], {"error": "No valid files to process"}

        self._logger.info("Analyzing languages...")
        languages = self.language_detector.detect_languages(valid_files)
        primary_language = next(iter(languages.keys())) if languages else "unknown"
        self.stats["languages_detected"] = len(languages)
        self._logger.info(f"Primary language: {primary_language}")

        self._logger.info("Detecting frameworks...")
        frameworks = self.language_detector.detect_frameworks(valid_files, primary_language)
        self.stats["frameworks_detected"] = len(frameworks)
        if frameworks:
            self._logger.info(f"Detected frameworks: {frameworks}")

        self._logger.info("Extracting dependencies...")
        dependencies = self.dependency_extractor.extract_dependencies(valid_files, primary_language)
        if dependencies:
            self._logger.info(f"Found {len(dependencies)} dependencies")

        self._logger.info("Prioritizing files...")
        prioritized_files = self.file_prioritizer.prioritize_files(valid_files, primary_language, context)

        selected_files = self._perform_smart_selection(prioritized_files, context)
        self.stats["files_selected"] = len(selected_files)

        processing_time = time.time() - start_time
        self.stats["processing_time"] = processing_time
        self._logger.info(f"Processing complete: {len(selected_files)} files selected in {processing_time:.2f}s")

        analysis_info = self._generate_analysis_info(selected_files, languages, frameworks, dependencies, primary_language)
        return selected_files, analysis_info

    def _apply_basic_filtering(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        valid = []
        for file_info in files:
            path = file_info.get("path", "")
            size = file_info.get("size", 0)
            content = file_info.get("content", "")
            if not self._is_valid_path(path):
                continue
            if size > Config.MAX_FILE_SIZE:
                self._logger.debug(f"Skipping oversized file: {path} ({size} bytes)")
                continue
            if Config.should_skip_file(path):
                continue
            if self._is_likely_binary(path, content):
                continue
            if size == 0 and not self._is_important_empty_file(path):
                continue
            valid.append(file_info)
        return valid

    def _is_valid_path(self, path: str) -> bool:
        from ..utils import ValidationUtils
        return ValidationUtils.validate_file_path(path)

    def _is_likely_binary(self, path: str, content: str) -> bool:
        if not path:
            return False
        binary_exts = {
            ".exe", ".dll", ".so", ".dylib", ".bin", ".img", ".iso",
            ".zip", ".tar", ".gz", ".rar", ".7z",
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".ico",
            ".mp3", ".mp4", ".avi", ".mov",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        }
        if Path(path).suffix.lower() in binary_exts:
            return True
        if content:
            if "\x00" in content:
                return True
            try:
                content.encode("utf-8")
                non_printable = sum(1 for c in content[:1000] if ord(c) < 32 and c not in "\n\r\t")
                if non_printable > len(content[:1000]) * 0.3:
                    return True
            except UnicodeEncodeError:
                return True
        return False

    def _is_important_empty_file(self, path: str) -> bool:
        return Path(path).name.lower() in {"__init__.py", ".gitkeep", ".keep"}

    def _perform_smart_selection(
        self, prioritized_files: List[Dict[str, Any]], context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if not prioritized_files:
            return []
        selected: List[Dict[str, Any]] = []
        total_size = 0
        size_limit = context.get("max_total_size", Config.MAX_TOTAL_SIZE_BYTES)
        count_limit = context.get("max_files", Config.MAX_FILES_COUNT)
        tiers = self._group_by_priority_tiers(prioritized_files)
        for tier_files in tiers.values():
            for file_info in tier_files:
                file_size = file_info.get("size", 0)
                if total_size + file_size > size_limit:
                    if file_size < size_limit * 0.1:
                        continue
                    else:
                        break
                if len(selected) >= count_limit:
                    break
                selected.append(file_info)
                total_size += file_size
            if len(selected) >= count_limit or total_size >= size_limit * 0.9:
                break
        self._logger.info(f"Selected {len(selected)} files, total size: {total_size:,} bytes")
        return selected

    def _group_by_priority_tiers(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        tiers: Dict[str, List[Dict[str, Any]]] = {"critical": [], "high": [], "medium": [], "low": []}
        for f in files:
            p = f.get("priority", 100)
            if p >= 800:
                tiers["critical"].append(f)
            elif p >= 600:
                tiers["high"].append(f)
            elif p >= 400:
                tiers["medium"].append(f)
            else:
                tiers["low"].append(f)
        return tiers

    def _generate_analysis_info(
        self,
        selected_files: List[Dict[str, Any]],
        languages: Dict[str, float],
        frameworks: List[str],
        dependencies: List[str],
        primary_language: str,
    ) -> Dict[str, Any]:
        total_size = sum(f.get("size", 0) for f in selected_files)
        total_lines = sum(len(f.get("content", "").splitlines()) for f in selected_files)
        complexity_scores = [f["complexity"] for f in selected_files if f.get("complexity")]
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 1.0
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
            "complexity_distribution": self._complexity_distribution(complexity_scores),
            "processing_stats": self.stats,
            "language_breakdown": self._language_breakdown(selected_files),
            "file_type_distribution": self._file_type_distribution(selected_files),
        }

    def _complexity_distribution(self, scores: List[float]) -> Dict[str, int]:
        dist = {"simple": 0, "moderate": 0, "complex": 0, "very_complex": 0}
        for s in scores:
            if s <= 2.0:
                dist["simple"] += 1
            elif s <= 4.0:
                dist["moderate"] += 1
            elif s <= 7.0:
                dist["complex"] += 1
            else:
                dist["very_complex"] += 1
        return dist

    def _language_breakdown(self, files: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        breakdown: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"files": 0, "size": 0, "lines": 0})
        for f in files:
            lang = f.get("language", "unknown")
            breakdown[lang]["files"] += 1
            breakdown[lang]["size"] += f.get("size", 0)
            breakdown[lang]["lines"] += len(f.get("content", "").splitlines())
        return dict(breakdown)

    def _file_type_distribution(self, files: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for f in files:
            ext = Path(f.get("path", "")).suffix.lower()
            counts[ext if ext else "no_extension"] += 1
        return dict(counts)

    def get_processing_summary(self) -> Dict[str, Any]:
        total = self.stats["total_files_processed"]
        return {
            "total_processed": total,
            "filtered_out": self.stats["files_filtered"],
            "selected": self.stats["files_selected"],
            "languages_found": self.stats["languages_detected"],
            "frameworks_found": self.stats["frameworks_detected"],
            "processing_time": round(self.stats["processing_time"], 2),
            "filter_rate": round(self.stats["files_filtered"] / total * 100, 1) if total > 0 else 0,
        }

    def reset_stats(self):
        self.stats = {
            "total_files_processed": 0,
            "files_filtered": 0,
            "files_selected": 0,
            "processing_time": 0.0,
            "languages_detected": 0,
            "frameworks_detected": 0,
        }

# py_github_analyzer/analysis/fallback_strategy.py
import time
from typing import Any, Dict, List, Optional, Tuple

from ..async_github_client import AsyncGitHubClient
from ..config import Config
from ..logger import AnalyzerLogger
from .strategy import AnalysisStrategy


class FallbackAnalysisStrategy(AnalysisStrategy):
    def __init__(self, client: AsyncGitHubClient, logger: AnalyzerLogger):
        self._client = client
        self._logger = logger

    async def execute(self, owner: str, repo: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        try:
            repo_info = await self._client.get_repository_info(owner, repo, safe_mode=True)
        except Exception as e:
            self._logger.warning(f"Could not get repository info: {e}")
            repo_info = {
                "name": repo,
                "full_name": f"{owner}/{repo}",
                "owner": {"login": owner},
                "description": "No description available",
                "language": None,
                "size": 0,
                "created_at": None,
                "updated_at": None,
                "stargazers_count": 0,
                "forks_count": 0,
                "private": True,
            }
        return [], repo_info

    def build_metadata(
        self,
        owner: str,
        repo: str,
        repo_info: Dict[str, Any],
        original_error_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            description = repo_info.get("description") if isinstance(repo_info, dict) else None
            language = str(repo_info["language"]) if isinstance(repo_info, dict) and repo_info.get("language") else "Unknown"
            try:
                size = int(repo_info.get("size", 0)) if isinstance(repo_info, dict) else 0
            except (ValueError, TypeError):
                size = 0

            metadata: Dict[str, Any] = {
                "repo": f"{owner}/{repo}",
                "owner": owner,
                "name": repo,
                "description": description,
                "lang": [language] if language != "Unknown" else ["Unknown"],
                "size": size,
                "created": repo_info.get("created_at") if isinstance(repo_info, dict) else None,
                "updated": repo_info.get("updated_at") if isinstance(repo_info, dict) else None,
                "stars": repo_info.get("stargazers_count", 0) if isinstance(repo_info, dict) else 0,
                "forks": repo_info.get("forks_count", 0) if isinstance(repo_info, dict) else 0,
                "fallback_mode": True,
                "analysis_mode": "basic_metadata_only",
                "files": 0,
                "main": [],
                "deps": [],
                "created_at": int(time.time()),
                "version": Config.VERSION,
            }
            if original_error_info:
                metadata["original_failure"] = original_error_info
            return metadata
        except Exception as e:
            self._logger.error(f"Safe fallback metadata generation failed: {e}")
            return {
                "repo": f"{owner}/{repo}",
                "owner": owner,
                "name": repo,
                "description": "Analysis failed - minimal data only",
                "lang": ["Unknown"],
                "size": 0,
                "fallback_mode": True,
                "analysis_mode": "emergency_fallback",
                "files": 0,
                "main": [],
                "deps": [],
                "created_at": int(time.time()),
                "version": Config.VERSION,
                "error": f"Metadata generation error: {e}",
            }

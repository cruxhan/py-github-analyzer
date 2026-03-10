# py_github_analyzer/analysis/api_strategy.py
from typing import Any, Dict, List, Tuple

from ..async_github_client import AsyncGitHubClient
from ..logger import AnalyzerLogger
from .strategy import AnalysisStrategy


class ApiAnalysisStrategy(AnalysisStrategy):
    def __init__(self, client: AsyncGitHubClient, logger: AnalyzerLogger):
        self._client = client
        self._logger = logger

    async def execute(self, owner: str, repo: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        repo_info = await self._client.get_repository_info(owner, repo)
        contents = await self._client.get_repository_contents(owner, repo, recursive=True)

        file_paths = [item["path"] for item in contents if item["type"] == "file"]
        batch_results = await self._client.batch_download_files(owner, repo, file_paths, safe_mode=False)

        files = [
            {
                "path": file_path,
                "content": file_data.get("content", ""),
                "size": file_data.get("size", 0),
                "type": "file",
                "sha": file_data.get("sha", ""),
            }
            for file_path, file_data in batch_results.items()
            if file_data
        ]

        self._logger.debug(f"API analysis extracted {len(files)} files")
        return files, repo_info or {}

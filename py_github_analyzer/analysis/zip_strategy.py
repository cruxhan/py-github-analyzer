# py_github_analyzer/analysis/zip_strategy.py
from typing import Any, Dict, List, Tuple

from ..async_github_client import AsyncGitHubClient
from ..exceptions import NetworkError
from ..logger import AnalyzerLogger
from .strategy import AnalysisStrategy


class ZipAnalysisStrategy(AnalysisStrategy):
    def __init__(self, client: AsyncGitHubClient, logger: AnalyzerLogger):
        self._client = client
        self._logger = logger

    async def execute(self, owner: str, repo: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        zip_data = await self._client.download_zip_archive(owner, repo)
        if not zip_data:
            raise NetworkError("ZIP download failed - no data received")

        files = [
            {"path": file_path, "content": file_content, "size": len(file_content), "type": "file"}
            for file_path, file_content in zip_data.items()
        ]

        repo_info = {
            "name": repo,
            "full_name": f"{owner}/{repo}",
            "owner": {"login": owner},
            "default_branch": "main",
        }

        self._logger.debug(f"ZIP analysis extracted {len(files)} files")
        return files, repo_info

# py_github_analyzer/analysis/strategy.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class AnalysisStrategy(ABC):
    @abstractmethod
    async def execute(self, owner: str, repo: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        ...

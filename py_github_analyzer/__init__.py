#!/usr/bin/env python3
"""
py-github-analyzer: High-performance async GitHub repository analyzer
with AI-optimized code extraction and smart .env file support
"""

import os
from typing import Any, Dict

try:
    from .async_github_client import AsyncGitHubClient
    from .config import Config
    from .core import (
        EmptyRepositoryError,
        GitHubRepositoryAnalyzer,
        analyze_repository_async,
    )
    from .exceptions import *
    from .logger import get_logger
    from .utils import TokenUtils, URLParser
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required dependencies are installed.")
    raise

__version__ = "1.0.0"
__author__ = "Han Jun-hee"
__email__ = "createbrain2heart@gmail.com"
__description__ = "High-performance async GitHub repository analyzer with AI-optimized code extraction"

__all__ = [
    "analyze_repository_async",
    "GitHubRepositoryAnalyzer",
    "AsyncGitHubClient",
    "get_logger",
    "get_version",
    "check_env_file",
    "get_token_sources",
    "URLParser",
    "TokenUtils",
    "Config",
    "EmptyRepositoryError",
    "GitHubAnalyzerError",
    "NetworkError",
    "AuthenticationError",
    "RateLimitError",
    "RepositoryNotFoundError",
    "ValidationError",
]


def get_version() -> str:
    """Get package version"""
    return __version__


def check_env_file() -> Dict[str, Any]:
    """Check .env file status and token availability"""
    try:
        if TokenUtils:
            env_files = TokenUtils._find_env_files()
            env_vars = TokenUtils._load_env_variables()
            
            token_sources = []
            for env_var in ["GITHUB_TOKEN", "GH_TOKEN"]:
                if os.environ.get(env_var):
                    token_sources.append(f"{env_var} (system)")
                if env_vars.get(env_var):
                    token_sources.append(f"{env_var} (.env)")
            
            token = TokenUtils.get_github_token()
            token_info = (
                TokenUtils.get_token_info(token) if token else {"status": "none"}
            )
            
            return {
                "env_files_found": len(env_files),
                "env_file_paths": env_files,
                "token_sources": token_sources,
                "token_status": token_info.get("status", "unknown"),
                "token_type": token_info.get("type", "unknown") if token else "none",
            }
        else:
            return {
                "env_files_found": 0,
                "env_file_paths": [],
                "token_sources": [],
                "token_status": "utils_unavailable",
                "token_type": "none",
            }
    except Exception as e:
        return {
            "env_files_found": 0,
            "env_file_paths": [],
            "token_sources": [],
            "token_status": "error",
            "token_type": "none",
            "error": str(e),
        }


def get_token_sources() -> Dict[str, Any]:
    """Get available token sources"""
    try:
        if not TokenUtils:
            return {"sources": [], "error": "TokenUtils not available"}
        
        sources = []
        
        # Check system environment variables
        for env_var in ["GITHUB_TOKEN", "GH_TOKEN"]:
            if os.environ.get(env_var):
                sources.append({
                    "type": "system_environment",
                    "variable": env_var,
                    "available": True,
                })
        
        # Check .env files
        env_files = TokenUtils._find_env_files()
        env_vars = TokenUtils._load_env_variables()
        
        for env_var in ["GITHUB_TOKEN", "GH_TOKEN"]:
            if env_vars.get(env_var):
                sources.append({
                    "type": "env_file",
                    "variable": env_var,
                    "available": True,
                    "file_count": len(env_files),
                })
        
        return {"sources": sources}
    except Exception as e:
        return {"sources": [], "error": str(e)}


def print_banner():
    """Print package banner"""
    banner = f"""
╭─────────────────────────────────────────────────────────────────╮
│ 🚀 py-github-analyzer v{__version__}                               │
│                                                                 │
│ High-performance async GitHub repository analyzer               │
│ with AI-optimized code extraction and smart .env support       │
│                                                                 │
│ Author: {__author__}                                    │
│ Email: {__email__}                         │
╰─────────────────────────────────────────────────────────────────╯
"""
    print(banner)


if __name__ == "__main__":
    print_banner()
    print("\n🔧 Quick usage:")
    print("  Python API: import py_github_analyzer as pga")
    print("  CLI usage: py-github-analyzer https://github.com/user/repo")
    print("  .env check: pga.check_env_file()")

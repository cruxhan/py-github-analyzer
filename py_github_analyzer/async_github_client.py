#!/usr/bin/env python3
"""
Async GitHub Client for py-github-analyzer v1.0.0
High-performance asynchronous GitHub API interaction with optimized access flow
"""

import asyncio
import time
import zipfile
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from .config import Config
from .exceptions import (
    AuthenticationError,
    NetworkError,
    PrivateRepositoryError,
    RateLimitExceededError,
    RepositoryNotFoundError,
    RepositoryTooLargeError,
)
from .exceptions import TimeoutError as AnalyzerTimeoutError
from .exceptions import (
    create_private_repo_guidance_message,
    create_repo_not_found_message,
    handle_github_api_error,
)
from .logger import AnalyzerLogger
from .utils import URLParser, ValidationUtils


class AsyncRateLimitManager:
    """Async-safe GitHub API rate limit management with race condition protection"""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.limit = 5000 if token else 60
        self.remaining = self.limit
        self.reset_time = int(time.time()) + 3600
        self._lock = asyncio.Lock()
        self._api_call_lock = asyncio.Lock()  # Lock to protect the entire API call process

    async def update_from_headers(self, headers: Dict[str, str]):
        """Update rate limit info from response headers"""
        async with self._lock:
            self.limit = int(headers.get("x-ratelimit-limit", self.limit))
            self.remaining = int(headers.get("x-ratelimit-remaining", self.remaining))
            self.reset_time = int(headers.get("x-ratelimit-reset", self.reset_time))

    async def check_rate_limit(self, required_calls: int = 1) -> bool:
        """Check if we have enough API calls remaining"""
        async with self._lock:
            return self.remaining >= (required_calls + Config.RATE_LIMIT_BUFFER)

    async def consume_calls(self, count: int = 1):
        """Consume API calls from remaining count"""
        async with self._lock:
            self.remaining = max(0, self.remaining - count)

    def wait_time_until_reset(self) -> int:
        """Calculate wait time until rate limit resets"""
        return max(0, self.reset_time - int(time.time()))

    async def wait_for_rate_limit_reset(self):
        """Wait for rate limit to reset if necessary"""
        wait_time = self.wait_time_until_reset()
        if wait_time > 0 and self.remaining <= Config.RATE_LIMIT_BUFFER:
            await asyncio.sleep(min(wait_time, 300))  # Max 5 minutes wait

    async def execute_api_call(self, api_call_func, required_calls: int = 1):
        """
        Execute API call with atomic rate limit management
        This prevents race conditions by making the entire check-call-update process atomic
        """
        async with self._api_call_lock:
            # Step 1: Check rate limit
            if not await self.check_rate_limit(required_calls):
                await self.wait_for_rate_limit_reset()
                # Re-check after waiting
                if not await self.check_rate_limit(required_calls):
                    raise RateLimitExceededError(
                        "Rate limit still exceeded after waiting",
                        reset_time=self.reset_time,
                        remaining=self.remaining,
                    )

            # Step 2: Execute API call
            try:
                response = await api_call_func()
                # Step 3: Update rate limit info from response headers
                await self.update_from_headers(dict(response.headers))
                await self.consume_calls(required_calls)
                return response
            except Exception as e:
                # If API call failed, don't consume rate limit calls
                raise e

    async def track_safe_api_call(self, response: "httpx.Response"):
        """
        Track API calls made in safe mode (without full rate limit protection)
        This helps maintain accurate rate limit tracking even for safe mode calls
        """
        try:
            # Update rate limit info from response headers if available
            if hasattr(response, "headers") and response.headers:
                await self.update_from_headers(dict(response.headers))
            # Consume the call that was made
            await self.consume_calls(1)
        except Exception:
            # If we can't track it precisely, at least consume one call
            await self.consume_calls(1)


class AsyncGitHubSession:
    """Async HTTP session for GitHub API using httpx"""

    def __init__(self, token: Optional[str] = None, timeout: int = 30):
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx library is required for async operations. Install with: pip install httpx"
            )

        self.token = token
        self.timeout = timeout

        # Setup HTTP headers for GitHub API with token optimization
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "py-github-analyzer/1.0.0",
        }

        if self.token:
            # Token optimization: Use appropriate authentication method based on token type
            if self.token.startswith('github_pat_'):
                # Fine-grained Token: Use Bearer authentication (optimal for github_pat_*)
                headers["Authorization"] = f"Bearer {self.token}"
            else:
                # Classic Token (ghp_*): Use token authentication (standard for classic tokens)
                headers["Authorization"] = f"token {self.token}"

        # Create httpx client with enhanced connection pooling
        limits = httpx.Limits(
            max_keepalive_connections=50, max_connections=200, keepalive_expiry=30
        )
        timeout_config = httpx.Timeout(timeout)
        self.client = httpx.AsyncClient(
            headers=headers,
            timeout=timeout_config,
            limits=limits,
            follow_redirects=True,
        )

    def _get_token_performance_profile(self) -> Dict[str, Any]:
        """Get token-specific performance profile for optimized processing"""
        if not self.token:
            return {'batch_size': 3, 'delay': 1.0, 'performance': 'limited'}
        
        if self.token.startswith('github_pat_'):
            # Fine-grained Token: Moderate performance settings based on real analysis
            return {'batch_size': 4, 'delay': 0.8, 'performance': 'moderate'}
        elif self.token.startswith('ghp_'):
            # Classic Token: Fast performance settings based on real analysis
            return {'batch_size': 10, 'delay': 0.1, 'performance': 'fast'}
        else:
            # Unknown token format: Conservative defaults
            return {'batch_size': 3, 'delay': 1.0, 'performance': 'unknown'}

    async def request(
        self, method: str, url: str, raise_on_error: bool = True, **kwargs
    ) -> httpx.Response:
        """Make async HTTP request with optional error handling"""
        try:
            response = await self.client.request(method, url, **kwargs)

            # Handle GitHub API errors only if requested
            if raise_on_error and not response.is_success:
                error_data = None
                try:
                    if response.content:
                        error_data = response.json()
                except:
                    pass
                error = handle_github_api_error(response.status_code, error_data, url)
                raise error

            return response

        except httpx.TimeoutException:
            raise AnalyzerTimeoutError(
                f"Request timeout after {self.timeout} seconds", self.timeout
            )
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection error: {e}")
        except httpx.HTTPError as e:
            raise NetworkError(f"HTTP error: {e}")

    async def get(
        self, url: str, raise_on_error: bool = True, **kwargs
    ) -> httpx.Response:
        """GET request wrapper"""
        return await self.request("GET", url, raise_on_error=raise_on_error, **kwargs)

    async def close(self):
        """Close HTTP session"""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class AsyncGitHubClient:
    """High-performance async GitHub client with optimized parallel processing"""

    def __init__(
        self, token: Optional[str] = None, logger: Optional[AnalyzerLogger] = None
    ):
        self.token = token
        self.logger = logger or AnalyzerLogger()
        self.rate_limit_manager = AsyncRateLimitManager(token)

        # Initialize session immediately in __init__
        self.session = AsyncGitHubSession(self.token)

        # Enhanced concurrency limits based on token availability
        max_concurrent = 100 if self.token else 20
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def _get_token_performance_profile(self) -> Dict[str, Any]:
        """Get token-specific performance profile for batch operations"""
        return self.session._get_token_performance_profile()

    async def __aenter__(self):
        # Session is already initialized when entering context manager
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_repository_info(
        self, owner: str, repo: str, safe_mode: bool = False
    ) -> Dict[str, Any]:
        """Get basic repository information with enhanced safe mode rate limit tracking"""
        url = URLParser.build_api_url(owner, repo, "")

        try:
            if safe_mode:
                # Safe mode: faster but still track rate limit usage
                response = await self.session.get(url, raise_on_error=False)
                # Track the API call even in safe mode to maintain accurate rate limit info
                await self.rate_limit_manager.track_safe_api_call(response)

                if not response.is_success:
                    return {
                        "name": repo,
                        "full_name": f"{owner}/{repo}",
                        "description": "",
                        "language": "Unknown",
                        "size": 0,
                        "default_branch": "main",
                        "private": None,
                    }
            else:
                # Use atomic rate limit management for API calls
                response = await self.rate_limit_manager.execute_api_call(
                    lambda: self.session.get(url)
                )

            repo_data = response.json()
            return {
                "name": repo_data["name"],
                "full_name": repo_data["full_name"],
                "description": repo_data.get("description", ""),
                "language": repo_data.get("language", "Unknown"),
                "size": repo_data.get("size", 0),
                "default_branch": repo_data.get("default_branch", "main"),
                "private": repo_data.get("private", False),
                "archived": repo_data.get("archived", False),
                "disabled": repo_data.get("disabled", False),
                "topics": repo_data.get("topics", []),
                "license": (
                    repo_data.get("license", {}).get("name")
                    if repo_data.get("license")
                    else None
                ),
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
                "clone_url": repo_data.get("clone_url"),
                "html_url": repo_data.get("html_url"),
            }
        except Exception as e:
            if safe_mode:
                self.logger.debug(f"Safe mode: Failed to get repository info: {e}")
                return {
                    "name": repo,
                    "full_name": f"{owner}/{repo}",
                    "description": "",
                    "language": "Unknown",
                    "size": 0,
                    "default_branch": "main",
                    "private": None,
                }
            else:
                raise

    async def get_repository_contents(
        self,
        owner: str,
        repo: str,
        path: str = "",
        branch: str = None,
        recursive: bool = True,
        safe_mode: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get repository contents via GitHub Contents API with recursive support"""
        async with self._semaphore:
            all_contents = []

            # Build initial API URL
            url = URLParser.build_api_url(owner, repo, "contents")
            if path:
                url += f"/{path.strip('/')}"
            if branch:
                url += f"?ref={branch}"

            try:
                if safe_mode:
                    response = await self.session.get(url, raise_on_error=False)
                    await self.rate_limit_manager.track_safe_api_call(response)
                    if not response.is_success:
                        return []
                else:
                    response = await self.rate_limit_manager.execute_api_call(
                        lambda: self.session.get(url)
                    )

                contents = response.json()

                # Handle single file response
                if isinstance(contents, dict):
                    contents = [contents]

                for item in contents:
                    all_contents.append({
                        "name": item["name"],
                        "path": item["path"],
                        "type": item["type"],
                        "size": item.get("size", 0),
                        "download_url": item.get("download_url"),
                        "git_url": item.get("git_url"),
                        "html_url": item.get("html_url"),
                        "sha": item.get("sha"),
                    })

                    # Recursively get subdirectory contents
                    if recursive and item["type"] == "dir":
                        try:
                            subcontents = await self.get_repository_contents(
                                owner, repo, item["path"], branch, recursive, safe_mode
                            )
                            all_contents.extend(subcontents)
                        except Exception as e:
                            self.logger.debug(f"Failed to get contents for {item['path']}: {e}")
                            continue

                return all_contents

            except Exception as e:
                if safe_mode:
                    self.logger.debug(f"Safe mode: Failed to get contents: {e}")
                    return []
                else:
                    raise

    async def get_file_content(
        self, owner: str, repo: str, file_path: str, branch: str = None, safe_mode: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get individual file content with enhanced error handling"""
        async with self._semaphore:
            url = URLParser.build_api_url(owner, repo, f"contents/{file_path}")
            if branch:
                url += f"?ref={branch}"

            try:
                if safe_mode:
                    response = await self.session.get(url, raise_on_error=False)
                    await self.rate_limit_manager.track_safe_api_call(response)
                    if not response.is_success:
                        return None
                else:
                    response = await self.rate_limit_manager.execute_api_call(
                        lambda: self.session.get(url)
                    )

                file_data = response.json()
                return {
                    "name": file_data["name"],
                    "path": file_data["path"],
                    "content": file_data.get("content", ""),
                    "encoding": file_data.get("encoding", "base64"),
                    "size": file_data.get("size", 0),
                    "sha": file_data.get("sha"),
                    "download_url": file_data.get("download_url"),
                }

            except Exception as e:
                if safe_mode:
                    self.logger.debug(f"Safe mode: Failed to get file content for {file_path}: {e}")
                    return None
                else:
                    raise

    async def batch_download_files(
        self,
        owner: str,
        repo: str,
        file_paths: List[str],
        branch: str = None,
        batch_size: int = None,
        safe_mode: bool = False,
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Download multiple files in parallel batches with token-optimized performance"""
        if not file_paths:
            return {}

        # Get token-specific performance profile for optimized batch processing
        token_profile = self._get_token_performance_profile()
        effective_batch_size = batch_size or token_profile['batch_size']
        delay_between_batches = token_profile['delay']

        results = {}
        start_time = time.time()

        # Log performance optimization info for large batches
        if len(file_paths) > 20:
            self.logger.info(
                f"Token-optimized batch download: {len(file_paths)} files, "
                f"batch_size={effective_batch_size}, delay={delay_between_batches}s "
                f"({token_profile['performance']} mode)"
            )

        # Process files in optimized batches
        for i in range(0, len(file_paths), effective_batch_size):
            batch = file_paths[i:i + effective_batch_size]
            
            # Create download tasks for this batch
            tasks = []
            for file_path in batch:
                task = asyncio.create_task(
                    self._download_single_file_with_retry(
                        owner, repo, file_path, branch, safe_mode
                    )
                )
                tasks.append(task)

            # Execute batch concurrently
            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for file_path, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        self.logger.debug(f"Failed to download {file_path}: {result}")
                        results[file_path] = None
                    else:
                        results[file_path] = result

            except Exception as e:
                self.logger.debug(f"Batch download failed: {e}")
                # Mark all files in failed batch as None
                for file_path in batch:
                    results[file_path] = None

            # Token-specific delay between batches to optimize API usage
            if i + effective_batch_size < len(file_paths) and delay_between_batches > 0:
                await asyncio.sleep(delay_between_batches)

        # Performance summary
        elapsed_time = time.time() - start_time
        successful_downloads = sum(1 for v in results.values() if v is not None)
        
        if len(file_paths) > 10:
            self.logger.info(
                f"Batch download completed: {successful_downloads}/{len(file_paths)} files "
                f"in {elapsed_time:.2f}s ({token_profile['performance']} performance)"
            )

        return results

    async def _download_single_file_with_retry(
        self,
        owner: str,
        repo: str,
        file_path: str,
        branch: str = None,
        safe_mode: bool = False,
        max_retries: int = 2
    ) -> Optional[Dict[str, Any]]:
        """Download single file with exponential backoff retry"""
        
        for attempt in range(max_retries + 1):
            try:
                # Get file content using existing method
                file_data = await self.get_file_content(owner, repo, file_path, branch, safe_mode)
                
                if file_data and file_data.get("content") and file_data.get("encoding") == "base64":
                    # Decode base64 content
                    import base64
                    try:
                        decoded_content = base64.b64decode(file_data["content"]).decode("utf-8")
                        return {
                            "path": file_path,
                            "content": decoded_content,
                            "size": len(decoded_content),
                            "sha": file_data.get("sha"),
                            "encoding": "utf-8",
                        }
                    except (UnicodeDecodeError, base64.binascii.Error):
                        # Try latin-1 encoding for non-UTF-8 files
                        try:
                            decoded_content = base64.b64decode(file_data["content"]).decode("latin-1")
                            return {
                                "path": file_path,
                                "content": decoded_content,
                                "size": len(decoded_content),
                                "sha": file_data.get("sha"),
                                "encoding": "latin-1",
                            }
                        except:
                            # Skip binary or unreadable files
                            return None
                elif file_data:
                    # File exists but couldn't decode content
                    return {
                        "path": file_path,
                        "content": "",
                        "size": 0,
                        "sha": file_data.get("sha"),
                        "encoding": "unknown",
                    }
                else:
                    return None
                    
            except Exception as e:
                if attempt < max_retries:
                    # Exponential backoff
                    wait_time = (2 ** attempt) * 0.5
                    await asyncio.sleep(wait_time)
                    self.logger.debug(f"Retrying {file_path} (attempt {attempt + 2}): {e}")
                else:
                    self.logger.debug(f"Final failure for {file_path}: {e}")
                    return None
        
        return None

    async def download_zip_archive(
        self, owner: str, repo: str, branch: str = "main", safe_mode: bool = False
    ) -> Optional[Dict[str, str]]:
        """Download repository as ZIP archive with enhanced error handling"""
        zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch}"

        try:
            if safe_mode:
                response = await self.session.get(zip_url, raise_on_error=False)
                await self.rate_limit_manager.track_safe_api_call(response)
                if not response.is_success:
                    return None
            else:
                response = await self.rate_limit_manager.execute_api_call(
                    lambda: self.session.get(zip_url)
                )

            if response.status_code != 200:
                return None

            return self._extract_zip_files(response.content)

        except Exception as e:
            if safe_mode:
                self.logger.debug(f"Safe mode: ZIP download failed: {e}")
                return None
            else:
                raise

    def _extract_zip_files(self, zip_data: bytes) -> Dict[str, str]:
        """Extract files from ZIP archive with enhanced encoding handling"""
        files = {}

        try:
            with zipfile.ZipFile(BytesIO(zip_data), "r") as zip_file:
                for file_info in zip_file.filelist:
                    if file_info.is_dir():
                        continue

                    file_path = file_info.filename
                    if "/" in file_path:
                        file_path = "/".join(file_path.split("/")[1:])

                    if not file_path:
                        continue

                    try:
                        file_content = zip_file.read(file_info.filename)

                        try:
                            decoded_content = file_content.decode("utf-8")
                        except UnicodeDecodeError:
                            try:
                                decoded_content = file_content.decode("latin-1")
                            except:
                                continue

                        files[file_path] = decoded_content

                    except Exception as e:
                        self.logger.debug(f"Failed to extract {file_path}: {e}")
                        continue

        except zipfile.BadZipFile:
            self.logger.error("Invalid ZIP file received")
            return {}
        except Exception as e:
            self.logger.error(f"ZIP extraction failed: {e}")
            return {}

        return files

    async def search_repositories(
        self,
        query: str,
        sort: str = "updated",
        order: str = "desc",
        per_page: int = 30,
        page: int = 1,
        safe_mode: bool = False,
    ) -> Dict[str, Any]:
        """Search repositories using GitHub Search API"""
        url = "https://api.github.com/search/repositories"
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100),
            "page": page,
        }

        try:
            if safe_mode:
                response = await self.session.get(url, params=params, raise_on_error=False)
                await self.rate_limit_manager.track_safe_api_call(response)
                if not response.is_success:
                    return {"total_count": 0, "items": []}
            else:
                response = await self.rate_limit_manager.execute_api_call(
                    lambda: self.session.get(url, params=params)
                )

            search_results = response.json()

            return {
                "total_count": search_results.get("total_count", 0),
                "items": [
                    {
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "description": repo.get("description", ""),
                        "language": repo.get("language"),
                        "stargazers_count": repo.get("stargazers_count", 0),
                        "forks_count": repo.get("forks_count", 0),
                        "updated_at": repo.get("updated_at"),
                        "html_url": repo.get("html_url"),
                        "clone_url": repo.get("clone_url"),
                        "default_branch": repo.get("default_branch", "main"),
                    }
                    for repo in search_results.get("items", [])
                ],
            }

        except Exception as e:
            if safe_mode:
                self.logger.debug(f"Safe mode: Repository search failed: {e}")
                return {"total_count": 0, "items": []}
            else:
                raise

    async def get_user_repositories(
        self,
        username: str,
        type_filter: str = "all",
        sort: str = "updated",
        direction: str = "desc",
        per_page: int = 30,
        page: int = 1,
        safe_mode: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get user's repositories with enhanced pagination support"""
        url = f"https://api.github.com/users/{username}/repos"
        params = {
            "type": type_filter,
            "sort": sort,
            "direction": direction,
            "per_page": min(per_page, 100),
            "page": page,
        }

        try:
            if safe_mode:
                response = await self.session.get(url, params=params, raise_on_error=False)
                await self.rate_limit_manager.track_safe_api_call(response)
                if not response.is_success:
                    return []
            else:
                response = await self.rate_limit_manager.execute_api_call(
                    lambda: self.session.get(url, params=params)
                )

            repositories = response.json()

            return [
                {
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "description": repo.get("description", ""),
                    "language": repo.get("language"),
                    "size": repo.get("size", 0),
                    "stargazers_count": repo.get("stargazers_count", 0),
                    "forks_count": repo.get("forks_count", 0),
                    "created_at": repo.get("created_at"),
                    "updated_at": repo.get("updated_at"),
                    "html_url": repo.get("html_url"),
                    "clone_url": repo.get("clone_url"),
                    "default_branch": repo.get("default_branch", "main"),
                    "private": repo.get("private", False),
                    "archived": repo.get("archived", False),
                }
                for repo in repositories
                if isinstance(repo, dict)
            ]

        except Exception as e:
            if safe_mode:
                self.logger.debug(f"Safe mode: Failed to get user repositories: {e}")
                return []
            else:
                raise

    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        url = "https://api.github.com/rate_limit"

        try:
            response = await self.session.get(url, raise_on_error=False)
            if response.is_success:
                rate_data = response.json()
                return {
                    "core": {
                        "limit": rate_data["resources"]["core"]["limit"],
                        "remaining": rate_data["resources"]["core"]["remaining"],
                        "reset": rate_data["resources"]["core"]["reset"],
                    },
                    "search": {
                        "limit": rate_data["resources"]["search"]["limit"],
                        "remaining": rate_data["resources"]["search"]["remaining"],
                        "reset": rate_data["resources"]["search"]["reset"],
                    },
                    "rate": rate_data.get("rate", {}),
                }
            else:
                return {"error": "Unable to fetch rate limit status"}

        except Exception as e:
            return {"error": f"Rate limit check failed: {e}"}

    async def close(self):
        """Close client and cleanup resources"""
        if self.session:
            await self.session.close()

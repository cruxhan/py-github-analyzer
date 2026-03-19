# py_github_analyzer/core.py
import asyncio
from typing import Any, Dict, List, Optional

from .analysis import (
    ASTSignatureExtractor,
    ApiAnalysisStrategy,
    FallbackAnalysisStrategy,
    ZipAnalysisStrategy,
)
from .async_github_client import AsyncGitHubClient
from .config import Config
from .exceptions import (
    AuthenticationError,
    GitHubAnalyzerError,
    NetworkError,
    PrivateRepositoryError,
    RateLimitExceededError,
    RepositoryTooLargeError,
)
from .exceptions import TimeoutError as AnalyzerTimeoutError
from .logger import AnalyzerLogger, get_logger
from .output_writer import OutputWriter
from .processing import FileProcessor
from .utils import TokenUtils, URLParser


class EmptyRepositoryError(GitHubAnalyzerError):
    pass


class GitHubRepositoryAnalyzer:
    def __init__(self, token: Optional[str] = None, logger: Optional[AnalyzerLogger] = None):
        self.github_token = self._resolve_github_token(token)
        self.logger = logger or get_logger()

        self.client = AsyncGitHubClient(self.github_token, self.logger)
        self.file_processor = FileProcessor(self.logger)
        self.output_writer = OutputWriter(self.logger)

        self._zip_strategy = ZipAnalysisStrategy(self.client, self.logger)
        self._api_strategy = ApiAnalysisStrategy(self.client, self.logger)
        self._fallback_strategy = FallbackAnalysisStrategy(self.client, self.logger)
        self._signature_extractor = ASTSignatureExtractor(self.logger)

        self._log_initialization_info()

    def _resolve_github_token(self, provided_token: Optional[str]) -> Optional[str]:
        try:
            return TokenUtils.get_github_token(provided_token)
        except ImportError:
            import os
            return provided_token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    def _log_initialization_info(self):
        if self.github_token:
            try:
                token_info = TokenUtils.get_token_info(self.github_token)
                if token_info["status"] == "provided":
                    self.logger.info(f"GitHub token loaded: {token_info['masked']} ({token_info['type']})")
                else:
                    self.logger.info("GitHub token loaded: provided")
            except Exception:
                self.logger.info("GitHub token provided")
            self.logger.info("Rate limit: 5000 requests/hour")
        else:
            self.logger.warning("No GitHub token - rate limited to 60 requests/hour")

    @property
    def github_token(self) -> Optional[str]:
        return self._github_token

    @github_token.setter
    def github_token(self, value: Optional[str]):
        self._github_token = value

    @property
    def token(self) -> Optional[str]:
        return self.github_token

    async def analyze_repository_async(
        self,
        repo_url: str,
        output_dir: str = "./results",
        output_format: str = "both",
        method: str = "auto",
        verbose: bool = False,
        dry_run: bool = False,
        fallback: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        original_error: Optional[Exception] = None
        fallback_error: Optional[Exception] = None

        try:
            url_info = URLParser.parse_github_url(repo_url)
            owner, repo = url_info["owner"], url_info["repo"]

            if verbose:
                self.logger.info(f"Analyzing repository: {owner}/{repo}")
                self.logger.info(f"Method: {method} | Output: {output_dir} | Format: {output_format}")

            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "repository": f"{owner}/{repo}",
                    "metadata": {
                        "repo": f"{owner}/{repo}",
                        "owner": owner,
                        "name": repo,
                        "lang": ["Simulated"],
                        "size": "Unknown",
                    },
                    "files": [],
                    "output_paths": {},
                    "fallback_mode": False,
                }

            files, repo_info = await self._run_strategy(owner, repo, method)

            if not files:
                self.logger.warning(f"No files extracted from repository: {repo_url}")
                if fallback:
                    return await self._run_fallback(owner, repo, output_dir, output_format)
                raise EmptyRepositoryError(f"No files found in repository: {owner}/{repo}")

            processed_files, processing_metadata = await asyncio.to_thread(
                self.file_processor.process_files, files
            )

            if not processed_files:
                self.logger.warning("No valid files to process")
                if fallback:
                    return await self._run_fallback(owner, repo, output_dir, output_format)
                raise EmptyRepositoryError("No processable files found")

            from .metadata_generator import MetadataGenerator
            metadata_generator = MetadataGenerator(self.logger)
            metadata = await asyncio.to_thread(
                self._safe_generate_metadata,
                metadata_generator,
                processed_files,
                processing_metadata,
                repo_info,
                repo_url,
            )

            total_lines = sum(f.get("lines", 0) for f in processed_files if isinstance(f, dict))
            self.logger.info(f"Analysis completed: {len(processed_files)} files, {total_lines} lines")

            output_paths = await self.output_writer.write(
                output_dir, output_format, metadata, processed_files, f"{owner}_{repo}"
            )

            return {
                "success": True,
                "repository": f"{owner}/{repo}",
                "metadata": metadata,
                "files": processed_files,
                "output_paths": output_paths,
                "fallback_mode": False,
                "analysis_method": method,
                "token_used": bool(self.token),
            }

        except Exception as e:
            original_error = e
            self.logger.error(f"Analysis failed: {type(e).__name__}: {e}")

            if fallback:
                self.logger.warning("Attempting fallback analysis...")
                try:
                    url_info = URLParser.parse_github_url(repo_url)
                    fallback_result = await self._run_fallback(
                        url_info["owner"],
                        url_info["repo"],
                        output_dir,
                        output_format,
                        original_error_info={
                            "error_type": type(original_error).__name__,
                            "error_message": str(original_error),
                            "analysis_method": method,
                        },
                    )
                    if fallback_result.get("success"):
                        fallback_result["original_error"] = {
                            "type": type(original_error).__name__,
                            "message": str(original_error),
                        }
                        fallback_result["fallback_triggered"] = True
                    return fallback_result
                except Exception as fe:
                    fallback_error = fe
                    self.logger.error(f"Fallback also failed: {type(fe).__name__}: {fe}")

                return {
                    "success": False,
                    "error_message": self._comprehensive_error_message(original_error, fallback_error),
                    "original_error": {"type": type(original_error).__name__, "message": str(original_error)},
                    "fallback_error": {"type": type(fallback_error).__name__, "message": str(fallback_error)} if fallback_error else None,
                    "repository": repo_url,
                    "fallback_mode": True,
                    "analysis_method": method,
                    "token_available": bool(self.token),
                }

            return {
                "success": False,
                "error_message": f"Analysis failed: {type(original_error).__name__}: {original_error}",
                "error_type": type(original_error).__name__,
                "repository": repo_url,
                "fallback_mode": False,
                "analysis_method": method,
                "token_available": bool(self.token),
            }

    async def analyze_signatures_async(
        self,
        repo_url: str,
        method: str = "auto",
        verbose: bool = False,
        fallback: bool = True,
        include_docstring: bool = False,
        public_only: bool = True,
        include_private_magic_methods: bool = True,
        output_dir: Optional[str] = None,
        output_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        original_error: Optional[Exception] = None
        fallback_error: Optional[Exception] = None

        try:
            url_info = URLParser.parse_github_url(repo_url)
            owner, repo = url_info["owner"], url_info["repo"]

            if verbose:
                self.logger.info(f"Analyzing signatures for repository: {owner}/{repo}")
                self.logger.info(
                    f"Method: {method} | include_docstring: {include_docstring} | public_only: {public_only}"
                )

            files, repo_info = await self._run_strategy(owner, repo, method)

            if not files:
                self.logger.warning(f"No files extracted from repository: {repo_url}")
                raise EmptyRepositoryError(f"No files found in repository: {owner}/{repo}")

            signature_result = await asyncio.to_thread(
                self._signature_extractor.extract_from_files,
                files,
                include_docstring,
                public_only,
                include_private_magic_methods,
            )

            signature_result["success"] = True
            signature_result["repository"] = f"{owner}/{repo}"
            signature_result["repo_info"] = repo_info
            signature_result["analysis_method"] = method
            signature_result["token_used"] = bool(self.token)

            if output_dir and output_format:
                output_paths = await self.output_writer.write(
                    output_dir,
                    output_format,
                    {
                        "repo": f"{owner}/{repo}",
                        "type": "signatures",
                        "include_docstring": include_docstring,
                        "public_only": public_only,
                        "file_count": signature_result.get("summary", {}).get("files_analyzed", 0),
                        "class_count": signature_result.get("summary", {}).get("classes", 0),
                        "function_count": signature_result.get("summary", {}).get("functions", 0),
                        "method_count": signature_result.get("summary", {}).get("methods", 0),
                        "version": Config.VERSION,
                    },
                    signature_result.get("files", []),
                    f"{owner}_{repo}_signatures",
                )
                signature_result["output_paths"] = output_paths
            else:
                signature_result["output_paths"] = {}

            return signature_result

        except Exception as e:
            original_error = e
            self.logger.error(f"Signature analysis failed: {type(e).__name__}: {e}")

            if fallback:
                try:
                    return {
                        "success": False,
                        "repository": repo_url,
                        "fallback_mode": True,
                        "analysis_method": method,
                        "error_message": self._comprehensive_error_message(original_error, fallback_error),
                        "files": [],
                        "summary": {
                            "files_analyzed": 0,
                            "classes": 0,
                            "functions": 0,
                            "methods": 0,
                        },
                    }
                except Exception as fe:
                    fallback_error = fe

            return {
                "success": False,
                "repository": repo_url,
                "fallback_mode": False,
                "analysis_method": method,
                "error_message": self._comprehensive_error_message(original_error, fallback_error),
                "files": [],
                "summary": {
                    "files_analyzed": 0,
                    "classes": 0,
                    "functions": 0,
                    "methods": 0,
                },
            }

    async def _run_strategy(
        self, owner: str, repo: str, method: str
    ):
        if method == "api":
            self.logger.info("Using API-only mode (explicit)")
            return await self._api_strategy.execute(owner, repo)

        if method == "zip":
            self.logger.info("Using ZIP-only mode (explicit)")
            return await self._zip_strategy.execute(owner, repo)

        self.logger.info("Using ZIP-first strategy (auto mode)")
        try:
            files, repo_info = await self._zip_strategy.execute(owner, repo)
            if files:
                self.logger.info(f"ZIP download successful! ({len(files)} files)")
            else:
                self.logger.warning("ZIP download returned no files")
            return files, repo_info
        except PrivateRepositoryError as e:
            if self.token:
                self.logger.warning("Private repository detected, trying API with token...")
                try:
                    files, repo_info = await self._api_strategy.execute(owner, repo)
                    self.logger.info(f"API access successful! ({len(files)} files)")
                    return files, repo_info
                except Exception as api_error:
                    self.logger.error(f"API access also failed: {api_error}")
            raise e
        except (NetworkError, AnalyzerTimeoutError, RepositoryTooLargeError) as e:
            if self.token:
                self.logger.warning(f"ZIP failed ({type(e).__name__}), attempting API fallback...")
                try:
                    files, repo_info = await self._api_strategy.execute(owner, repo)
                    self.logger.info(f"API fallback successful! ({len(files)} files)")
                    return files, repo_info
                except Exception as api_error:
                    self.logger.error(f"API fallback also failed: {api_error}")
            raise e
        except Exception as e:
            if self.token:
                self.logger.warning(f"ZIP failed with unexpected error, trying API fallback: {e}")
                try:
                    files, repo_info = await self._api_strategy.execute(owner, repo)
                    self.logger.info(f"API fallback successful! ({len(files)} files)")
                    return files, repo_info
                except Exception as api_error:
                    self.logger.error(f"API fallback also failed: {api_error}")
            raise e

    async def _run_fallback(
        self,
        owner: str,
        repo: str,
        output_dir: str,
        output_format: str,
        original_error_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            _, repo_info = await self._fallback_strategy.execute(owner, repo)
            fallback_metadata = self._fallback_strategy.build_metadata(owner, repo, repo_info, original_error_info)
            output_paths = await self.output_writer.write(
                output_dir, output_format, fallback_metadata, [], f"{owner}_{repo}_fallback"
            )
            self.logger.warning("Fallback analysis completed with limited data")
            return {
                "success": True,
                "repository": f"{owner}/{repo}",
                "metadata": fallback_metadata,
                "files": [],
                "output_paths": output_paths,
                "fallback_mode": True,
                "analysis_method": "fallback",
                "original_error": original_error_info,
                "warning": "Analysis completed in fallback mode with limited repository information only",
            }
        except Exception as e:
            error_msg = f"Fallback analysis failed: {type(e).__name__}: {e}"
            self.logger.error(error_msg)
            result: Dict[str, Any] = {
                "success": False,
                "error_message": error_msg,
                "fallback_error": {"type": type(e).__name__, "message": str(e)},
                "repository": f"{owner}/{repo}",
                "fallback_mode": True,
                "analysis_method": "fallback_failed",
            }
            if original_error_info:
                result["original_error"] = original_error_info
                result["error_message"] = (
                    f"Complete analysis failure. "
                    f"Original error: {original_error_info.get('error_type')}: {original_error_info.get('error_message')}. "
                    f"Fallback error: {type(e).__name__}: {e}"
                )
            return result

    def _safe_generate_metadata(
        self,
        metadata_generator: Any,
        processed_files: List[Dict[str, Any]],
        processing_metadata: Dict[str, Any],
        repo_info: Dict[str, Any],
        repo_url: str,
    ) -> Dict[str, Any]:
        try:
            if not isinstance(processed_files, list):
                processed_files = []
            if not isinstance(processing_metadata, dict):
                processing_metadata = {}
            if not isinstance(repo_info, dict):
                repo_info = {}
            if not isinstance(repo_url, str):
                repo_url = ""
            metadata = metadata_generator.generate_metadata(
                processed_files, processing_metadata, repo_info, repo_url
            )
            if not isinstance(metadata, dict):
                self.logger.warning(f"Metadata generator returned unexpected type: {type(metadata)}")
                return self._emergency_metadata(processed_files)
            return metadata
        except Exception as e:
            self.logger.error(f"Metadata generation failed: {e}")
            return self._emergency_metadata(processed_files, error=str(e))

    def _emergency_metadata(self, processed_files: List[Dict[str, Any]], error: Optional[str] = None) -> Dict[str, Any]:
        import time
        result: Dict[str, Any] = {
            "repo": "error/metadata-generation",
            "lang": ["Unknown"],
            "size": {"display_size": "0KB"},
            "files": len(processed_files) if isinstance(processed_files, list) else 0,
            "main": [],
            "deps": [],
            "created": int(time.time()),
            "version": Config.VERSION,
            "analysis_mode": "error_fallback",
        }
        if error:
            result["error"] = f"Metadata generation failed: {error}"
        return result

    def _comprehensive_error_message(self, original_error: Exception, fallback_error: Optional[Exception] = None) -> str:
        original_type = type(original_error).__name__
        if fallback_error:
            msg = (
                f"Repository analysis failed completely. "
                f"Primary: {original_type}: {original_error}. "
                f"Fallback: {type(fallback_error).__name__}: {fallback_error}."
            )
        else:
            msg = f"Repository analysis failed: {original_type}: {original_error}"
        if isinstance(original_error, (PrivateRepositoryError, AuthenticationError)):
            msg += " Verify your GitHub token has repo scope." if self.token else " Consider providing a GitHub token."
        elif isinstance(original_error, (NetworkError, AnalyzerTimeoutError)):
            msg += " Check your internet connection and try again."
        elif isinstance(original_error, RateLimitExceededError):
            msg += " GitHub API rate limit exceeded. Wait or use a different token."
        elif isinstance(original_error, RepositoryTooLargeError):
            msg += " Repository is too large. Consider increasing size limits."
        return msg

    async def close(self):
        if self.client:
            await self.client.close()


async def analyze_repository_async(repo_url: str, **kwargs) -> Dict[str, Any]:
    analyzer = GitHubRepositoryAnalyzer(
        token=kwargs.pop("github_token", None),
        logger=kwargs.pop("logger", None),
    )
    try:
        return await analyzer.analyze_repository_async(repo_url, **kwargs)
    finally:
        await analyzer.close()

async def analyze_signatures_async(
    self,
    repo_url: str,
    method: str = "auto",
    verbose: bool = False,
    fallback: bool = True,
    include_docstring: bool = False,
    public_only: bool = True,
    include_private_magic_methods: bool = True,
    output_dir: Optional[str] = None,
    output_format: Optional[str] = None,
) -> Dict[str, Any]:
    original_error: Optional[Exception] = None
    fallback_error: Optional[Exception] = None

    try:
        url_info = URLParser.parse_github_url(repo_url)
        owner, repo = url_info["owner"], url_info["repo"]

        if verbose:
            self.logger.info(f"Analyzing signatures for repository: {owner}/{repo}")
            self.logger.info(
                f"Method: {method} | include_docstring: {include_docstring} | public_only: {public_only}"
            )

        files, repo_info = await self._run_strategy(owner, repo, method)

        if not files:
            self.logger.warning(f"No files extracted from repository: {repo_url}")
            raise EmptyRepositoryError(f"No files found in repository: {owner}/{repo}")

        signature_result = await asyncio.to_thread(
            self._signature_extractor.extract_from_files,
            files,
            include_docstring,
            public_only,
            include_private_magic_methods,
        )

        extracted_files: List[Dict[str, Any]] = signature_result.get("files", [])

        files_with_content = [
            f for f in extracted_files
            if f.get("classes") or f.get("functions")
        ]
        classes_count = sum(len(f.get("classes", [])) for f in extracted_files)
        methods_count = sum(
            len(cls.get("methods", []))
            for f in extracted_files
            for cls in f.get("classes", [])
        )
        functions_count = sum(len(f.get("functions", [])) for f in extracted_files)
        files_skipped = len(extracted_files) - len(files_with_content)

        computed_summary: Dict[str, Any] = {
            "files_analyzed": len(files_with_content),
            "files_skipped": files_skipped,
            "classes": classes_count,
            "methods": methods_count,
            "functions": functions_count,
        }

        signature_result["summary"] = computed_summary
        signature_result["success"] = True
        signature_result["repository"] = f"{owner}/{repo}"
        signature_result["repo_info"] = repo_info
        signature_result["analysis_method"] = method
        signature_result["token_used"] = bool(self.token)

        self.logger.info(
            f"Signature extraction complete: {len(files_with_content)} files, "
            f"{classes_count} classes, {methods_count} methods, {functions_count} top-level functions"
        )

        if output_dir and output_format:
            output_paths = await self.output_writer.write(
                output_dir,
                output_format,
                {
                    "repo": f"{owner}/{repo}",
                    "type": "signatures",
                    "include_docstring": include_docstring,
                    "public_only": public_only,
                    "file_count": computed_summary["files_analyzed"],
                    "class_count": computed_summary["classes"],
                    "function_count": computed_summary["functions"],
                    "method_count": computed_summary["methods"],
                    "version": Config.VERSION,
                },
                extracted_files,
                f"{owner}_{repo}_signatures",
            )
            signature_result["output_paths"] = output_paths
        else:
            signature_result["output_paths"] = {}

        return signature_result

    except Exception as e:
        original_error = e
        self.logger.error(f"Signature analysis failed: {type(e).__name__}: {e}")

        empty_summary: Dict[str, Any] = {
            "files_analyzed": 0,
            "files_skipped": 0,
            "classes": 0,
            "functions": 0,
            "methods": 0,
        }

        if fallback:
            try:
                return {
                    "success": False,
                    "repository": repo_url,
                    "fallback_mode": True,
                    "analysis_method": method,
                    "error_message": self._comprehensive_error_message(original_error, fallback_error),
                    "files": [],
                    "summary": empty_summary,
                    "output_paths": {},
                }
            except Exception as fe:
                fallback_error = fe

        return {
            "success": False,
            "repository": repo_url,
            "fallback_mode": False,
            "analysis_method": method,
            "error_message": self._comprehensive_error_message(original_error, fallback_error),
            "files": [],
            "summary": empty_summary,
            "output_paths": {},
        }


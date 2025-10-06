#!/usr/bin/env python3
"""
GitHub Repository Analyzer Core Module
High-performance async-first GitHub repository analysis with enhanced error reporting
"""

import asyncio
import os
import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiofiles

from .async_github_client import AsyncGitHubClient
from .config import Config
from .exceptions import (
    TimeoutError as AnalyzerTimeoutError,
    GitHubAnalyzerError,
    AuthenticationError,
    NetworkError,
    PrivateRepositoryError,
    RateLimitExceededError,
    RepositoryNotFoundError,
    RepositoryTooLargeError
)
from .file_processor import FileProcessor
from .logger import AnalyzerLogger, get_logger
from .metadata_generator import MetadataGenerator
from .utils import TokenUtils, URLParser


class EmptyRepositoryError(GitHubAnalyzerError):
    """Raised when repository exists but contains no analyzable files"""
    pass


class GitHubRepositoryAnalyzer:
    """High-performance async GitHub repository analyzer with enhanced error handling"""

    def __init__(self, token: Optional[str] = None, logger: Optional[AnalyzerLogger] = None):
        """Initialize analyzer with optional token and logger"""
        self.github_token = self._resolve_github_token(token)
        self.logger = logger or get_logger()
        
        self.client = AsyncGitHubClient(self.github_token, self.logger)
        self.metadata_generator = MetadataGenerator(self.logger)
        self.file_processor = FileProcessor(self.logger)
        
        self._log_initialization_info()
    
    def _resolve_github_token(self, provided_token: Optional[str]) -> Optional[str]:
        """Resolve GitHub token from multiple sources"""
        try:
            from .utils import TokenUtils
            return TokenUtils.get_github_token(provided_token)
        except ImportError:
            if provided_token:
                return provided_token
            import os
            return os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    
    def _log_initialization_info(self):
        """Log initialization information"""
        if self.github_token:
            try:
                from .utils import TokenUtils
                token_info = TokenUtils.get_token_info(self.github_token)
                if token_info['status'] == 'provided':
                    self.logger.info(f"GitHub token loaded: {token_info['masked']} ({token_info['type']})")
                else:
                    self.logger.info("GitHub token loaded: provided")
            except (ImportError, Exception):
                self.logger.info("GitHub token provided")
            self.logger.info("Rate limit: 5000 requests/hour")
        else:
            self.logger.warning("No GitHub token - rate limited to 60 requests/hour")
    
    @property
    def github_token(self) -> Optional[str]:
        """Get the current GitHub token"""
        return self._github_token
    
    @github_token.setter
    def github_token(self, value: Optional[str]):
        """Set the GitHub token"""
        self._github_token = value
    
    @property
    def token(self) -> Optional[str]:
        """Backward compatibility property"""
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
        **kwargs
    ) -> Dict[str, Any]:
        """Analyze a GitHub repository asynchronously with ZIP-first strategy"""
        original_error = None
        fallback_error = None
        
        try:
            url_info = URLParser.parse_github_url(repo_url)
            owner = url_info['owner']
            repo = url_info['repo']
            
            if verbose:
                self.logger.info(f"Analyzing repository: {owner}/{repo}")
                self.logger.info(f"Method: {method}")
                self.logger.info(f"Output: {output_dir}")
                self.logger.info(f"Format: {output_format}")
            
            if dry_run:
                self.logger.info("Dry-run mode: Simulating analysis...")
                return {
                    'success': True,
                    'dry_run': True,
                    'repository': f"{owner}/{repo}",
                    'metadata': {
                        'repo': f"{owner}/{repo}",
                        'owner': owner,
                        'name': repo,
                        'lang': ["Simulated"],
                        'size': "Unknown"
                    },
                    'files': [],
                    'output_paths': {},
                    'fallback_mode': False
                }
            
            files = []
            repo_info = {}
            
            if method == "api":
                self.logger.info("Using API-only mode (explicit)")
                files, repo_info = await self.analyze_with_api(owner, repo)
            elif method == "zip":
                self.logger.info("Using ZIP-only mode (explicit)")
                files, repo_info = await self.analyze_with_zip(owner, repo)
            else:
                self.logger.info("Using ZIP-first strategy (auto mode)")
                try:
                    files, repo_info = await self.analyze_with_zip(owner, repo)
                    if files:
                        self.logger.info(f"ZIP download successful! ({len(files)} files)")
                    else:
                        self.logger.warning("ZIP download returned no files")
                except PrivateRepositoryError as e:
                    if self.token:
                        self.logger.warning("Private repository detected, trying API with token...")
                        try:
                            files, repo_info = await self.analyze_with_api(owner, repo)
                            self.logger.info(f"API access successful! ({len(files)} files)")
                        except Exception as api_error:
                            self.logger.error(f"API access also failed: {api_error}")
                            raise e
                    else:
                        self.logger.error("Private repository requires GitHub token")
                        raise e
                except (NetworkError, AnalyzerTimeoutError, RepositoryTooLargeError) as e:
                    if self.token:
                        self.logger.warning(f"ZIP failed ({type(e).__name__}), attempting API fallback...")
                        try:
                            files, repo_info = await self.analyze_with_api(owner, repo)
                            self.logger.info(f"API fallback successful! ({len(files)} files)")
                        except Exception as api_error:
                            self.logger.error(f"API fallback also failed: {api_error}")
                            raise e
                    else:
                        self.logger.error(f"ZIP failed and no token for API fallback: {e}")
                        raise e
                except Exception as e:
                    if self.token:
                        self.logger.warning(f"ZIP failed with unexpected error, trying API fallback: {e}")
                        try:
                            files, repo_info = await self.analyze_with_api(owner, repo)
                            self.logger.info(f"API fallback successful! ({len(files)} files)")
                        except Exception as api_error:
                            self.logger.error(f"API fallback also failed: {api_error}")
                            raise e
                    else:
                        raise e
            
            if not files:
                self.logger.warning(f"No files extracted from repository: {repo_url}")
                if fallback:
                    self.logger.warning("Attempting fallback analysis...")
                    return await self.fallback_analysis(owner, repo, output_dir, output_format)
                else:
                    raise EmptyRepositoryError(f"No files found in repository: {owner}/{repo}")
            
            processed_files, processing_metadata = await asyncio.to_thread(
                self.file_processor.process_files, files
            )
            
            if not processed_files:
                self.logger.warning("No valid files to process")
                if fallback:
                    return await self.fallback_analysis(owner, repo, output_dir, output_format)
                else:
                    raise EmptyRepositoryError("No processable files found")
            
            metadata = await asyncio.to_thread(
                self._safe_generate_metadata,
                processed_files,
                processing_metadata,
                repo_info,
                repo_url
            )
            
            total_lines = sum(f.get('lines', 0) for f in processed_files if isinstance(f, dict))
            self.logger.info(f"Analysis completed: {len(processed_files)} files, {total_lines} lines")
            self.logger.info(f"Primary language: {metadata.get('lang', ['Unknown'])[0] if metadata.get('lang') else 'Unknown'}")
            
            output_paths = await self.save_output_async(
                output_dir, output_format, metadata, processed_files, f"{owner}_{repo}"
            )
            
            return {
                'success': True,
                'repository': f"{owner}/{repo}",
                'metadata': metadata,
                'files': processed_files,
                'output_paths': output_paths,
                'fallback_mode': False,
                'analysis_method': method,
                'token_used': bool(self.token)
            }
            
        except Exception as e:
            original_error = e
            self.logger.error(f"Analysis failed with error: {type(e).__name__}: {e}")
            
            if fallback:
                self.logger.warning("Attempting fallback analysis...")
                try:
                    url_info = URLParser.parse_github_url(repo_url)
                    fallback_result = await self.fallback_analysis(
                        url_info['owner'],
                        url_info['repo'],
                        output_dir,
                        output_format,
                        original_error_info={
                            'error_type': type(original_error).__name__,
                            'error_message': str(original_error),
                            'analysis_method': method
                        }
                    )
                    
                    if fallback_result.get('success'):
                        fallback_result['original_error'] = {
                            'type': type(original_error).__name__,
                            'message': str(original_error)
                        }
                        fallback_result['fallback_triggered'] = True
                        return fallback_result
                    else:
                        return fallback_result
                        
                except Exception as fallback_ex:
                    fallback_error = fallback_ex
                    self.logger.error(f"Fallback analysis also failed: {type(fallback_ex).__name__}: {fallback_ex}")
                
                comprehensive_error = self.create_comprehensive_error_message(original_error, fallback_error)
                return {
                    'success': False,
                    'error_message': comprehensive_error,
                    'original_error': {
                        'type': type(original_error).__name__,
                        'message': str(original_error)
                    },
                    'fallback_error': {
                        'type': type(fallback_error).__name__,
                        'message': str(fallback_error)
                    } if fallback_error else None,
                    'repository': repo_url,
                    'fallback_mode': True,
                    'analysis_method': method,
                    'token_available': bool(self.token)
                }
            else:
                return {
                    'success': False,
                    'error_message': f"Analysis failed: {type(original_error).__name__}: {original_error}",
                    'error_type': type(original_error).__name__,
                    'repository': repo_url,
                    'fallback_mode': False,
                    'analysis_method': method,
                    'token_available': bool(self.token)
                }
    
    def _safe_generate_metadata(
        self,
        processed_files: List[Dict[str, Any]],
        processing_metadata: Dict[str, Any],
        repo_info: Dict[str, Any],
        repo_url: str
    ) -> Dict[str, Any]:
        """Safe metadata generation with proper error handling"""
        try:
            if not isinstance(processed_files, list):
                processed_files = []
            if not isinstance(processing_metadata, dict):
                processing_metadata = {}
            if not isinstance(repo_info, dict):
                repo_info = {}
            if not isinstance(repo_url, str):
                repo_url = ""
            
            metadata = self.metadata_generator.generate_metadata(
                processed_files,
                processing_metadata,
                repo_info,
                repo_url
            )
            
            if not isinstance(metadata, dict):
                self.logger.warning(f"Metadata generator returned unexpected type: {type(metadata)}")
                return {
                    'repo': 'unknown/unknown',
                    'lang': ['Unknown'],
                    'size': {'display_size': '0KB'},
                    'files': len(processed_files),
                    'main': [],
                    'deps': [],
                    'created': int(asyncio.get_event_loop().time()),
                    'version': Config.VERSION,
                    'analysis_mode': 'fallback'
                }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Metadata generation failed: {e}")
            return {
                'repo': 'error/metadata-generation',
                'lang': ['Unknown'],
                'size': {'display_size': '0KB'},
                'files': len(processed_files) if isinstance(processed_files, list) else 0,
                'main': [],
                'deps': [],
                'created': int(asyncio.get_event_loop().time()),
                'version': Config.VERSION,
                'analysis_mode': 'error_fallback',
                'error': f"Metadata generation failed: {e}"
            }

    async def analyze_with_zip(self, owner: str, repo: str) -> tuple:
        """Perform analysis using ZIP method"""
        try:
            zip_data = await self.client.download_zip_archive(owner, repo)
            if not zip_data:
                raise NetworkError("ZIP download failed - no data received")
            
            files = []
            for file_path, file_content in zip_data.items():
                file_info = {
                    'path': file_path,
                    'content': file_content,
                    'size': len(file_content),
                    'type': 'file'
                }
                files.append(file_info)
            
            repo_info = {
                'name': repo,
                'full_name': f"{owner}/{repo}",
                'owner': {'login': owner},
                'default_branch': 'main',
            }
            
            self.logger.debug(f"ZIP analysis extracted {len(files)} files")
            return files, repo_info
            
        except Exception as e:
            self.logger.error(f"ZIP analysis failed: {e}")
            raise

    async def analyze_with_api(self, owner: str, repo: str) -> tuple:
        """Perform analysis using API method"""
        try:
            repo_info = await self.client.get_repository_info(owner, repo)
            contents = await self.client.get_repository_contents(owner, repo, recursive=True)
            
            file_paths = [item['path'] for item in contents if item['type'] == 'file']
            
            batch_results = await self.client.batch_download_files(
                owner, repo, file_paths, safe_mode=False
            )
            
            files = []
            for file_path, file_data in batch_results.items():
                if file_data:
                    file_info = {
                        'path': file_path,
                        'content': file_data.get('content', ''),
                        'size': file_data.get('size', 0),
                        'type': 'file',
                        'sha': file_data.get('sha', ''),
                    }
                    files.append(file_info)
            
            self.logger.debug(f"API analysis extracted {len(files)} files")
            return files, repo_info or {}
            
        except Exception as e:
            self.logger.error(f"API analysis failed: {e}")
            raise

    def create_comprehensive_error_message(self, original_error: Exception, fallback_error: Exception = None) -> str:
        """Create a comprehensive error message that includes both original and fallback failures"""
        original_type = type(original_error).__name__
        
        if fallback_error:
            fallback_type = type(fallback_error).__name__
            comprehensive_message = (
                f"Repository analysis failed completely. "
                f"Primary analysis failed with {original_type}: {original_error}. "
                f"Fallback analysis also failed with {fallback_type}: {fallback_error}."
            )
        else:
            comprehensive_message = f"Repository analysis failed: {original_type}: {original_error}"
        
        if isinstance(original_error, (PrivateRepositoryError, AuthenticationError)):
            if not self.token:
                comprehensive_message += " Consider providing a GitHub token for private repository access."
            else:
                comprehensive_message += " Verify that your GitHub token has sufficient permissions (repo scope)."
        elif isinstance(original_error, (NetworkError, AnalyzerTimeoutError)):
            comprehensive_message += " This appears to be a network connectivity issue. Please check your internet connection and try again."
        elif isinstance(original_error, RateLimitExceededError):
            comprehensive_message += " GitHub API rate limit exceeded. Please wait before retrying or use a different token."
        elif isinstance(original_error, RepositoryTooLargeError):
            comprehensive_message += " Repository is too large for analysis. Consider analyzing a smaller repository or increasing size limits."
        
        return comprehensive_message

    async def fallback_analysis(
        self,
        owner: str,
        repo: str,
        output_dir: str,
        output_format: str,
        original_error_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Provide basic fallback analysis when normal processing fails"""
        try:
            try:
                repo_info = await self.client.get_repository_info(owner, repo, safe_mode=True)
            except Exception as e:
                self.logger.warning(f"Could not get repository info: {e}")
                repo_info = {
                    'name': repo,
                    'full_name': f"{owner}/{repo}",
                    'owner': {'login': owner},
                    'description': 'No description available',
                    'language': None,
                    'size': 0,
                    'created_at': None,
                    'updated_at': None,
                    'stargazers_count': 0,
                    'forks_count': 0,
                    'private': True
                }
            
            fallback_metadata = self._generate_safe_fallback_metadata(owner, repo, repo_info, original_error_info)
            
            fallback_filename = f"{owner}_{repo}_fallback"
            output_paths = await self.save_output_async(
                output_dir, output_format, fallback_metadata, [], fallback_filename
            )
            
            self.logger.warning("Fallback analysis completed with limited data")
            
            return {
                'success': True,
                'repository': f"{owner}/{repo}",
                'metadata': fallback_metadata,
                'files': [],
                'output_paths': output_paths,
                'fallback_mode': True,
                'analysis_method': 'fallback',
                'original_error': original_error_info,
                'warning': 'Analysis completed in fallback mode with limited repository information only'
            }
            
        except Exception as e:
            fallback_error_message = f"Fallback analysis failed: {type(e).__name__}: {e}"
            self.logger.error(f"{fallback_error_message}")
            
            error_details = {
                'success': False,
                'error_message': fallback_error_message,
                'fallback_error': {
                    'type': type(e).__name__,
                    'message': str(e)
                },
                'repository': f"{owner}/{repo}",
                'fallback_mode': True,
                'analysis_method': 'fallback_failed'
            }
            
            if original_error_info:
                error_details['original_error'] = original_error_info
                comprehensive_msg = (
                    f"Complete analysis failure. "
                    f"Original error: {original_error_info.get('error_type', 'Unknown')}: {original_error_info.get('error_message', 'Unknown')}. "
                    f"Fallback error: {type(e).__name__}: {e}"
                )
                error_details['error_message'] = comprehensive_msg
            
            return error_details

    def _generate_safe_fallback_metadata(
        self,
        owner: str,
        repo: str,
        repo_info: Dict[str, Any],
        original_error_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate safe fallback metadata with proper error handling"""
        try:
            import time
            
            description = None
            if isinstance(repo_info, dict):
                description = repo_info.get('description')
            
            language = 'Unknown'
            if isinstance(repo_info, dict) and repo_info.get('language'):
                language = str(repo_info['language'])
            
            size = 0
            if isinstance(repo_info, dict) and repo_info.get('size'):
                try:
                    size = int(repo_info['size'])
                except (ValueError, TypeError):
                    size = 0
            
            fallback_metadata = {
                'repo': f"{owner}/{repo}",
                'owner': owner,
                'name': repo,
                'description': description,
                'lang': [language] if language != 'Unknown' else ['Unknown'],
                'size': size,
                'created': repo_info.get('created_at') if isinstance(repo_info, dict) else None,
                'updated': repo_info.get('updated_at') if isinstance(repo_info, dict) else None,
                'stars': repo_info.get('stargazers_count', 0) if isinstance(repo_info, dict) else 0,
                'forks': repo_info.get('forks_count', 0) if isinstance(repo_info, dict) else 0,
                'fallback_mode': True,
                'analysis_mode': 'basic_metadata_only',
                'files': 0,
                'main': [],
                'deps': [],
                'created_at': int(time.time()),
                'version': Config.VERSION
            }
            
            if original_error_info:
                fallback_metadata['original_failure'] = original_error_info
            
            return fallback_metadata
            
        except Exception as e:
            self.logger.error(f"Safe fallback metadata generation failed: {e}")
            import time
            return {
                'repo': f"{owner}/{repo}",
                'owner': owner,
                'name': repo,
                'description': 'Analysis failed - minimal data only',
                'lang': ['Unknown'],
                'size': 0,
                'fallback_mode': True,
                'analysis_mode': 'emergency_fallback',
                'files': 0,
                'main': [],
                'deps': [],
                'created_at': int(time.time()),
                'version': Config.VERSION,
                'error': f"Metadata generation error: {e}"
            }

    async def save_output_async(
        self,
        output_dir: str,
        output_format: str,
        metadata: Dict[str, Any],
        files: List[Dict[str, Any]],
        filename_prefix: str
    ) -> Dict[str, str]:
        """Save analysis results asynchronously with enhanced error handling"""
        try:
            output_dir_path = Path(output_dir)
            output_dir_path.mkdir(parents=True, exist_ok=True)
            
            output_paths = {}
            
            if output_format in ['json', 'both']:
                json_path = output_dir_path / f"{filename_prefix}.json"
                output_data = {
                    'metadata': metadata,
                    'files': files,
                    'generated_at': asyncio.get_event_loop().time(),
                    'version': Config.VERSION
                }
                
                async with aiofiles.open(json_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(output_data, indent=2, ensure_ascii=False))
                
                output_paths['json'] = str(json_path)
                self.logger.debug(f"Saved JSON output: {json_path}")
            
            if output_format in ['bin', 'both']:
                bin_path = output_dir_path / f"{filename_prefix}.bin"
                output_data = {
                    'metadata': metadata,
                    'files': files,
                    'generated_at': asyncio.get_event_loop().time(),
                    'version': Config.VERSION
                }
                
                async with aiofiles.open(bin_path, 'wb') as f:
                    import pickle
                    await f.write(pickle.dumps(output_data))
                
                output_paths['bin'] = str(bin_path)
                self.logger.debug(f"Saved binary output: {bin_path}")
            
            return output_paths
            
        except Exception as e:
            self.logger.error(f"Failed to save output files: {e}")
            return {'error': f"Output save failed: {e}"}

    async def close(self):
        """Close analyzer and cleanup resources"""
        if self.client:
            await self.client.close()


async def analyze_repository_async(repo_url: str, **kwargs) -> Dict[str, Any]:
    """Standalone async function for repository analysis with enhanced error reporting"""
    analyzer = GitHubRepositoryAnalyzer(
        token=kwargs.get('github_token'),
        logger=kwargs.get('logger')
    )
    
    try:
        result = await analyzer.analyze_repository_async(repo_url, **kwargs)
        return result
    finally:
        await analyzer.close()

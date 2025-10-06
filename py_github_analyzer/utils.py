"""

Utility functions and classes for py-github-analyzer

URL parsing, file operations, and token management utilities

"""

import re
import os
import gzip
import bz2
import lzma
import random
import mimetypes
import hashlib
from pathlib import Path
from typing import Dict, List, Union, Callable, Optional
import tempfile
import shutil
from contextlib import contextmanager
from functools import wraps

from .config import Config
from .exceptions import ValidationError, CompressionError


class URLParser:
    """GitHub URL parsing and validation utilities"""
    
    GITHUB_URL_PATTERN = re.compile(
        r'(?:https?://)?github\.com[/:](?P<owner>[^/\s]+)[/:](?P<repo>[^/\s\.]+)(?:\.git)?(?:/(?P<path>.+))?',
        re.IGNORECASE
    )

    @classmethod
    def parse_github_url(cls, url: str) -> Dict[str, str]:
        """Parse GitHub URL and extract owner, repo, and optional path"""
        if not url:
            raise ValidationError("Empty URL provided")
        
        url = url.strip().rstrip('/')
        if not url:
            raise ValidationError("Invalid GitHub URL format")
        
        # Handle different URL formats
        if not url.startswith(('http', 'https')):
            if url.startswith('github.com'):
                url = f"https://{url}"
            elif '/' in url and len(url.split('/')) >= 2 and not url.startswith('github.com'):
                url = f"https://github.com/{url}"
            else:
                url = f"https://github.com/{url}"
        
        match = cls.GITHUB_URL_PATTERN.match(url)
        if not match:
            raise ValidationError(
                f"Invalid GitHub URL format: {url}. "
                "Expected format: https://github.com/owner/repo"
            )
        
        result = match.groupdict()
        if not result['owner'] or not result['repo']:
            raise ValidationError("URL must contain both owner and repository name")
        
        # Clean up repo name
        if result['repo'].endswith('.git'):
            result['repo'] = result['repo'][:-4]
        
        return {
            'owner': result['owner'],
            'repo': result['repo'],
            'path': result.get('path') or '',  # Always string, never None
            'full_name': f"{result['owner']}/{result['repo']}"
        }

    @staticmethod
    def is_valid_github_url(url: str) -> bool:
        """Check if URL is a valid GitHub repository URL"""
        try:
            URLParser.parse_github_url(url)
            return True
        except ValidationError:
            return False

    @staticmethod
    def build_api_url(owner: str, repo: str, path: str = "") -> str:
        """Build GitHub API URL"""
        base_url = f"{Config.GITHUB_API_BASE}/repos/{owner}/{repo}"
        if path:
            return f"{base_url}/{path.lstrip('/')}"
        return base_url

    @staticmethod
    def build_raw_url(owner: str, repo: str, branch: str, path: str) -> str:
        """Build GitHub raw content URL"""
        return f"{Config.GITHUB_RAW_BASE}/{owner}/{repo}/{branch}/{path.lstrip('/')}"

    @staticmethod
    def build_zip_url(owner: str, repo: str, branch: str = "main") -> str:
        """Build GitHub ZIP download URL"""
        return f"{Config.GITHUB_ARCHIVE_BASE}/{owner}/{repo}/archive/refs/heads/{branch}.zip"


class ValidationUtils:
    """Validation utility functions"""

    @staticmethod
    def validate_github_token(token: Optional[str]) -> bool:
        """Validate GitHub token format"""
        if not token or not isinstance(token, str):
            return False

        token = token.strip()
        if not token:
            return False

        # GitHub personal access tokens (classic) - exactly 40 chars starting with ghp_
        if token.startswith('ghp_'):
            return len(token) == 40

        # GitHub App tokens - exactly 40 chars starting with ghs_
        if token.startswith('ghs_'):
            return len(token) == 40

        # GitHub OAuth tokens - exactly 40 chars starting with gho_
        if token.startswith('gho_'):
            return len(token) == 40

        # GitHub refresh tokens - exactly 40 chars starting with ghr_
        if token.startswith('ghr_'):
            return len(token) == 40

        # Fine-grained personal access tokens - starts with github_pat_ and longer than 80 chars
        if token.startswith('github_pat_'):
            return len(token) >= 80

        # Legacy tokens (40 characters, hexadecimal)
        if len(token) == 40:
            try:
                int(token, 16)  # Check if it's valid hexadecimal
                return True
            except ValueError:
                return False

        return False

    @staticmethod
    def validate_file_path(file_path: Optional[str]) -> bool:
        """Validate file path for security"""
        if not file_path:
            return False
        
        # Check for path traversal attacks
        if '..' in file_path:
            return False
        
        # Check for absolute paths
        if file_path.startswith('/'):
            return False
        
        # Check for Windows absolute paths
        if len(file_path) > 1 and file_path[1] == ':':
            return False
        
        # Check for backslashes (Windows path separators)
        if '\\' in file_path:  # Fixed: single backslash check
            return False
        
        # Check for relative path indicators
        if file_path.startswith('./') or '/./' in file_path:
            return False
        
        return True

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe filesystem usage"""
        if not filename:
            return "sanitized_file"
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove or replace dangerous characters
        # Keep alphanumeric, dots, hyphens, underscores, and parentheses
        safe_filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
        safe_filename = re.sub(r'[ ]+', '_', safe_filename)  # Replace spaces with underscores
        
        # Remove leading/trailing dots and spaces
        safe_filename = safe_filename.strip(' .')
        
        # Handle edge cases
        if not safe_filename:
            return "sanitized_file"
        
        # Remove trailing dots (Windows issue)
        safe_filename = safe_filename.rstrip('.')
        
        # Handle hidden files (starting with dot)
        if safe_filename.startswith('.'):
            safe_filename = safe_filename[1:]
            if not safe_filename:
                return "hidden"
        
        # Limit length
        if len(safe_filename) > 200:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:200-len(ext)] + ext
        
        return safe_filename

    @staticmethod
    def is_safe_path(path: str) -> bool:
        """Check if path is safe (no directory traversal)"""
        if not path:
            return False
        
        # Normalize the path
        try:
            normalized = os.path.normpath(path)
        except ValueError:
            return False
        
        # Check for directory traversal
        if normalized.startswith('..') or '/..' in normalized or '\\..\\' in normalized:
            return False
        
        # Check for absolute paths
        if os.path.isabs(normalized):
            return False
        
        return True

    @staticmethod
    def validate_file_size(size: int) -> bool:
        """Check if file size is within limits"""
        return size <= Config.MAX_FILE_SIZE

    @staticmethod
    def validate_repository_size(size: int) -> bool:
        """Check if repository size is within limits"""
        return size <= Config.MAX_REPOSITORY_SIZE

    @staticmethod
    def validate_file_count(count: int) -> bool:
        """Check if file count is within limits"""
        return count <= Config.MAX_FILES_COUNT

    @staticmethod
    def is_text_file(filename: str, content: bytes = None) -> bool:
        """Determine if file is likely text-based"""
        if not filename:
            return False

        ext = Path(filename).suffix.lower()
        
        # Check binary extensions
        if ext in Config.BINARY_EXTENSIONS:
            return False

        # Check supported text extensions
        if ext in sum(Config.SUPPORTED_EXTENSIONS.values(), []):
            return True

        # Try to decode content if provided
        if content and len(content) > 0:
            try:
                content[:1024].decode('utf-8')
                return True
            except UnicodeDecodeError:
                return False

        # Check MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type.startswith('text/') or mime_type in [
                'application/json', 'application/xml', 'application/javascript'
            ]

        # Default to text if uncertain
        return True


class FileUtils:
    """File operation utilities"""

    @staticmethod
    def safe_read_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> Optional[str]:
        """Safely read file content with encoding fallback"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            # Try alternative encodings
            for fallback_encoding in ['latin-1', 'cp1252', 'utf-16']:
                try:
                    with open(file_path, 'r', encoding=fallback_encoding) as f:
                        return f.read()
                except (UnicodeDecodeError, UnicodeError):
                    continue
        except (FileNotFoundError, PermissionError, OSError):
            return None
        return None

    @staticmethod
    def safe_write_file(file_path: Union[str, Path], content: str, encoding: str = 'utf-8') -> bool:
        """Safely write file content"""
        try:
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            return True
        except (PermissionError, OSError, UnicodeEncodeError):
            return False

    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """Get file size safely"""
        try:
            return os.path.getsize(file_path)
        except (FileNotFoundError, OSError):
            return 0

    @staticmethod
    def ensure_directory_exists(directory: Union[str, Path]) -> bool:
        """Ensure directory exists"""
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except (PermissionError, OSError):
            return False

    @staticmethod
    def is_binary_file(file_path: Union[str, Path], check_size: int = 1024) -> bool:
        """Check if file is binary"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(check_size)
                if not chunk:
                    return False
                
                # Look for null bytes (common in binary files)
                if b'\x00' in chunk:
                    return True
                
                # Check for high percentage of non-text characters
                text_chars = sum(1 for byte in chunk if 32 <= byte <= 126 or byte in [9, 10, 13])
                return (text_chars / len(chunk)) < 0.75
        except (FileNotFoundError, PermissionError, OSError):
            return False

    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize file path for cross-platform compatibility"""
        return str(Path(path).as_posix())

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get normalized file extension"""
        return Path(filename).suffix.lower()

    @staticmethod
    def calculate_file_hash(content: Union[str, bytes]) -> str:
        """Calculate file content hash"""
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()[:16]

    @staticmethod
    def safe_filename(filename: str) -> str:
        """Create safe filename for filesystem"""
        safe_chars = re.sub(r'[<>:"/\\|?*]', '_', filename)
        return safe_chars[:200]  # Limit length

    @staticmethod
    def count_lines(content: str) -> int:
        """Count lines in text content"""
        if not content:
            return 0
        return len(content.splitlines())

    @staticmethod
    def detect_encoding(content: bytes) -> str:
        """Detect text encoding using built-in methods"""
        # Simple encoding detection without external dependencies
        encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252', 'ascii']
        
        for encoding in encodings:
            try:
                content.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue
        
        # Final fallback
        return 'utf-8'


class CompressionUtils:
    """Compression and decompression utilities"""

    @staticmethod
    def detect_compression(filename: str) -> Optional[str]:
        """Detect compression type from filename"""
        ext = Path(filename).suffix.lower()
        compression_map = {
            '.gz': 'gzip',
            '.bz2': 'bzip2',
            '.xz': 'lzma',
            '.lzma': 'lzma'
        }
        return compression_map.get(ext)

    @staticmethod
    def decompress_file(source_path: Union[str, Path], target_path: Union[str, Path]) -> bool:
        """Decompress file to target location"""
        source_path = Path(source_path)
        target_path = Path(target_path)
        
        compression = CompressionUtils.detect_compression(str(source_path))
        
        try:
            with open(source_path, 'rb') as src:
                content = src.read()
            
            if compression == 'gzip':
                content = gzip.decompress(content)
            elif compression == 'bzip2':
                content = bz2.decompress(content)
            elif compression == 'lzma':
                content = lzma.decompress(content)
            # If no compression, content remains as-is
            
            with open(target_path, 'wb') as tgt:
                tgt.write(content)
            
            return True
        except Exception as e:
            raise CompressionError(f"Decompression failed: {e}")

    @staticmethod
    def compress_file(source_path: Union[str, Path], target_path: Union[str, Path], 
                     compression: str) -> bool:
        """Compress file to target location"""
        source_path = Path(source_path)
        target_path = Path(target_path)
        
        try:
            with open(source_path, 'rb') as src:
                content = src.read()
            
            if compression == 'gzip':
                content = gzip.compress(content)
            elif compression == 'bzip2':
                content = bz2.compress(content)
            elif compression == 'lzma':
                content = lzma.compress(content)
            else:
                raise CompressionError(f"Unsupported compression format: {compression}")
            
            with open(target_path, 'wb') as tgt:
                tgt.write(content)
            
            return True
        except Exception as e:
            raise CompressionError(f"Compression failed: {e}")

    @staticmethod
    def decompress_content(content: bytes, compression: str) -> bytes:
        """Decompress content based on compression type"""
        try:
            if compression == 'gzip':
                return gzip.decompress(content)
            elif compression == 'bzip2':
                return bz2.decompress(content)
            elif compression in ['lzma', 'xz']:
                return lzma.decompress(content)
            else:
                return content
        except Exception as e:
            raise CompressionError(f"Failed to decompress content: {e}")


@contextmanager
def temporary_directory():
    """Create and cleanup temporary directory"""
    temp_dir = tempfile.mkdtemp()
    try:
        yield Path(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class RetryUtils:
    """Retry mechanism utilities"""

    @staticmethod
    def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
        """Calculate exponential backoff delay"""
        delay = base_delay * (2 ** attempt)
        jitter = random.uniform(0.1, 0.3) * delay
        return min(delay + jitter, max_delay)

    @staticmethod
    def retry_with_backoff(max_attempts: int = 3, base_delay: float = 1.0):
        """Decorator for retry with exponential backoff"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            delay = RetryUtils.exponential_backoff(attempt, base_delay)
                            import time
                            time.sleep(delay)
                        else:
                            break
                
                raise last_exception
            return wrapper
        return decorator


class TokenUtils:
    """GitHub token utility functions with .env file support"""

    @staticmethod
    def _parse_env_file(env_path: str) -> Dict[str, str]:
        """Parse .env file and return key-value pairs"""
        env_vars = {}
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        
                        env_vars[key] = value
        except (FileNotFoundError, PermissionError, UnicodeDecodeError):
            # Silently ignore file access errors
            pass
        
        return env_vars

    @staticmethod
    def _find_env_files() -> List[str]:
        """Find .env files in current directory and parent directories"""
        env_files = []
        current_dir = Path.cwd()
        
        # Check current directory and up to 3 parent directories
        for _ in range(4):
            env_file = current_dir / '.env'
            if env_file.exists() and env_file.is_file():
                env_files.append(str(env_file))
            
            parent = current_dir.parent
            if parent == current_dir:  # Reached root
                break
            current_dir = parent
        
        return env_files

    @staticmethod
    def _load_env_variables() -> Dict[str, str]:
        """Load environment variables from .env files"""
        all_env_vars = {}
        
        # Find and parse .env files
        env_files = TokenUtils._find_env_files()
        for env_file in env_files:
            env_vars = TokenUtils._parse_env_file(env_file)
            all_env_vars.update(env_vars)
        
        return all_env_vars

    @staticmethod
    def get_github_token(provided_token: Optional[str] = None) -> Optional[str]:
        """
        Get GitHub token from multiple sources with priority order:
        1. Provided token parameter
        2. GITHUB_TOKEN environment variable
        3. GH_TOKEN environment variable (GitHub CLI)
        4. .env file GITHUB_TOKEN
        5. .env file GH_TOKEN
        6. None if not found
        """
        # Priority 1: Explicitly provided token
        if provided_token and provided_token.strip():
            return provided_token.strip()
        
        # Priority 2-3: System environment variables
        for env_var in ['GITHUB_TOKEN', 'GH_TOKEN']:
            token = os.environ.get(env_var)
            if token and token.strip():
                return token.strip()
        
        # Priority 4-5: .env file variables
        env_vars = TokenUtils._load_env_variables()
        for env_var in ['GITHUB_TOKEN', 'GH_TOKEN']:
            token = env_vars.get(env_var)
            if token and token.strip():
                return token.strip()
        
        # Priority 6: No token found
        return None

    @staticmethod
    def mask_token(token: Optional[str]) -> str:
        """Mask token for safe logging"""
        if not token:
            return "None"
        
        if len(token) <= 8:
            return "***"
        
        return f"{token[:4]}...{token[-4:]}"

    @staticmethod
    def validate_token_format(token: Optional[str]) -> bool:
        """Validate GitHub token format (uses ValidationUtils method)"""
        return ValidationUtils.validate_github_token(token)

    @staticmethod
    def get_token_info(token: Optional[str]) -> Dict[str, Union[str, bool]]:
        """Get token information for logging"""
        if not token:
            return {
                'status': 'not_provided',
                'type': 'none',
                'masked': 'Not provided',
                'valid': False,
                'source': 'none'
            }

        masked = TokenUtils.mask_token(token)
        valid = TokenUtils.validate_token_format(token)

        # Determine token type
        token_type = 'unknown'
        if token.startswith('ghp_'):
            token_type = 'classic'
        elif token.startswith('ghs_'):
            token_type = 'app'
        elif token.startswith('gho_'):
            token_type = 'oauth'
        elif token.startswith('ghr_'):
            token_type = 'refresh'
        elif token.startswith('github_pat_'):
            token_type = 'fine_grained'
        elif len(token) == 40 and all(c in '0123456789abcdef' for c in token.lower()):
            token_type = 'legacy'

        # Determine source
        source = 'parameter'
        if os.environ.get('GITHUB_TOKEN') == token:
            source = 'GITHUB_TOKEN env'
        elif os.environ.get('GH_TOKEN') == token:
            source = 'GH_TOKEN env'
        else:
            env_vars = TokenUtils._load_env_variables()
            if env_vars.get('GITHUB_TOKEN') == token:
                source = '.env file'
            elif env_vars.get('GH_TOKEN') == token:
                source = '.env file'

        return {
            'status': 'provided',
            'type': token_type,
            'masked': masked,
            'valid': valid,
            'source': source
        }

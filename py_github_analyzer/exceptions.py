"""

Custom exceptions for py-github-analyzer

Enhanced error handling with private repository detection

"""


class GitHubAnalyzerError(Exception):
    """Base exception for GitHub Analyzer"""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class NetworkError(GitHubAnalyzerError):
    """Network-related errors"""
    pass


class RateLimitExceededError(GitHubAnalyzerError):
    """GitHub API rate limit exceeded"""
    
    def __init__(self, message: str, reset_time: int = None, remaining: int = None):
        super().__init__(message)
        self.reset_time = reset_time
        self.remaining = remaining


class AuthenticationError(GitHubAnalyzerError):
    """GitHub authentication failed"""
    pass


class RepositoryNotFoundError(GitHubAnalyzerError):
    """Repository not found or not accessible"""
    pass


class PrivateRepositoryError(AuthenticationError):
    """Private repository detected - requires GitHub token"""
    
    def __init__(self, message: str, repo_url: str = ""):
        super().__init__(message)
        self.repo_url = repo_url


class RepositoryTooLargeError(GitHubAnalyzerError):
    """Repository exceeds size limits"""
    
    def __init__(self, message: str, size_mb: float, limit_mb: float):
        super().__init__(message)
        self.size_mb = size_mb
        self.limit_mb = limit_mb


class InvalidRepositoryURLError(GitHubAnalyzerError):
    """Invalid repository URL format"""
    pass


class FileProcessingError(GitHubAnalyzerError):
    """Error processing repository files"""
    pass


class ValidationError(GitHubAnalyzerError):
    """Data validation failed"""
    pass


class CompressionError(GitHubAnalyzerError):
    """Compression/decompression failed"""
    pass


class UnsupportedFormatError(GitHubAnalyzerError):
    """Unsupported file or output format"""
    pass


class OutputError(GitHubAnalyzerError):
    """Error writing output files"""
    pass


class AnalyzerTimeoutError(GitHubAnalyzerError):
    """Operation timeout exceeded (renamed to avoid Python builtin conflict)"""
    
    def __init__(self, message: str, timeout_seconds: int):
        super().__init__(message)
        self.timeout_seconds = timeout_seconds


class EmptyRepositoryError(GitHubAnalyzerError):
    """Raised when repository exists but contains no analyzable files"""
    
    def __init__(self, message: str, repo_url: str, file_count: int = 0):
        super().__init__(message)
        self.repo_url = repo_url
        self.file_count = file_count


class RepositoryContentError(GitHubAnalyzerError):
    """Raised when repository content cannot be analyzed"""
    
    def __init__(self, message: str, repo_url: str, reason: str):
        super().__init__(message)
        self.repo_url = repo_url
        self.reason = reason


def handle_github_api_error(status_code: int, response_data: dict = None, repo_url: str = "") -> GitHubAnalyzerError:
    """
    Convert GitHub API error responses to appropriate exceptions
    Enhanced with private repository detection
    """
    if status_code == 401:
        return AuthenticationError(
            "GitHub authentication failed. Your token may be invalid or expired.\n"
            "Get a new token at: https://github.com/settings/tokens"
        )
    
    elif status_code == 403:
        if response_data and "rate limit" in str(response_data).lower():
            # Rate limit error
            reset_time = response_data.get('reset', 0) if response_data else 0
            remaining = response_data.get('remaining', 0) if response_data else 0
            return RateLimitExceededError(
                "GitHub API rate limit exceeded. Please wait or use a personal access token for higher limits.",
                reset_time=reset_time,
                remaining=remaining
            )
        else:
            # Likely private repository or insufficient permissions
            return PrivateRepositoryError(
                "Repository appears to be private or requires authentication.\n"
                "If this is a private repository, you need a GitHub token with 'repo' scope.\n"
                "Get a token at: https://github.com/settings/tokens",
                repo_url
            )
    
    elif status_code == 404:
        # Could be private repo OR truly not found - will be refined by caller
        return RepositoryNotFoundError(
            "Repository not found, private, or requires authentication.\n"
            "Please verify the repository URL and access permissions."
        )
    
    elif status_code == 422:
        return ValidationError(
            "Invalid request parameters. Please check the repository URL format."
        )
    
    elif status_code >= 500:
        return NetworkError(
            f"GitHub server error (HTTP {status_code}). Please try again later."
        )
    
    else:
        return GitHubAnalyzerError(
            f"Unexpected GitHub API error (HTTP {status_code}). Please try again."
        )


def create_private_repo_guidance_message(owner: str, repo: str, has_token: bool = False) -> str:
    """Create a helpful message for private repository access"""
    repo_name = f"{owner}/{repo}"
    repo_url = f"https://github.com/{repo_name}"
    
    if not has_token:
        return (
            f"🔒 Repository '{repo_name}' appears to be private and requires authentication.\n\n"
            f"📋 To access private repositories:\n"
            f"  1. Visit: https://github.com/settings/tokens\n"
            f"  2. Click 'Generate new token (classic)'\n"
            f"  3. Select 'repo' scope for private repository access\n"
            f"  4. Copy the generated token\n"
            f"  5. Use it with your analysis\n\n"
            f"💡 CLI Example:\n"
            f"  py-github-analyzer {repo_url} --github-token YOUR_TOKEN\n\n"
            f"💡 Python Example:\n"
            f"  pga.analyze_repository('{repo_url}', github_token='YOUR_TOKEN')"
        )
    else:
        return (
            f"🔐 Repository '{repo_name}' is private and your token doesn't have access.\n\n"
            f"🔍 Please check:\n"
            f"  • Your token has 'repo' scope enabled\n"
            f"  • You have access permissions to this repository\n"
            f"  • The repository hasn't been deleted or moved\n\n"
            f"🔧 To fix token permissions:\n"
            f"  1. Visit: https://github.com/settings/tokens\n"
            f"  2. Edit your existing token\n"
            f"  3. Ensure 'repo' scope is selected\n"
            f"  4. Update the token if needed"
        )


def create_repo_not_found_message(owner: str, repo: str) -> str:
    """Create a helpful message for repository not found errors"""
    repo_name = f"{owner}/{repo}"
    repo_url = f"https://github.com/{repo_name}"
    
    return (
        f"❌ Repository '{repo_name}' does not exist or is not accessible.\n\n"
        f"🔍 Please verify:\n"
        f"  • Repository URL is correct: {repo_url}\n"
        f"  • Repository is public OR you have a valid token\n"
        f"  • Repository owner and name are spelled correctly\n"
        f"  • Repository hasn't been deleted, renamed, or moved\n\n"
        f"💡 If this is a private repository, use:\n"
        f"  py-github-analyzer {repo_url} --github-token YOUR_TOKEN"
    )


def suggest_token_creation() -> str:
    """Create a helpful token creation guide"""
    return (
        "🔑 GitHub Personal Access Token Required\n\n"
        "📋 Create a token in 4 easy steps:\n"
        "  1. Go to: https://github.com/settings/tokens\n"
        "  2. Click 'Generate new token (classic)'\n"
        "  3. Select scopes:\n"
        "     • 'repo' - for private repositories\n"
        "     • 'public_repo' - for public repositories (optional)\n"
        "  4. Copy the generated token (starts with 'ghp_' or 'github_pat_')\n\n"
        "⚠️ Important:\n"
        "  • Save your token safely - you can't see it again!\n"
        "  • Never share your token publicly\n"
        "  • Tokens provide the same access as your GitHub password\n\n"
        "💡 Usage examples:\n"
        "  CLI: py-github-analyzer [URL] -t YOUR_TOKEN\n"
        "  Python: pga.analyze_repository(url, github_token='YOUR_TOKEN')"
    )


# Backward compatibility alias (in case the old name was used)
TimeoutError = AnalyzerTimeoutError

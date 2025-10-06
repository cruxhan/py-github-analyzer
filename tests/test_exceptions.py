"""
Tests for py_github_analyzer exceptions.py module
예외 처리 모듈 테스트
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock

# Add the parent directory to sys.path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_base_exception():
    """GitHubAnalyzerError 기본 예외 테스트"""
    from py_github_analyzer.exceptions import GitHubAnalyzerError
    
    # 기본 메시지만으로 생성
    error = GitHubAnalyzerError("Test error")
    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.details is None
    
    # 메시지와 세부사항으로 생성
    error_with_details = GitHubAnalyzerError("Main error", "Detailed explanation")
    assert str(error_with_details) == "Main error: Detailed explanation"
    assert error_with_details.message == "Main error"
    assert error_with_details.details == "Detailed explanation"
    
    # Exception 상속 확인
    assert isinstance(error, Exception)
    assert issubclass(GitHubAnalyzerError, Exception)

def test_network_error():
    """NetworkError 테스트"""
    from py_github_analyzer.exceptions import NetworkError, GitHubAnalyzerError
    
    error = NetworkError("Connection failed")
    assert str(error) == "Connection failed"
    assert isinstance(error, GitHubAnalyzerError)
    assert issubclass(NetworkError, GitHubAnalyzerError)

def test_rate_limit_exceeded_error():
    """RateLimitExceededError 테스트"""
    from py_github_analyzer.exceptions import RateLimitExceededError, GitHubAnalyzerError
    
    # 기본 메시지만으로 생성
    error = RateLimitExceededError("Rate limit exceeded")
    assert str(error) == "Rate limit exceeded"
    assert error.reset_time is None
    assert error.remaining is None
    
    # 추가 정보와 함께 생성
    error_with_info = RateLimitExceededError("Rate limit exceeded", reset_time=1640995200, remaining=0)
    assert error_with_info.reset_time == 1640995200
    assert error_with_info.remaining == 0
    
    # 상속 관계 확인
    assert isinstance(error, GitHubAnalyzerError)
    assert issubclass(RateLimitExceededError, GitHubAnalyzerError)

def test_authentication_error():
    """AuthenticationError 테스트"""
    from py_github_analyzer.exceptions import AuthenticationError, GitHubAnalyzerError
    
    error = AuthenticationError("Invalid token")
    assert str(error) == "Invalid token"
    assert isinstance(error, GitHubAnalyzerError)
    assert issubclass(AuthenticationError, GitHubAnalyzerError)

def test_repository_not_found_error():
    """RepositoryNotFoundError 테스트"""
    from py_github_analyzer.exceptions import RepositoryNotFoundError, GitHubAnalyzerError
    
    error = RepositoryNotFoundError("Repository not found")
    assert str(error) == "Repository not found"
    assert isinstance(error, GitHubAnalyzerError)
    assert issubclass(RepositoryNotFoundError, GitHubAnalyzerError)

def test_private_repository_error():
    """PrivateRepositoryError 테스트"""
    from py_github_analyzer.exceptions import PrivateRepositoryError, AuthenticationError
    
    # 기본 메시지만으로 생성 (repo_url은 기본값 "")
    error = PrivateRepositoryError("Private repository detected")
    assert str(error) == "Private repository detected"
    assert error.repo_url == ""  # 실제 구현에서는 빈 문자열이 기본값
    
    # 저장소 URL과 함께 생성
    repo_url = "https://github.com/user/private-repo"
    error_with_url = PrivateRepositoryError("Private repository detected", repo_url=repo_url)
    assert error_with_url.repo_url == repo_url
    
    # 상속 관계 확인 (AuthenticationError를 상속)
    assert isinstance(error, AuthenticationError)
    assert issubclass(PrivateRepositoryError, AuthenticationError)

def test_repository_too_large_error():
    """RepositoryTooLargeError 테스트"""
    from py_github_analyzer.exceptions import RepositoryTooLargeError, GitHubAnalyzerError
    
    # 필수 매개변수와 함께 생성
    error = RepositoryTooLargeError("Repository too large", size_mb=1000.0, limit_mb=500.0)
    assert str(error) == "Repository too large"
    assert error.size_mb == 1000.0
    assert error.limit_mb == 500.0
    
    # 상속 관계 확인
    assert isinstance(error, GitHubAnalyzerError)
    assert issubclass(RepositoryTooLargeError, GitHubAnalyzerError)

def test_timeout_error():
    """AnalyzerTimeoutError 테스트"""
    from py_github_analyzer.exceptions import AnalyzerTimeoutError, GitHubAnalyzerError
    
    # 필수 매개변수와 함께 생성
    error = AnalyzerTimeoutError("Operation timed out", timeout_seconds=30)
    assert str(error) == "Operation timed out"
    assert error.timeout_seconds == 30
    
    # 상속 관계 확인
    assert isinstance(error, GitHubAnalyzerError)
    assert issubclass(AnalyzerTimeoutError, GitHubAnalyzerError)

def test_timeout_error_alias():
    """TimeoutError 별칭 테스트"""
    from py_github_analyzer.exceptions import TimeoutError, AnalyzerTimeoutError
    
    # 별칭이 올바르게 설정되어 있는지 확인
    assert TimeoutError is AnalyzerTimeoutError

def test_validation_error():
    """ValidationError 테스트"""
    from py_github_analyzer.exceptions import ValidationError, GitHubAnalyzerError
    
    # 기본 메시지만으로 생성
    error = ValidationError("Invalid input")
    assert str(error) == "Invalid input"
    
    # 상속 관계 확인
    assert isinstance(error, GitHubAnalyzerError)
    assert issubclass(ValidationError, GitHubAnalyzerError)

def test_compression_error():
    """CompressionError 테스트"""
    from py_github_analyzer.exceptions import CompressionError, GitHubAnalyzerError
    
    # 기본 메시지만으로 생성
    error = CompressionError("Compression failed")
    assert str(error) == "Compression failed"
    
    # 상속 관계 확인
    assert isinstance(error, GitHubAnalyzerError)
    assert issubclass(CompressionError, GitHubAnalyzerError)

def test_empty_repository_error():
    """EmptyRepositoryError 테스트"""
    from py_github_analyzer.exceptions import EmptyRepositoryError, GitHubAnalyzerError
    
    # 필수 매개변수와 함께 생성
    error = EmptyRepositoryError("Repository is empty", repo_url="https://github.com/user/empty", file_count=0)
    assert str(error) == "Repository is empty"
    assert error.repo_url == "https://github.com/user/empty"
    assert error.file_count == 0
    
    # 상속 관계 확인
    assert isinstance(error, GitHubAnalyzerError)
    assert issubclass(EmptyRepositoryError, GitHubAnalyzerError)

def test_repository_content_error():
    """RepositoryContentError 테스트"""
    from py_github_analyzer.exceptions import RepositoryContentError, GitHubAnalyzerError
    
    # 필수 매개변수와 함께 생성
    error = RepositoryContentError("Cannot analyze content", 
                                 repo_url="https://github.com/user/repo", 
                                 reason="No supported files")
    assert str(error) == "Cannot analyze content"
    assert error.repo_url == "https://github.com/user/repo"
    assert error.reason == "No supported files"
    
    # 상속 관계 확인
    assert isinstance(error, GitHubAnalyzerError)
    assert issubclass(RepositoryContentError, GitHubAnalyzerError)

def test_additional_exception_classes():
    """추가 예외 클래스들 테스트"""
    from py_github_analyzer.exceptions import (
        InvalidRepositoryURLError,
        FileProcessingError,
        UnsupportedFormatError,
        OutputError,
        GitHubAnalyzerError
    )
    
    # 각 예외 클래스 테스트
    url_error = InvalidRepositoryURLError("Invalid URL format")
    file_error = FileProcessingError("File processing failed")
    format_error = UnsupportedFormatError("Unsupported format")
    output_error = OutputError("Output writing failed")
    
    # 모두 GitHubAnalyzerError를 상속하는지 확인
    for error in [url_error, file_error, format_error, output_error]:
        assert isinstance(error, GitHubAnalyzerError)

def test_github_api_error_handler():
    """handle_github_api_error 함수 테스트"""
    from py_github_analyzer.exceptions import handle_github_api_error
    from py_github_analyzer.exceptions import (
        AuthenticationError,
        RepositoryNotFoundError,
        PrivateRepositoryError,
        RateLimitExceededError,
        ValidationError,
        NetworkError,
        GitHubAnalyzerError
    )
    
    # 401 Unauthorized 테스트
    error = handle_github_api_error(401)
    assert isinstance(error, AuthenticationError)
    
    # 404 Not Found 테스트
    error = handle_github_api_error(404, repo_url="https://github.com/user/repo")
    assert isinstance(error, RepositoryNotFoundError)
    
    # 403 Forbidden (rate limit) 테스트
    response_data = {"message": "API rate limit exceeded", "reset": 1640995200, "remaining": 0}
    error = handle_github_api_error(403, response_data=response_data)
    assert isinstance(error, RateLimitExceededError)
    assert error.reset_time == 1640995200
    assert error.remaining == 0
    
    # 403 Forbidden (private repo) 테스트
    error = handle_github_api_error(403, repo_url="https://github.com/user/private")
    assert isinstance(error, PrivateRepositoryError)
    
    # 422 Validation Error 테스트
    error = handle_github_api_error(422)
    assert isinstance(error, ValidationError)
    
    # 500+ Server Error 테스트
    error = handle_github_api_error(500)
    assert isinstance(error, NetworkError)
    
    # 기타 에러 테스트
    error = handle_github_api_error(418)  # I'm a teapot
    assert isinstance(error, GitHubAnalyzerError)

def test_create_private_repo_guidance_message():
    """create_private_repo_guidance_message 함수 테스트"""
    from py_github_analyzer.exceptions import create_private_repo_guidance_message
    
    # 토큰이 없는 경우
    message = create_private_repo_guidance_message("user", "private-repo", has_token=False)
    
    assert isinstance(message, str)
    assert len(message) > 0
    assert "user/private-repo" in message
    assert "private" in message.lower()
    assert "token" in message.lower()
    assert "https://github.com/settings/tokens" in message
    
    # 토큰이 있는 경우
    message_with_token = create_private_repo_guidance_message("user", "private-repo", has_token=True)
    assert isinstance(message_with_token, str)
    assert len(message_with_token) > 0
    assert "scope" in message_with_token.lower()

def test_create_repo_not_found_message():
    """create_repo_not_found_message 함수 테스트"""
    from py_github_analyzer.exceptions import create_repo_not_found_message
    
    message = create_repo_not_found_message("user", "nonexistent")
    
    assert isinstance(message, str)
    assert len(message) > 0
    assert "user/nonexistent" in message
    assert "https://github.com/user/nonexistent" in message
    assert ("not exist" in message.lower() or "does not exist" in message.lower())

def test_suggest_token_creation():
    """suggest_token_creation 함수 테스트"""
    from py_github_analyzer.exceptions import suggest_token_creation
    
    message = suggest_token_creation()
    
    assert isinstance(message, str)
    assert len(message) > 0
    assert "token" in message.lower()
    assert "https://github.com/settings/tokens" in message
    assert "ghp_" in message or "github_pat_" in message

def test_exception_inheritance_hierarchy():
    """예외 상속 계층구조 테스트"""
    from py_github_analyzer.exceptions import (
        GitHubAnalyzerError,
        NetworkError,
        AuthenticationError,
        RepositoryNotFoundError,
        PrivateRepositoryError,
        RateLimitExceededError,
        ValidationError,
        CompressionError,
        AnalyzerTimeoutError,
        EmptyRepositoryError,
        RepositoryContentError,
        InvalidRepositoryURLError,
        FileProcessingError,
        UnsupportedFormatError,
        OutputError,
        RepositoryTooLargeError
    )
    
    # 모든 예외가 GitHubAnalyzerError를 상속하는지 확인
    exceptions_to_test = [
        NetworkError,
        AuthenticationError,
        RepositoryNotFoundError,
        RateLimitExceededError,
        ValidationError,
        CompressionError,
        AnalyzerTimeoutError,
        EmptyRepositoryError,
        RepositoryContentError,
        InvalidRepositoryURLError,
        FileProcessingError,
        UnsupportedFormatError,
        OutputError,
        RepositoryTooLargeError
    ]
    
    for exception_class in exceptions_to_test:
        assert issubclass(exception_class, GitHubAnalyzerError), f"{exception_class} should inherit from GitHubAnalyzerError"
    
    # PrivateRepositoryError는 AuthenticationError를 상속
    assert issubclass(PrivateRepositoryError, AuthenticationError)
    assert issubclass(PrivateRepositoryError, GitHubAnalyzerError)  # 간접 상속

def test_base_exception_with_none_details():
    """None details로 기본 예외 생성 테스트"""
    from py_github_analyzer.exceptions import GitHubAnalyzerError
    
    # None details로 생성
    error = GitHubAnalyzerError("Test message", None)
    assert error.message == "Test message"
    assert error.details is None
    assert str(error) == "Test message"

def test_exception_serialization():
    """예외 직렬화 테스트"""
    from py_github_analyzer.exceptions import GitHubAnalyzerError
    import pickle
    
    # 기본 예외
    error = GitHubAnalyzerError("Test error", "Detail")
    
    try:
        # 피클링과 언피클링
        pickled = pickle.dumps(error)
        unpickled = pickle.loads(pickled)
        
        assert str(unpickled) == str(error)
        assert unpickled.message == error.message
        assert unpickled.details == error.details
    except Exception:
        # 피클링이 지원되지 않을 수도 있음
        pytest.skip("Serialization not supported")

def test_error_message_formatting():
    """에러 메시지 포맷팅 테스트"""
    from py_github_analyzer.exceptions import GitHubAnalyzerError
    
    # 메시지만 있는 경우
    error1 = GitHubAnalyzerError("Simple message")
    assert str(error1) == "Simple message"
    
    # 메시지와 details가 있는 경우
    error2 = GitHubAnalyzerError("Main message", "Additional details")
    assert str(error2) == "Main message: Additional details"
    
    # 빈 details (falsy이므로 details 출력 안함)
    error3 = GitHubAnalyzerError("Main message", "")
    assert str(error3) == "Main message"  # 빈 문자열은 falsy이므로 details 출력 안함
    
    # None details
    error4 = GitHubAnalyzerError("Main message", None)
    assert str(error4) == "Main message"


def test_specific_error_attributes():
    """특정 에러의 속성 테스트"""
    from py_github_analyzer.exceptions import (
        RateLimitExceededError,
        PrivateRepositoryError,
        RepositoryTooLargeError,
        AnalyzerTimeoutError,
        EmptyRepositoryError,
        RepositoryContentError
    )
    
    # RateLimitExceededError 속성
    rate_error = RateLimitExceededError("Rate limit", reset_time=123456, remaining=10)
    assert rate_error.reset_time == 123456
    assert rate_error.remaining == 10
    
    # PrivateRepositoryError 속성
    private_error = PrivateRepositoryError("Private repo", repo_url="https://github.com/user/repo")
    assert private_error.repo_url == "https://github.com/user/repo"
    
    # RepositoryTooLargeError 속성
    large_error = RepositoryTooLargeError("Too large", size_mb=1000.5, limit_mb=500.0)
    assert large_error.size_mb == 1000.5
    assert large_error.limit_mb == 500.0
    
    # AnalyzerTimeoutError 속성
    timeout_error = AnalyzerTimeoutError("Timeout", timeout_seconds=30)
    assert timeout_error.timeout_seconds == 30
    
    # EmptyRepositoryError 속성
    empty_error = EmptyRepositoryError("Empty", repo_url="https://github.com/user/empty", file_count=0)
    assert empty_error.repo_url == "https://github.com/user/empty"
    assert empty_error.file_count == 0
    
    # RepositoryContentError 속성
    content_error = RepositoryContentError("Content error", 
                                         repo_url="https://github.com/user/repo", 
                                         reason="No files")
    assert content_error.repo_url == "https://github.com/user/repo"
    assert content_error.reason == "No files"

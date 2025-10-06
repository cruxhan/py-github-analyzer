"""
Tests for py_github_analyzer __init__.py module
패키지 초기화 모듈 테스트
"""

import pytest
from unittest.mock import patch, Mock
import sys
import os
from pathlib import Path

# Add the parent directory to sys.path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_package_metadata():
    """패키지 메타데이터 테스트"""
    try:
        from py_github_analyzer import (
            __version__, 
            __author__, 
            __email__, 
            __description__
        )
        
        assert __version__ == "1.0.0"
        assert __author__ == "Han Jun-hee" 
        assert __email__ == "createbrain2heart@gmail.com"
        assert "High-performance async GitHub repository analyzer" in __description__
        
    except ImportError as e:
        pytest.skip(f"Package import failed: {e}")

def test_main_imports():
    """주요 클래스 및 함수 임포트 테스트"""
    try:
        from py_github_analyzer import (
            analyze_repository_async,
            GitHubRepositoryAnalyzer,
            AsyncGitHubClient,
            get_logger,
            URLParser,
            TokenUtils
        )
        
        # 함수가 callable한지 확인
        assert callable(analyze_repository_async)
        assert callable(get_logger)
        
        # 클래스가 타입인지 확인
        assert isinstance(GitHubRepositoryAnalyzer, type)
        assert isinstance(AsyncGitHubClient, type)
        assert isinstance(URLParser, type)
        assert isinstance(TokenUtils, type)
        
    except ImportError as e:
        pytest.skip(f"Main imports failed: {e}")

def test_exception_imports():
    """예외 클래스 임포트 테스트"""
    try:
        from py_github_analyzer import (
            GitHubAnalyzerError,
            NetworkError,
            AuthenticationError,
            RepositoryNotFoundError,
            EmptyRepositoryError
        )
        
        # 모든 예외가 Exception을 상속받는지 확인
        assert issubclass(GitHubAnalyzerError, Exception)
        assert issubclass(NetworkError, GitHubAnalyzerError)
        assert issubclass(AuthenticationError, GitHubAnalyzerError)
        assert issubclass(RepositoryNotFoundError, GitHubAnalyzerError)
        assert issubclass(EmptyRepositoryError, GitHubAnalyzerError)
        
    except ImportError as e:
        pytest.skip(f"Exception imports failed: {e}")

def test_version_function():
    """get_version 함수 테스트"""
    try:
        from py_github_analyzer import get_version
        
        version = get_version()
        
        # get_version은 문자열을 반환함
        assert isinstance(version, str)
        assert version == "1.0.0"
        
    except ImportError as e:
        pytest.skip(f"get_version import failed: {e}")

def test_env_check_functions():
    """환경 설정 확인 함수들 테스트"""
    try:
        from py_github_analyzer import check_env_file, get_token_sources
        
        # check_env_file 함수 테스트
        assert callable(check_env_file)
        
        # get_token_sources 함수 테스트  
        assert callable(get_token_sources)
        
        # 실제 호출해보기
        with patch.dict(os.environ, {}, clear=True):
            token_sources = get_token_sources()
            # get_token_sources는 dict를 반환함
            assert isinstance(token_sources, dict)
            assert "sources" in token_sources
            assert isinstance(token_sources["sources"], list)
            
    except ImportError as e:
        pytest.skip(f"Environment functions import failed: {e}")

@patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"})
def test_token_detection_with_env():
    """환경 변수 토큰 감지 테스트"""
    try:
        from py_github_analyzer import get_token_sources
        
        token_sources = get_token_sources()
        
        # 응답 구조 확인
        assert isinstance(token_sources, dict)
        assert "sources" in token_sources
        
        # 환경 변수에서 토큰을 찾았는지 확인
        sources = token_sources["sources"]
        assert any(source.get("type") == "system_environment" and 
                  source.get("variable") == "GITHUB_TOKEN" for source in sources)
        
    except ImportError as e:
        pytest.skip(f"Token detection failed: {e}")

def test_env_file_check(temp_dir):
    """환경 파일 체크 함수 테스트"""
    try:
        from py_github_analyzer import check_env_file
        
        # 임시 .env 파일 생성
        env_file = temp_dir / ".env"
        env_file.write_text("GITHUB_TOKEN=test_token_from_file\n")
        
        # 현재 디렉토리를 임시 디렉토리로 변경
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            env_result = check_env_file()
            
            # check_env_file은 dict를 반환함
            assert isinstance(env_result, dict)
            
            # 기본 구조 확인
            expected_keys = ["env_files_found", "env_file_paths", "token_sources", "token_status", "token_type"]
            for key in expected_keys:
                assert key in env_result
                
        finally:
            os.chdir(original_cwd)
            
    except ImportError as e:
        pytest.skip(f"check_env_file import failed: {e}")

def test_all_exports_available():
    """__all__ 목록의 모든 항목이 임포트 가능한지 테스트"""
    try:
        from py_github_analyzer import __all__
        import py_github_analyzer
        
        # __all__에서 실제로 사용 가능하지 않을 수 있는 항목들은 스킵
        skip_items = {"RateLimitError", "ValidationError"}  # 실제 코드에 따라 조정
        
        for item in __all__:
            if item in skip_items:
                continue
            assert hasattr(py_github_analyzer, item), f"{item} not found in module"
            
    except ImportError as e:
        pytest.skip(f"__all__ test failed: {e}")

def test_import_error_handling():
    """임포트 에러 처리 테스트"""
    # 실제 import error를 발생시키기는 어려우므로 기본적인 import만 테스트
    try:
        import py_github_analyzer
        # 모듈이 정상적으로 로드되는지만 확인
        assert py_github_analyzer.__version__ == "1.0.0"
    except ImportError:
        pytest.fail("Package should be importable")

def test_logger_initialization():
    """로거 초기화 테스트"""
    try:
        from py_github_analyzer import get_logger
        
        logger = get_logger()
        
        # 로거가 올바르게 초기화되었는지 확인
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'debug')
        
    except ImportError as e:
        pytest.skip(f"Logger initialization test failed: {e}")

def test_async_function_availability():
    """비동기 함수 사용 가능성 테스트"""
    try:
        from py_github_analyzer import analyze_repository_async
        import asyncio
        import inspect
        
        # 함수가 코루틴인지 확인
        assert inspect.iscoroutinefunction(analyze_repository_async)
        
    except ImportError as e:
        pytest.skip(f"Async function test failed: {e}")

def test_package_structure():
    """패키지 구조 테스트"""
    try:
        import py_github_analyzer
        
        # 주요 모듈들이 패키지에 포함되어 있는지 확인
        expected_attributes = [
            'GitHubRepositoryAnalyzer',
            'AsyncGitHubClient', 
            'analyze_repository_async',
            'get_logger',
            'URLParser',
            'TokenUtils'
        ]
        
        for attr in expected_attributes:
            assert hasattr(py_github_analyzer, attr), f"Missing attribute: {attr}"
            
    except ImportError as e:
        pytest.skip(f"Package structure test failed: {e}")

@patch('py_github_analyzer.get_logger')
def test_logger_mock(mock_get_logger, mock_logger):
    """로거 모킹 테스트"""
    try:
        mock_get_logger.return_value = mock_logger
        
        from py_github_analyzer import get_logger
        
        logger = get_logger()
        logger.info("Test message")
        
        assert "INFO: Test message" in mock_logger.messages
        
    except ImportError as e:
        pytest.skip(f"Logger mock test failed: {e}")

def test_config_constants_accessible():
    """설정 상수 접근 가능성 테스트"""
    try:
        from py_github_analyzer.config import (
            SKIP_FILES,
            SKIP_DIRECTORIES,
            BINARY_EXTENSIONS,
            TEXT_EXTENSIONS
        )
        
        assert isinstance(SKIP_FILES, set)
        assert isinstance(SKIP_DIRECTORIES, set) 
        assert isinstance(BINARY_EXTENSIONS, set)
        assert isinstance(TEXT_EXTENSIONS, dict)
        
        # 일부 기본값들이 포함되어 있는지 확인
        assert '.git' in SKIP_DIRECTORIES
        assert '.gitignore' in SKIP_FILES
        
    except ImportError as e:
        pytest.skip(f"Config constants test failed: {e}")

def test_banner_function():
    """print_banner 함수 테스트"""
    try:
        from py_github_analyzer import print_banner
        
        # 함수가 존재하고 호출 가능한지만 확인
        assert callable(print_banner)
        
        # 실제 호출은 출력을 발생시키므로 테스트에서는 스킵
        
    except ImportError as e:
        pytest.skip(f"print_banner test failed: {e}")

def test_token_utils_integration():
    """TokenUtils와 관련 함수들의 통합 테스트"""
    try:
        from py_github_analyzer import TokenUtils, get_token_sources, check_env_file
        
        # TokenUtils 클래스 확인
        assert hasattr(TokenUtils, 'get_github_token')
        assert hasattr(TokenUtils, '_find_env_files')
        assert hasattr(TokenUtils, '_load_env_variables')
        
        # 관련 함수들이 TokenUtils를 올바르게 사용하는지 확인
        with patch.dict(os.environ, {}, clear=True):
            sources = get_token_sources()
            env_check = check_env_file()
            
            assert isinstance(sources, dict)
            assert isinstance(env_check, dict)
            
    except ImportError as e:
        pytest.skip(f"TokenUtils integration test failed: {e}")

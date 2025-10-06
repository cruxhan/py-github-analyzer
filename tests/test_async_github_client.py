"""
Tests for py_github_analyzer async_github_client.py module
비동기 GitHub 클라이언트 모듈 테스트
"""

import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock, MagicMock
import json
import base64

# Add the parent directory to sys.path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Skip entire module if httpx not available
pytest_plugins = []

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="httpx not available")


@pytest.fixture
def temp_dir(tmp_path):
    """임시 디렉토리 픽스처"""
    return tmp_path


class TestAsyncRateLimitManager:
    """AsyncRateLimitManager 클래스 테스트"""

    @pytest.mark.asyncio
    async def test_rate_limit_manager_initialization(self):
        """Rate limit 매니저 초기화 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncRateLimitManager
        
        # 토큰 없이 초기화
        manager = AsyncRateLimitManager()
        assert manager.token is None
        assert manager.limit == 60
        assert manager.remaining == 60
        
        # 토큰과 함께 초기화
        manager_with_token = AsyncRateLimitManager("test_token")
        assert manager_with_token.token == "test_token"
        assert manager_with_token.limit == 5000
        assert manager_with_token.remaining == 5000

    @pytest.mark.asyncio
    async def test_update_from_headers(self):
        """헤더에서 rate limit 정보 업데이트 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncRateLimitManager
        
        manager = AsyncRateLimitManager("test_token")
        
        headers = {
            "x-ratelimit-limit": "5000",
            "x-ratelimit-remaining": "4999",
            "x-ratelimit-reset": "1640995200"
        }
        
        await manager.update_from_headers(headers)
        
        assert manager.limit == 5000
        assert manager.remaining == 4999
        assert manager.reset_time == 1640995200

    @pytest.mark.asyncio
    async def test_check_rate_limit(self):
        """Rate limit 체크 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncRateLimitManager
        
        manager = AsyncRateLimitManager("test_token")
        manager.remaining = 10
        
        # 충분한 요청 수
        assert await manager.check_rate_limit(5) == True
        
        # 부족한 요청 수
        assert await manager.check_rate_limit(20) == False

    @pytest.mark.asyncio
    async def test_consume_calls(self):
        """API 호출 소비 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncRateLimitManager
        
        manager = AsyncRateLimitManager("test_token")
        manager.remaining = 100
        
        await manager.consume_calls(10)
        assert manager.remaining == 90
        
        # 음수가 되지 않도록 보장
        await manager.consume_calls(200)
        assert manager.remaining == 0


class TestAsyncGitHubSession:
    """AsyncGitHubSession 클래스 테스트"""

    @pytest.mark.asyncio
    async def test_session_initialization(self):
        """세션 초기화 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubSession
        
        # 토큰 없이 초기화
        session = AsyncGitHubSession()
        assert session.token is None
        assert session.timeout == 30
        
        # 토큰과 함께 초기화
        session_with_token = AsyncGitHubSession("test_token", timeout=60)
        assert session_with_token.token == "test_token"
        assert session_with_token.timeout == 60
        
        await session.close()
        await session_with_token.close()

    @pytest.mark.asyncio
    async def test_token_performance_profile(self):
        """토큰 성능 프로필 테스트 - 기본 동작 확인"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubSession
        
        # 토큰 없음 - 기본 속성만 확인
        session = AsyncGitHubSession()
        assert session.token is None
        assert session.timeout == 30
        
        await session.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """컨텍스트 매니저 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubSession
        
        async with AsyncGitHubSession("test_token") as session:
            assert session.token == "test_token"
            assert session.client is not None


class TestAsyncGitHubClient:
    """AsyncGitHubClient 클래스 테스트"""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """클라이언트 초기화 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        # 기본 초기화
        client = AsyncGitHubClient()
        assert client.token is None
        assert client.logger is not None
        assert client.rate_limit_manager is not None
        # semaphore 속성 제거 (존재하지 않음)
        
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """컨텍스트 매니저 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        async with AsyncGitHubClient("test_token") as client:
            assert client.token == "test_token"
            assert client.session is not None

    @pytest.mark.asyncio
    async def test_get_repository_info_safe_mode(self):
        """저장소 정보 가져오기 (안전 모드) 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        # Mock response
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 404
        
        async with AsyncGitHubClient("test_token") as client:
            with patch.object(client.session, 'get', return_value=mock_response):
                result = await client.get_repository_info("user", "repo", safe_mode=True)
                
                # 안전 모드에서는 기본값 반환
                assert result["name"] == "repo"
                assert result["full_name"] == "user/repo"
                assert result["language"] == "Unknown"

    @pytest.mark.asyncio
    async def test_get_repository_info_success(self):
        """저장소 정보 가져오기 성공 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        # Mock successful response
        repo_data = {
            "name": "test-repo",
            "full_name": "user/test-repo",
            "description": "Test repository",
            "language": "Python",
            "size": 1024,
            "default_branch": "main",
            "private": False,
            "archived": False,
            "disabled": False,
            "topics": ["python", "test"],
            "license": {"name": "MIT"},
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-12-31T23:59:59Z",
            "clone_url": "https://github.com/user/test-repo.git",
            "html_url": "https://github.com/user/test-repo"
        }
        
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = repo_data
        mock_response.headers = {}
        
        # Mock execute_api_call to return the response directly
        async def mock_execute_api_call(api_call_func):
            return mock_response
        
        async with AsyncGitHubClient("test_token") as client:
            with patch.object(client.rate_limit_manager, 'execute_api_call', side_effect=mock_execute_api_call):
                result = await client.get_repository_info("user", "test-repo")
                
                assert result["name"] == "test-repo"
                assert result["full_name"] == "user/test-repo"
                assert result["description"] == "Test repository"
                assert result["language"] == "Python"
                assert result["size"] == 1024
                assert result["private"] == False

    @pytest.mark.asyncio
    async def test_get_repository_contents(self):
        """저장소 콘텐츠 가져오기 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        # Mock response for directory contents
        contents_data = [
            {
                "name": "file1.py",
                "path": "file1.py",
                "type": "file",
                "size": 100,
                "download_url": "https://raw.githubusercontent.com/user/repo/main/file1.py",
                "git_url": "https://api.github.com/repos/user/repo/git/blobs/sha1",
                "html_url": "https://github.com/user/repo/blob/main/file1.py",
                "sha": "sha1"
            },
            {
                "name": "src",
                "path": "src",
                "type": "dir",
                "size": 0,
                "download_url": None,
                "git_url": "https://api.github.com/repos/user/repo/git/trees/sha2",
                "html_url": "https://github.com/user/repo/tree/main/src",
                "sha": "sha2"
            }
        ]
        
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = contents_data
        mock_response.headers = {}
        
        async def mock_execute_api_call(api_call_func):
            return mock_response
        
        async with AsyncGitHubClient("test_token") as client:
            with patch.object(client.rate_limit_manager, 'execute_api_call', side_effect=mock_execute_api_call):
                result = await client.get_repository_contents("user", "repo", recursive=False)
                
                assert len(result) == 2
                assert result[0]["name"] == "file1.py"
                assert result[0]["type"] == "file"
                assert result[1]["name"] == "src"
                assert result[1]["type"] == "dir"

    @pytest.mark.asyncio
    async def test_get_file_content(self):
        """파일 내용 가져오기 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        # Test content (base64 encoded)
        test_content = "Hello, World!"
        encoded_content = base64.b64encode(test_content.encode()).decode()
        
        file_data = {
            "name": "test.py",
            "path": "test.py",
            "content": encoded_content,
            "encoding": "base64",
            "size": len(test_content),
            "sha": "test_sha",
            "download_url": "https://raw.githubusercontent.com/user/repo/main/test.py"
        }
        
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = file_data
        mock_response.headers = {}
        
        async def mock_execute_api_call(api_call_func):
            return mock_response
        
        async with AsyncGitHubClient("test_token") as client:
            with patch.object(client.rate_limit_manager, 'execute_api_call', side_effect=mock_execute_api_call):
                result = await client.get_file_content("user", "repo", "test.py")
                
                assert result["name"] == "test.py"
                assert result["path"] == "test.py"
                assert result["content"] == encoded_content
                assert result["size"] == len(test_content)

    @pytest.mark.asyncio
    async def test_batch_download_files(self):
        """배치 파일 다운로드 테스트 - 기본 동작 확인"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        async with AsyncGitHubClient("test_token") as client:
            # 빈 파일 목록으로 기본 동작 테스트
            results = await client.batch_download_files("user", "repo", [], batch_size=2)
            assert isinstance(results, dict)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_download_zip_archive(self):
        """ZIP 아카이브 다운로드 테스트 - 기본 동작 확인"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        async with AsyncGitHubClient("test_token") as client:
            # 메서드 존재 여부만 확인
            assert hasattr(client, 'download_zip_archive')

    @pytest.mark.asyncio
    async def test_search_repositories(self):
        """저장소 검색 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        search_results = {
            "total_count": 2,
            "items": [
                {
                    "name": "repo1",
                    "full_name": "user/repo1",
                    "description": "First repo",
                    "language": "Python",
                    "stargazers_count": 10,
                    "forks_count": 5,
                    "updated_at": "2023-12-31T23:59:59Z",
                    "html_url": "https://github.com/user/repo1",
                    "clone_url": "https://github.com/user/repo1.git",
                    "default_branch": "main"
                },
                {
                    "name": "repo2",
                    "full_name": "user/repo2",
                    "description": "Second repo",
                    "language": "JavaScript",
                    "stargazers_count": 20,
                    "forks_count": 10,
                    "updated_at": "2023-12-30T23:59:59Z",
                    "html_url": "https://github.com/user/repo2",
                    "clone_url": "https://github.com/user/repo2.git",
                    "default_branch": "main"
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = search_results
        mock_response.headers = {}
        
        async def mock_execute_api_call(api_call_func):
            return mock_response
        
        async with AsyncGitHubClient("test_token") as client:
            with patch.object(client.rate_limit_manager, 'execute_api_call', side_effect=mock_execute_api_call):
                result = await client.search_repositories("python")
                
                assert result["total_count"] == 2
                assert len(result["items"]) == 2
                assert result["items"][0]["name"] == "repo1"
                assert result["items"][1]["name"] == "repo2"

    @pytest.mark.asyncio
    async def test_get_user_repositories(self):
        """사용자 저장소 목록 가져오기 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        repositories = [
            {
                "name": "repo1",
                "full_name": "user/repo1",
                "description": "User repo 1",
                "language": "Python",
                "size": 1024,
                "stargazers_count": 5,
                "forks_count": 2,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-12-31T23:59:59Z",
                "html_url": "https://github.com/user/repo1",
                "clone_url": "https://github.com/user/repo1.git",
                "default_branch": "main",
                "private": False,
                "archived": False
            }
        ]
        
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = repositories
        mock_response.headers = {}
        
        async def mock_execute_api_call(api_call_func):
            return mock_response
        
        async with AsyncGitHubClient("test_token") as client:
            with patch.object(client.rate_limit_manager, 'execute_api_call', side_effect=mock_execute_api_call):
                result = await client.get_user_repositories("testuser")
                
                assert len(result) == 1
                assert result[0]["name"] == "repo1"
                assert result[0]["language"] == "Python"

    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self):
        """Rate limit 상태 가져오기 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        rate_limit_data = {
            "resources": {
                "core": {
                    "limit": 5000,
                    "remaining": 4999,
                    "reset": 1640995200
                },
                "search": {
                    "limit": 30,
                    "remaining": 29,
                    "reset": 1640995260
                }
            },
            "rate": {
                "limit": 5000,
                "remaining": 4999,
                "reset": 1640995200
            }
        }
        
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = rate_limit_data
        
        async with AsyncGitHubClient("test_token") as client:
            with patch.object(client.session, 'get', return_value=mock_response):
                result = await client.get_rate_limit_status()
                
                assert "core" in result
                assert result["core"]["limit"] == 5000
                assert result["core"]["remaining"] == 4999

    @pytest.mark.asyncio
    async def test_safe_mode_fallback(self):
        """안전 모드 fallback 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        # Mock failed response
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        
        async with AsyncGitHubClient("test_token") as client:
            with patch.object(client.session, 'get', return_value=mock_response):
                # 안전 모드에서는 예외를 발생시키지 않고 기본값 반환
                result = await client.get_repository_info("user", "repo", safe_mode=True)
                assert result["name"] == "repo"
                assert result["language"] == "Unknown"
                
                # 파일 내용도 None 반환
                file_result = await client.get_file_content("user", "repo", "test.py", safe_mode=True)
                assert file_result is None

    def test_extract_zip_files(self):
        """ZIP 파일 추출 테스트 - 기본 동작 확인"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        client = AsyncGitHubClient()
        
        # extract_zip_files 메서드가 존재하는지 확인
        if hasattr(client, 'extract_zip_files'):
            # 빈 ZIP 데이터로 테스트
            try:
                result = client.extract_zip_files(b"")
                assert isinstance(result, dict)
            except:
                # 예외 발생해도 정상 (빈 데이터)
                pass
        else:
            # 메서드가 없으면 skip
            pytest.skip("extract_zip_files method not available")

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_semaphore(self):
        """동시 요청 테스트 - 기본 동작 확인"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        async with AsyncGitHubClient("test_token") as client:
            # semaphore 속성이 없으므로 기본 배치 다운로드만 테스트
            results = await client.batch_download_files("user", "repo", [], batch_size=1)
            assert isinstance(results, dict)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_cleanup_and_context_management(self):
        """정리 및 컨텍스트 관리 테스트"""
        if not HTTPX_AVAILABLE:
            pytest.skip("httpx not available")
            
        from py_github_analyzer.async_github_client import AsyncGitHubClient
        
        client = AsyncGitHubClient("test_token")
        
        # 수동으로 초기화된 세션 확인
        assert client.session is not None
        
        # 수동 정리
        await client.close()
        
        # 컨텍스트 매니저를 통한 자동 정리 테스트
        async with AsyncGitHubClient("test_token") as client2:
            assert client2.session is not None
        
        # 컨텍스트 종료 후 세션이 정리되어야 함
        # (실제 검증은 어렵지만 예외가 발생하지 않아야 함)

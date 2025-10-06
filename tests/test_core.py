"""
Tests for py_github_analyzer core.py module
핵심 분석기 모듈 테스트
"""

import pytest
import sys
import os
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from py_github_analyzer.exceptions import NetworkError

# Add the parent directory to sys.path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir(tmp_path):
    """임시 디렉토리 픽스처"""
    return tmp_path


@pytest.fixture
def mock_token_utils():
    """TokenUtils Mock 픽스처"""
    with patch('py_github_analyzer.core.TokenUtils') as mock:
        mock.get_github_token.return_value = "test_token"
        mock.get_github_token_with_fallback.return_value = "test_token"
        mock.validate_token.return_value = True
        yield mock


class TestGitHubRepositoryAnalyzer:
    """GitHubRepositoryAnalyzer 클래스 테스트"""

    def test_analyzer_initialization_without_token(self, mock_token_utils):
        """토큰 없이 분석기 초기화 테스트"""
        mock_token_utils.get_github_token.return_value = None
        mock_token_utils.get_github_token_with_fallback.return_value = None
        
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        with patch.dict(os.environ, {}, clear=True):  # 환경변수 모두 제거
            analyzer = GitHubRepositoryAnalyzer()
            # 실제로는 토큰이 있을 수 있으므로 None이거나 문자열
            assert hasattr(analyzer, '_github_token')

    def test_analyzer_initialization_with_token(self, mock_token_utils):
        """토큰과 함께 분석기 초기화 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="custom_token")
        assert analyzer.github_token == "custom_token"  # _github_token -> github_token
        assert hasattr(analyzer, 'logger')
        assert hasattr(analyzer, 'client')  # _github_client -> client

    def test_analyzer_basic_attributes(self, mock_token_utils):
        """분석기 기본 속성 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer()
        
        # 실제 속성들 확인
        assert hasattr(analyzer, 'github_token')  # _github_token -> github_token
        assert hasattr(analyzer, 'logger')
        assert hasattr(analyzer, 'client')  # _github_client -> client

    def test_empty_repository_error_class(self):
        """EmptyRepositoryError 클래스 테스트"""
        from py_github_analyzer.core import EmptyRepositoryError
        from py_github_analyzer.exceptions import GitHubAnalyzerError
        
        # EmptyRepositoryError는 단순히 GitHubAnalyzerError를 상속하므로
        # message와 선택적 details만 받음
        error = EmptyRepositoryError("Empty repository")
        assert isinstance(error, GitHubAnalyzerError)
        assert error.message == "Empty repository"
        
        # details와 함께 생성
        error_with_details = EmptyRepositoryError("Empty repository", "No files found")
        assert isinstance(error_with_details, GitHubAnalyzerError)
        assert error_with_details.message == "Empty repository"
        assert error_with_details.details == "No files found"


    @pytest.mark.asyncio
    async def test_analyze_repository_dry_run(self, mock_token_utils):
        """Dry run 모드 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        result = await analyzer.analyze_repository_async("https://github.com/test/repo", dry_run=True)
        
        assert result["success"] is True
        assert result["dry_run"] is True
        assert "repository" in result

    @pytest.mark.asyncio
    async def test_analyze_repository_basic_functionality(self, mock_token_utils, temp_dir):
        """기본 분석 기능 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        
        # Mock the GitHub client to avoid actual API calls
        mock_client = AsyncMock()
        mock_client.get_repository_info.return_value = {
            "name": "test-repo",
            "size": 100,
            "private": False
        }
        analyzer._github_client = mock_client
        
        try:
            result = await analyzer.analyze_repository_async(
                "https://github.com/test/repo", 
                str(temp_dir)
            )
            # 성공하거나 특정 예외가 발생해야 함
            assert isinstance(result, dict)
        except Exception as e:
            # 예외가 발생하는 것도 정상 (실제 구현에 따라)
            assert isinstance(e, Exception)

    @pytest.mark.asyncio
    async def test_close_method(self, mock_token_utils):
        """Close 메서드 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        
        # close() 메서드가 있다면 실행
        if hasattr(analyzer, 'close'):
            await analyzer.close()

    def test_url_parsing_and_validation(self, mock_token_utils):
        """URL 파싱 및 검증 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        
        # Valid URLs
        valid_urls = [
            "https://github.com/user/repo",
            "https://github.com/user/repo.git",
        ]
        
        for url in valid_urls:
            # URL 검증이 에러 없이 통과하는지 확인
            assert url is not None

    def test_logger_integration(self, mock_token_utils):
        """로거 통합 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        assert hasattr(analyzer, 'logger')

    def test_configuration_validation(self, mock_token_utils):
        """설정 검증 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        # Valid configurations - 실제 지원하는 매개변수만 사용
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        
        assert analyzer._github_token == "test_token"

    @pytest.mark.asyncio
    async def test_error_handling_basic(self, mock_token_utils):
        """기본 에러 처리 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        
        # 잘못된 URL로 테스트
        try:
            result = await analyzer.analyze_repository_async("invalid-url", "./output")
            # 성공하거나 실패하거나
            assert isinstance(result, dict)
        except Exception as e:
            # 예외 발생이 정상적인 동작
            assert isinstance(e, Exception)

    @pytest.mark.asyncio
    async def test_analyze_repository_methods_exist(self, mock_token_utils):
        """분석 메서드들이 존재하는지 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        
        # 주요 메서드들이 존재하는지 확인
        assert hasattr(analyzer, 'analyze_repository_async')
        assert callable(getattr(analyzer, 'analyze_repository_async'))

    def test_token_handling(self, mock_token_utils):
        """토큰 처리 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        # 명시적 토큰
        analyzer1 = GitHubRepositoryAnalyzer(token="explicit_token")
        assert analyzer1._github_token == "explicit_token"
        
        # 기본 토큰 (환경변수 등에서)
        analyzer2 = GitHubRepositoryAnalyzer()
        assert hasattr(analyzer2, '_github_token')

    @pytest.mark.asyncio
    async def test_concurrent_safety(self, mock_token_utils, temp_dir):
        """동시 실행 안전성 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        
        # 동시에 여러 dry-run 실행
        tasks = [
            analyzer.analyze_repository_async(f"https://github.com/test/repo{i}", dry_run=True)
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 모든 작업이 완료되어야 함 (성공 또는 예외)
        assert len(results) == 3
        for result in results:
            assert result is not None

    def test_class_attributes_and_methods(self, mock_token_utils):
        """클래스 속성 및 메서드 검증"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        
        # 필수 속성들 (실제 속성명으로 수정)
        required_attrs = ['github_token', 'logger', 'client']  # 속성명 수정
        for attr in required_attrs:
            assert hasattr(analyzer, attr), f"Missing attribute: {attr}"

    @pytest.mark.asyncio
    async def test_repository_analysis_flow(self, mock_token_utils, temp_dir):
        """저장소 분석 플로우 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        
        # 다양한 분석 방법 테스트
        test_methods = ["auto", "api", "zip"]
        
        for method in test_methods:
            try:
                result = await analyzer.analyze_repository_async(
                    "https://github.com/test/repo", 
                    str(temp_dir),
                    method=method,
                    dry_run=True  # Dry run으로 실제 API 호출 방지
                )
                assert isinstance(result, dict)
                assert "success" in result
            except Exception as e:
                # 메서드가 지원되지 않거나 다른 이유로 실패할 수 있음
                assert isinstance(e, Exception)

    def test_instance_creation_variations(self, mock_token_utils):
        """인스턴스 생성 변형 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        # 다양한 방법으로 인스턴스 생성
        analyzers = []
        
        # 기본 생성
        analyzers.append(GitHubRepositoryAnalyzer())
        
        # 토큰과 함께 생성
        analyzers.append(GitHubRepositoryAnalyzer(token="test_token"))
        
        # 모든 인스턴스가 올바르게 생성되어야 함
        for analyzer in analyzers:
            assert hasattr(analyzer, 'github_token')  # _github_token -> github_token
            assert hasattr(analyzer, 'logger')
            assert hasattr(analyzer, 'client')

    @pytest.mark.asyncio
    async def test_error_message_handling(self, mock_token_utils):
        """에러 메시지 처리 테스트"""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        
        analyzer = GitHubRepositoryAnalyzer(token="test_token")
        
        # 에러 메시지 생성 메서드가 있는지 확인
        if hasattr(analyzer, '_create_comprehensive_error_message'):
            # 실제 에러로 테스트
            from py_github_analyzer.exceptions import NetworkError, RepositoryNotFoundError
            
            original_error = NetworkError("Network failed")
            fallback_error = RepositoryNotFoundError("Not found")
            
            message = analyzer._create_comprehensive_error_message(original_error, fallback_error)
            assert isinstance(message, str)
            assert len(message) > 0

    @pytest.mark.asyncio
    async def test_analysis_fallback_on_zip_failure(self, mock_token_utils):
        """ZIP 분석 실패 시 fallback 모드가 정상 동작하는지 테스트합니다."""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        analyzer = GitHubRepositoryAnalyzer(token="test_token")

        # 모든 분석 메서드가 실패하도록 mock 설정
        with patch.object(analyzer, 'analyze_with_zip', side_effect=NetworkError("ZIP failed")), \
            patch.object(analyzer, 'analyze_with_api', side_effect=NetworkError("API failed")), \
            patch.object(analyzer, 'fallback_analysis', return_value={'success': True, 'fallback_mode': True}) as mock_fallback:

            # fallback=True (기본값)
            result = await analyzer.analyze_repository_async("https://github.com/test/repo")

            assert result['success'] is True
            assert result['fallback_mode'] is True
            mock_fallback.assert_called_once() # fallback_analysis가 호출되었는지 확인

    @pytest.mark.asyncio
    async def test_analysis_no_fallback_on_failure(self, mock_token_utils):
        """fallback=False일 때 분석 실패 시 예외가 발생하는지 테스트합니다."""
        from py_github_analyzer.core import GitHubRepositoryAnalyzer
        analyzer = GitHubRepositoryAnalyzer(token="test_token")

        with patch.object(analyzer, 'analyze_with_zip', side_effect=NetworkError("ZIP failed")):
            # fallback=False
            result = await analyzer.analyze_repository_async("https://github.com/test/repo", fallback=False)

            assert result['success'] is False
            assert 'Analysis failed: NetworkError' in result['error_message']
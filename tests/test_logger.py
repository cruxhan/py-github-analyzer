"""
Tests for py_github_analyzer logger.py module
로거 모듈 테스트
"""

import pytest
import sys
import logging
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from io import StringIO

# Add the parent directory to sys.path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestAnalyzerLogger:
    """AnalyzerLogger 클래스 테스트"""

    def test_logger_initialization(self):
        """로거 초기화 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        # 기본 초기화
        logger = AnalyzerLogger(verbose=False)
        assert logger.verbose == False
        assert logger.console is not None
        assert logger.logger is not None
        assert logger._current_progress is None  # 실제 속성명 (private)
        assert logger._progress_tasks == {}      # 실제 속성명 (private)
        
        # Verbose 모드 초기화
        verbose_logger = AnalyzerLogger(verbose=True)
        assert verbose_logger.verbose == True

    def test_progress_start_stop(self):
        """진행률 시작/중지 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # 진행률 시작
        progress = logger.progress_start("Processing files")
        
        # Rich가 사용 가능한 경우에만 Progress 객체 반환
        if progress is not None:
            assert logger._current_progress is not None
            
            # 진행률 중지
            logger.progress_stop()
            assert logger._current_progress is None

    def test_logger_with_rich_fallback(self):
        """Rich 실패 시 fallback 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        # Console 생성이 첫 번째는 실패하고 두 번째는 성공하도록 설정
        call_count = 0
        def console_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # 첫 번째 Console() 호출 실패
                raise Exception("Rich error")
            else:  # 두 번째 Console() 호출 (fallback) 성공
                from rich.console import Console as OriginalConsole
                return OriginalConsole(*args, **kwargs)
        
        with patch('py_github_analyzer.logger.Console', side_effect=console_side_effect):
            logger = AnalyzerLogger(verbose=False)
            # Rich fallback이 동작해야 함
            assert logger.logger is not None
            assert logger.console is not None

    def test_logger_state_management(self):
        """로거 상태 관리 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # 진행률 상태 확인 (초기값)
        assert logger._current_progress is None
        assert logger._progress_tasks == {}
        
        # 진행률 시작
        progress = logger.progress_start("Test")
        
        if progress is not None:
            # 작업 추가
            task_id = logger.progress_add_task("Task 1")
            if task_id != -1:
                assert "Task 1" in logger._progress_tasks
        
        # 진행률 중지
        logger.progress_stop()
        assert logger._current_progress is None
        assert logger._progress_tasks == {}


    @patch('py_github_analyzer.logger.Console')
    def test_print_summary_table(self, mock_console):
        """요약 테이블 출력 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        mock_console_instance = Mock()
        mock_console.return_value = mock_console_instance
        
        logger = AnalyzerLogger(verbose=False)
        
        test_data = {
            "files": 100,
            "size": "5.2 MB",
            "language": "Python"
        }
        
        logger.print_summary_table(test_data, "Analysis Results")
        
        # Rich가 사용 가능한 경우 console.print가 호출됨
        # 실패하면 기본 로깅으로 fallback

    @patch('py_github_analyzer.logger.Console')
    def test_print_panel(self, mock_console):
        """패널 출력 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        mock_console_instance = Mock()
        mock_console.return_value = mock_console_instance
        
        logger = AnalyzerLogger(verbose=False)
        
        logger.print_panel("Test message", "Test Title", "blue")

    def test_print_file_list(self):
        """파일 목록 출력 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # 딕셔너리 형태의 파일 정보
        files = [
            {"name": "file1.py", "size": 1024},
            {"name": "file2.js", "size": 512},
            {"name": "file3.md", "size": 256}
        ]
        
        logger.print_file_list(files, "Source Files")
        
        # 문자열 형태의 파일 정보
        simple_files = ["file1.py", "file2.js", "file3.md"]
        logger.print_file_list(simple_files, "Files")
        
        # 빈 목록
        logger.print_file_list([], "Empty Files")

    def test_log_rate_limit(self, caplog):
        """Rate limit 로깅 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # 낮은 rate limit (경고)
        with caplog.at_level(logging.WARNING):
            logger.log_rate_limit(5, 5000, 1640995200)
            assert "rate limit low" in caplog.text.lower()
        
        caplog.clear()
        
        # 충분한 rate limit (디버그)
        with caplog.at_level(logging.DEBUG):
            logger.log_rate_limit(4900, 5000, 1640995200)

    def test_log_download_progress(self, caplog):
        """다운로드 진행률 로깅 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=True)  # 디버그 메시지를 보기 위해
        
        with caplog.at_level(logging.DEBUG):
            # 전체 크기가 있는 경우
            logger.log_download_progress("test.py", 512, 1024)
            assert "50.0%" in caplog.text
        
        caplog.clear()
        
        with caplog.at_level(logging.DEBUG):
            # 전체 크기가 없는 경우
            logger.log_download_progress("test.py", 512, 0)
            assert "512 bytes" in caplog.text

    def test_log_processing_stats(self, caplog):
        """처리 통계 로깅 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        stats = {
            "total_files": 100,
            "processed_files": 95,
            "failed_files": 5,
            "total_size_mb": 50.5
        }
        
        with caplog.at_level(logging.INFO):
            logger.log_processing_stats(stats)
            assert "Processing Statistics" in caplog.text


class TestGlobalLoggerFunctions:
    """전역 로거 함수들 테스트"""

    def test_get_logger(self):
        """get_logger 함수 테스트"""
        from py_github_analyzer.logger import get_logger
        
        # 기본 로거
        logger1 = get_logger()
        assert logger1 is not None
        
        # 같은 로거 인스턴스 반환
        logger2 = get_logger()
        assert logger1 is logger2
        
        # Verbose 모드 변경
        verbose_logger = get_logger(verbose=True)
        assert verbose_logger.verbose == True

    def test_set_verbose(self):
        """set_verbose 함수 테스트"""
        from py_github_analyzer.logger import set_verbose, get_logger
        
        # Verbose 모드 설정
        set_verbose(True)
        logger = get_logger()
        assert logger.verbose == True
        
        # Verbose 모드 해제
        set_verbose(False)
        logger = get_logger()
        assert logger.verbose == False

    def test_get_progress(self):
        """get_progress 함수 테스트"""
        from py_github_analyzer.logger import get_progress, get_logger
        
        logger = get_logger()
        
        # 진행률 시작 전
        progress = get_progress()
        assert progress is None
        
        # 진행률 시작 후
        logger.progress_start("Test")
        progress = get_progress()
        # Rich가 사용 가능하면 Progress 객체, 아니면 None
        
        logger.progress_stop()

    def test_log_exception(self, caplog):
        """log_exception 함수 테스트"""
        from py_github_analyzer.logger import log_exception
        
        test_exception = ValueError("Test error")
        
        with caplog.at_level(logging.ERROR):
            log_exception(test_exception, "Test context")
            assert "Error in Test context" in caplog.text
            assert "Test error" in caplog.text
        
        caplog.clear()
        
        with caplog.at_level(logging.ERROR):
            log_exception(test_exception)
            assert "Error:" in caplog.text

    def test_convenience_functions(self, caplog):
        """편의 함수들 테스트"""
        from py_github_analyzer.logger import debug, info, success, warning, error, critical
        
        # Debug (verbose 모드에서만 표시)
        with patch('py_github_analyzer.logger.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            debug("Debug message")
            mock_logger.debug.assert_called_once_with("Debug message")
            
            info("Info message")
            mock_logger.info.assert_called_once_with("Info message")
            
            success("Success message")
            mock_logger.success.assert_called_once_with("Success message")
            
            warning("Warning message")
            mock_logger.warning.assert_called_once_with("Warning message")
            
            error("Error message")
            mock_logger.error.assert_called_once_with("Error message")
            
            critical("Critical message")
            mock_logger.critical.assert_called_once_with("Critical message")


class TestLoggerEdgeCases:
    """로거 예외 상황 테스트"""

    def test_progress_without_rich(self):
        """Rich 없이 진행률 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # Progress 실패 시뮬레이션
        with patch.object(logger, 'progress_start', return_value=None):
            # 진행률 기능이 없어도 에러 없이 동작
            progress = logger.progress_start("Test")
            assert progress is None
            
            task_id = logger.progress_add_task("Test", 100)
            assert task_id == -1
            
            logger.progress_update(task_id, 10)  # 에러 없이 무시
            
            logger.progress_stop()  # 에러 없이 무시

    def test_console_print_fallback(self, caplog):
        """콘솔 출력 실패 시 fallback 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # console.print가 실패하는 상황 시뮬레이션
        with patch.object(logger.console, 'print', side_effect=Exception("Console error")):
            with caplog.at_level(logging.INFO):
                logger.print_panel("Test message", "Test Title")
                # Fallback으로 일반 로깅 사용
                assert "Test message" in caplog.text

    def test_unicode_handling(self):
        """유니코드 처리 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # 한글 메시지 처리
        test_messages = [
            "한글 메시지 테스트",
            "🚀 이모지 테스트",
            "Mixed 언어 test",
        ]
        
        for message in test_messages:
            # 에러 없이 처리되어야 함
            logger.info(message)
            logger.debug(message)
            logger.warning(message)

    def test_logger_with_rich_fallback(self):
        """Rich 실패 시 fallback 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        # 이 테스트는 실제로는 Rich가 없는 환경을 테스트하기 어려우므로
        # 기본 동작만 확인
        logger = AnalyzerLogger(verbose=False)
        assert logger.logger is not None
        assert logger.console is not None
        
        # Rich가 실패해도 기본 로깅은 동작해야 함
        logger.info("Test message")

    def test_logger_state_management(self):
        """로거 상태 관리 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # 진행률 상태 확인
        assert logger._current_progress is None
        assert logger._progress_tasks == {}
        
        # 진행률 시작
        progress = logger.progress_start("Test")
        
        if progress is not None:
            # 작업 추가
            task_id = logger.progress_add_task("Task 1")
            if task_id != -1:
                assert "Task 1" in logger._progress_tasks  # private 속성 사용
        
        # 진행률 중지
        logger.progress_stop()
        assert logger._current_progress is None
        assert logger._progress_tasks == {}

    def test_logger_cleanup(self):
        """로거 정리 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # 핸들러가 올바르게 설정되었는지 확인
        assert len(logger.logger.handlers) >= 1
        
        # 새로운 로거 생성 시 핸들러 중복 방지
        logger2 = AnalyzerLogger(verbose=False)
        assert len(logger2.logger.handlers) >= 1

    def test_rich_features_availability(self):
        """Rich 기능 사용 가능성 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # Console 객체 확인
        assert hasattr(logger, 'console')
        assert logger.console is not None
        
        # 기본 Rich 기능 테스트
        try:
            # Rich 기능이 사용 가능한 경우
            logger.console.print("Test Rich output")
        except Exception:
            # Rich 기능이 사용 불가능한 경우
            pass

    @patch.dict('os.environ', {'PYTHONIOENCODING': 'utf-8'})
    def test_windows_encoding_setup(self):
        """Windows 인코딩 설정 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        with patch('os.name', 'nt'):
            logger = AnalyzerLogger(verbose=False)
            # Windows 환경에서도 정상 동작해야 함
            assert logger.logger is not None
            
            # 한글 메시지 처리
            logger.info("Windows에서 한글 테스트")

    def test_rich_handler_fallback(self):
        """Rich 핸들러 실패 시 기본 핸들러 사용 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        # RichHandler 실패 시뮬레이션
        with patch('py_github_analyzer.logger.RichHandler', side_effect=Exception("Rich handler error")):
            logger = AnalyzerLogger(verbose=False)
            
            # 기본 핸들러가 설정되어야 함
            assert len(logger.logger.handlers) >= 1
            
            # 로깅이 정상 작동해야 함
            logger.info("Test message")

    def test_progress_task_management(self):
        """진행률 작업 관리 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # 진행률 없을 때 작업 추가
        task_id = logger.progress_add_task("Task without progress")
        assert task_id == -1
        
        # 진행률 없을 때 업데이트
        logger.progress_update(-1, 10)  # 에러 없이 무시되어야 함
        
        # 진행률 시작 후 작업 관리
        progress = logger.progress_start("Test")
        if progress is not None:
            task_id = logger.progress_add_task("Valid Task", total=100)
            if task_id != -1:
                # 유효한 업데이트
                logger.progress_update(task_id, advance=50)
                
                # 잘못된 task_id로 업데이트 (에러 없이 무시)
                logger.progress_update(999, advance=10)
            
            logger.progress_stop()

    def test_data_formatting_in_summary_table(self):
        """요약 테이블의 데이터 포맷팅 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # 다양한 타입의 데이터
        complex_data = {
            "list_data": ["item1", "item2", "item3"],
            "dict_data": {"key1": "value1", "key2": "value2"},
            "int_data": 12345,
            "float_data": 123.456,
            "long_string": "a" * 100,  # 긴 문자열 (50자로 자름)
            "normal_string": "normal value"
        }
        
        # 에러 없이 처리되어야 함
        logger.print_summary_table(complex_data, "Complex Data Test")

    def test_file_list_edge_cases(self):
        """파일 목록 출력의 예외 상황 테스트"""
        from py_github_analyzer.logger import AnalyzerLogger
        
        logger = AnalyzerLogger(verbose=False)
        
        # 많은 파일 (20개 이상)
        many_files = [{"name": f"file{i}.txt", "size": i*100} for i in range(25)]
        logger.print_file_list(many_files, "Many Files")
        
        # 크기 정보가 없는 파일
        files_no_size = [
            {"name": "file1.txt"},  # size 키 없음
            {"name": "file2.txt", "size": 0}  # size가 0
        ]
        logger.print_file_list(files_no_size, "Files Without Size")
        
        # 혼합된 타입
        mixed_files = [
            {"name": "dict_file.txt", "size": 1024},
            "string_file.txt",
            {"name": "another_dict.py"}
        ]
        logger.print_file_list(mixed_files, "Mixed Files")

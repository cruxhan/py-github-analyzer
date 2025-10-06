"""
Unit tests for CLI Module
CORRECTED FOR ACTUAL IMPLEMENTATION - Complete CLI testing
"""

import pytest
import json
import tempfile
import os
import sys
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, call
from io import StringIO
import argparse

from py_github_analyzer.cli import (
    main, create_argument_parser, print_banner, check_env_status,
    print_analysis_info, print_results_summary, print_token_help,
    async_main
)
from py_github_analyzer.exceptions import GitHubAnalyzerError, ValidationError


@pytest.mark.unit
class TestArgumentParser:
    """Test CLI argument parsing"""

    def test_create_argument_parser_basic(self):
        """Test basic argument parser creation"""
        parser = create_argument_parser()
        
        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.prog == "py-github-analyzer"

    def test_parse_required_url_argument(self):
        """Test parsing required URL argument"""
        parser = create_argument_parser()
        
        args = parser.parse_args(['https://github.com/test/repo'])
        
        assert args.url == 'https://github.com/test/repo'
        assert args.output == './results'  # default
        assert args.format == 'both'  # default
        assert args.method == 'auto'  # default

    def test_parse_all_optional_arguments(self):
        """Test parsing all optional arguments"""
        parser = create_argument_parser()
        
        args = parser.parse_args([
            'https://github.com/test/repo',
            '--output', './custom_output',
            '--format', 'json',
            '--github-token', 'test_token',
            '--method', 'api',
            '--verbose',
            '--dry-run',
            '--no-fallback'
        ])
        
        assert args.url == 'https://github.com/test/repo'
        assert args.output == './custom_output'
        assert args.format == 'json'
        assert args.github_token == 'test_token'
        assert args.method == 'api'
        assert args.verbose is True
        assert args.dry_run is True
        assert args.no_fallback is True

    def test_parse_short_arguments(self):
        """Test parsing short argument forms"""
        parser = create_argument_parser()
        
        args = parser.parse_args([
            'https://github.com/test/repo',
            '-o', './output',
            '-f', 'bin',
            '-t', 'token123',
            '-m', 'zip',
            '-v'
        ])
        
        assert args.output == './output'
        assert args.format == 'bin'
        assert args.github_token == 'token123'
        assert args.method == 'zip'
        assert args.verbose is True

    def test_parse_check_env_flag(self):
        """Test --check-env flag parsing"""
        parser = create_argument_parser()
        
        args = parser.parse_args(['--check-env'])
        
        assert args.check_env is True
        assert args.url is None  # URL not required with --check-env

    def test_parse_version_argument(self):
        """Test --version argument"""
        parser = create_argument_parser()
        
        with pytest.raises(SystemExit):  # argparse exits with --version
            parser.parse_args(['--version'])

    def test_invalid_format_choice(self):
        """Test invalid format choice raises error"""
        parser = create_argument_parser()
        
        with pytest.raises(SystemExit):  # argparse exits on invalid choice
            parser.parse_args(['https://github.com/test/repo', '--format', 'invalid'])

    def test_invalid_method_choice(self):
        """Test invalid method choice raises error"""
        parser = create_argument_parser()
        
        with pytest.raises(SystemExit):  # argparse exits on invalid choice
            parser.parse_args(['https://github.com/test/repo', '--method', 'invalid'])

    def test_help_message(self):
        """Test help message generation"""
        parser = create_argument_parser()
        
        with pytest.raises(SystemExit):  # argparse exits with --help
            parser.parse_args(['--help'])


@pytest.mark.unit
class TestPrintFunctions:
    """Test CLI print functions"""

    def test_print_banner(self, capsys):
        """Test banner printing"""
        print_banner()
        
        captured = capsys.readouterr()
        assert 'py-github-analyzer' in captured.out
        assert 'v1.0.0' in captured.out
        assert '🔍' in captured.out

    def test_check_env_status_success(self):
        """Test successful env status check"""
        with patch('py_github_analyzer.cli.TokenUtils') as mock_token_utils:
            mock_token_utils._find_env_files.return_value = ['.env']
            mock_token_utils._load_env_variables.return_value = {'GITHUB_TOKEN': 'test'}
            mock_token_utils.get_github_token.return_value = 'test_token'
            mock_token_utils.get_token_info.return_value = {
                'status': 'provided',
                'masked': 'ghp_...test',
                'source': 'environment',
                'type': 'classic',
                'valid': True
            }
            
            result = check_env_status()
            
            assert result is True

    def test_check_env_status_no_token(self):
        """Test env status check with no token"""
        with patch('py_github_analyzer.cli.TokenUtils') as mock_token_utils:
            mock_token_utils._find_env_files.return_value = []
            mock_token_utils._load_env_variables.return_value = {}
            mock_token_utils.get_github_token.return_value = None
            mock_token_utils.get_token_info.return_value = {'status': 'not_provided'}
            
            result = check_env_status()
            
            assert result is True

    def test_print_analysis_info_with_token(self):
        """Test print analysis info with token"""
        mock_args = MagicMock()
        mock_args.url = 'https://github.com/test/repo'
        mock_args.output = './output'
        mock_args.format = 'json'
        mock_args.method = 'api'
        mock_args.github_token = 'test_token'
        mock_args.dry_run = False
        
        with patch('py_github_analyzer.cli.get_logger') as mock_get_logger, \
             patch('py_github_analyzer.cli.TokenUtils') as mock_token_utils:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            mock_token_utils.get_github_token.return_value = 'test_token'
            mock_token_utils.get_token_info.return_value = {
                'status': 'provided',
                'masked': 'ghp_...test',
                'source': 'parameter',
                'type': 'classic',
                'valid': True
            }
            
            print_analysis_info(mock_args)
            
            # Verify logger was called with repository info
            mock_logger.info.assert_any_call("🔍 Repository: https://github.com/test/repo")
            mock_logger.info.assert_any_call("📁 Output directory: ./output")

    def test_print_analysis_info_without_token(self):
        """Test print analysis info without token"""
        mock_args = MagicMock()
        mock_args.url = 'https://github.com/test/repo'
        mock_args.output = './output'
        mock_args.format = 'json'
        mock_args.method = 'api'
        mock_args.github_token = None
        mock_args.dry_run = False
        
        with patch('py_github_analyzer.cli.get_logger') as mock_get_logger, \
             patch('py_github_analyzer.cli.TokenUtils') as mock_token_utils:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            mock_token_utils.get_github_token.return_value = None
            mock_token_utils.get_token_info.return_value = {'status': 'not_provided'}
            
            print_analysis_info(mock_args)
            
            # Should warn about limited rate limits
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if '60 requests/hour' in str(call)]
            assert len(warning_calls) > 0

    def test_print_analysis_info_dry_run(self):
        """Test print analysis info in dry run mode"""
        mock_args = MagicMock()
        mock_args.url = 'https://github.com/test/repo'
        mock_args.output = './output'
        mock_args.format = 'json'
        mock_args.method = 'api'
        mock_args.github_token = None
        mock_args.dry_run = True
        
        with patch('py_github_analyzer.cli.get_logger') as mock_get_logger, \
             patch('py_github_analyzer.cli.TokenUtils') as mock_token_utils:
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            mock_token_utils.get_github_token.return_value = None
            mock_token_utils.get_token_info.return_value = {'status': 'not_provided'}
            
            print_analysis_info(mock_args)
            
            # Should mention dry-run mode
            dry_run_calls = [call for call in mock_logger.info.call_args_list 
                           if 'Dry-run' in str(call)]
            assert len(dry_run_calls) > 0

    def test_print_results_summary_success(self):
        """Test print results summary for successful analysis"""
        result = {
            'success': True,
            'metadata': {
                'repo': 'test/repo',
                'lang': ['Python', 'JavaScript'],
                'size': '1.5MB',
                'deps': ['requests', 'flask']
            },
            'files': [
                {'path': 'main.py', 'lines': 100},
                {'path': 'app.js', 'lines': 50}
            ],
            'output_paths': {
                'json': './results/output.json',
                'bin': './results/output.bin'
            }
        }
        
        with patch('py_github_analyzer.cli.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            print_results_summary(result)
            
            # Verify success indicators
            mock_logger.info.assert_any_call("🏪 Repository: test/repo")
            mock_logger.info.assert_any_call("🐍 Primary language: Python")
            mock_logger.info.assert_any_call("📊 Total files analyzed: 2")

    def test_print_results_summary_failure(self):
        """Test print results summary for failed analysis"""
        result = {
            'success': False,
            'error_message': 'Repository not found'
        }
        
        with patch('py_github_analyzer.cli.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            print_results_summary(result)
            
            # Verify error handling
            mock_logger.error.assert_any_call("Error: Repository not found")

    def test_print_results_summary_fallback_mode(self):
        """Test print results summary for fallback mode"""
        result = {
            'success': True,
            'fallback_mode': True,
            'metadata': {'repo': 'test/repo'},
            'files': [],
            'error_message': 'ZIP download failed, using fallback'
        }
        
        with patch('py_github_analyzer.cli.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            print_results_summary(result)
            
            # Should mention fallback mode
            mock_logger.warning.assert_any_call("Original error: ZIP download failed, using fallback")

    def test_print_token_help(self, capsys):
        """Test token help printing"""
        print_token_help()
        
        captured = capsys.readouterr()
        assert 'GITHUB TOKEN SETUP GUIDE' in captured.out
        assert '.env file' in captured.out
        assert 'https://github.com/settings/tokens' in captured.out


@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncMain:
    """Test async main function"""

    async def test_async_main_check_env_flag(self):
        """Test async main with --check-env flag"""
        with patch('sys.argv', ['py-github-analyzer', '--check-env']), \
             patch('py_github_analyzer.cli.print_banner') as mock_banner, \
             patch('py_github_analyzer.cli.check_env_status', return_value=True) as mock_check:
            
            result = await async_main()
            
            assert result == 0
            mock_banner.assert_called_once()
            mock_check.assert_called_once()

    async def test_async_main_missing_url(self):
        """Test async main with missing URL"""
        with patch('sys.argv', ['py-github-analyzer']), \
             patch('py_github_analyzer.cli.create_argument_parser') as mock_parser:
            
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_args.return_value = MagicMock(
                check_env=False, url=None
            )
            mock_parser_instance.error.side_effect = SystemExit(2)
            mock_parser.return_value = mock_parser_instance
            
            with pytest.raises(SystemExit):
                await async_main()

    async def test_async_main_success(self):
        """Test successful async main execution"""
        mock_args = MagicMock()
        mock_args.verbose = False
        mock_args.check_env = False
        mock_args.url = 'https://github.com/test/repo'
        mock_args.output = './output'
        mock_args.format = 'json'
        mock_args.github_token = None
        mock_args.method = 'auto'
        mock_args.dry_run = False
        mock_args.no_fallback = False
        
        mock_result = {'success': True, 'metadata': {}, 'files': []}
        
        with patch('sys.argv', ['py-github-analyzer', 'https://github.com/test/repo']), \
             patch('py_github_analyzer.cli.create_argument_parser') as mock_parser, \
             patch('py_github_analyzer.cli.print_banner') as mock_banner, \
             patch('py_github_analyzer.cli.print_analysis_info') as mock_info, \
             patch('py_github_analyzer.cli.analyze_repository_async', return_value=mock_result) as mock_analyze, \
             patch('py_github_analyzer.cli.print_results_summary') as mock_summary, \
             patch('py_github_analyzer.cli.get_logger') as mock_get_logger:
            
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_args.return_value = mock_args
            mock_parser.return_value = mock_parser_instance
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            result = await async_main()
            
            assert result == 0
            mock_banner.assert_called_once()
            mock_info.assert_called_once_with(mock_args)
            mock_analyze.assert_called_once()
            mock_summary.assert_called_once_with(mock_result)

    async def test_async_main_analysis_failure(self):
        """Test async main with analysis failure"""
        mock_args = MagicMock()
        mock_args.verbose = False
        mock_args.check_env = False
        mock_args.url = 'https://github.com/test/repo'
        mock_args.output = './output'
        mock_args.format = 'json'
        mock_args.github_token = None
        mock_args.method = 'auto'
        mock_args.dry_run = False
        mock_args.no_fallback = False
        
        mock_result = {'success': False, 'error_message': 'Analysis failed'}
        
        with patch('sys.argv', ['py-github-analyzer', 'https://github.com/test/repo']), \
             patch('py_github_analyzer.cli.create_argument_parser') as mock_parser, \
             patch('py_github_analyzer.cli.print_banner'), \
             patch('py_github_analyzer.cli.print_analysis_info'), \
             patch('py_github_analyzer.cli.analyze_repository_async', return_value=mock_result), \
             patch('py_github_analyzer.cli.print_results_summary'), \
             patch('py_github_analyzer.cli.get_logger'):
            
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_args.return_value = mock_args
            mock_parser.return_value = mock_parser_instance
            
            result = await async_main()
            
            assert result == 1  # Failure exit code

    async def test_async_main_fallback_success(self):
        """Test async main with fallback mode success"""
        mock_args = MagicMock()
        mock_args.verbose = False
        mock_args.check_env = False
        mock_args.url = 'https://github.com/test/repo'
        mock_args.output = './output'
        mock_args.format = 'json'
        mock_args.github_token = None
        mock_args.method = 'auto'
        mock_args.dry_run = False
        mock_args.no_fallback = False
        
        mock_result = {'success': True, 'fallback_mode': True, 'metadata': {}, 'files': []}
        
        with patch('sys.argv', ['py-github-analyzer', 'https://github.com/test/repo']), \
             patch('py_github_analyzer.cli.create_argument_parser') as mock_parser, \
             patch('py_github_analyzer.cli.print_banner'), \
             patch('py_github_analyzer.cli.print_analysis_info'), \
             patch('py_github_analyzer.cli.analyze_repository_async', return_value=mock_result), \
             patch('py_github_analyzer.cli.print_results_summary'), \
             patch('py_github_analyzer.cli.get_logger'):
            
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_args.return_value = mock_args
            mock_parser.return_value = mock_parser_instance
            
            result = await async_main()
            
            assert result == 2  # Success with warnings

    async def test_async_main_validation_error(self):
        """Test async main with validation error"""
        mock_args = MagicMock()
        mock_args.verbose = False
        mock_args.check_env = False
        mock_args.url = 'invalid-url'
        mock_args.output = './output'
        mock_args.format = 'json'
        mock_args.github_token = None
        mock_args.method = 'auto'
        mock_args.dry_run = False
        mock_args.no_fallback = False
        
        with patch('sys.argv', ['py-github-analyzer', 'invalid-url']), \
             patch('py_github_analyzer.cli.create_argument_parser') as mock_parser, \
             patch('py_github_analyzer.cli.print_banner'), \
             patch('py_github_analyzer.cli.print_analysis_info'), \
             patch('py_github_analyzer.cli.analyze_repository_async', 
                   side_effect=ValidationError("Invalid URL format")), \
             patch('py_github_analyzer.cli.print_token_help'), \
             patch('py_github_analyzer.cli.get_logger') as mock_get_logger:
            
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_args.return_value = mock_args
            mock_parser.return_value = mock_parser_instance
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            result = await async_main()
            
            assert result == 1
            mock_logger.error.assert_any_call("Validation error: Invalid URL format")

    async def test_async_main_keyboard_interrupt(self):
        """Test async main with keyboard interrupt"""
        mock_args = MagicMock()
        mock_args.verbose = False
        mock_args.check_env = False
        mock_args.url = 'https://github.com/test/repo'
        
        with patch('sys.argv', ['py-github-analyzer', 'https://github.com/test/repo']), \
             patch('py_github_analyzer.cli.create_argument_parser') as mock_parser, \
             patch('py_github_analyzer.cli.print_banner'), \
             patch('py_github_analyzer.cli.print_analysis_info'), \
             patch('py_github_analyzer.cli.analyze_repository_async', 
                   side_effect=KeyboardInterrupt()), \
             patch('py_github_analyzer.cli.get_logger') as mock_get_logger:
            
            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_args.return_value = mock_args
            mock_parser.return_value = mock_parser_instance
            
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            result = await async_main()
            
            assert result == 130  # Standard keyboard interrupt exit code
            mock_logger.warning.assert_any_call("Analysis interrupted by user")


@pytest.mark.unit
class TestMainFunction:
    """Test main entry point function"""

    def test_main_success(self):
        """Test successful main function execution"""
        with patch('py_github_analyzer.cli.asyncio.run', return_value=0) as mock_run, \
             patch('sys.exit') as mock_exit:
            
            main()
            
            mock_run.assert_called_once()
            mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_main_keyboard_interrupt_in_async_main(self):
        """async_main이 KeyboardInterrupt를 처리하는지 테스트합니다."""
        # 👇 new_callable=AsyncMock 추가
        with patch('py_github_analyzer.cli.analyze_repository_async',
                new_callable=AsyncMock, 
                side_effect=KeyboardInterrupt), \
            patch('sys.argv', ['py-github-analyzer', 'https://github.com/test/repo']):
            
            result = await async_main()
            assert result == 130

    def test_main_exception(self):
        """Test main function with general exception"""
        with patch('py_github_analyzer.cli.asyncio.run', 
                   side_effect=Exception("Test error")), \
             patch('sys.exit') as mock_exit:
            
            main()
            
            mock_exit.assert_called_once_with(1)

    @patch('py_github_analyzer.cli.sys.platform', 'win32')
    def test_main_windows_event_loop_policy(self):
        """Test Windows-specific event loop policy setup"""
        with patch('py_github_analyzer.cli.asyncio.set_event_loop_policy') as mock_policy, \
             patch('py_github_analyzer.cli.asyncio.run', return_value=0), \
             patch('sys.exit'):
            
            main()
            
            # Should set Windows-specific policy
            mock_policy.assert_called_once()
            call_args = mock_policy.call_args[0][0]
            assert 'WindowsProactor' in str(type(call_args))


@pytest.mark.integration
class TestCLIIntegration:
    """Integration tests for CLI functionality"""

    def test_argument_parser_integration(self):
        """Test complete argument parsing integration"""
        parser = create_argument_parser()
        
        # Test comprehensive argument parsing
        test_cases = [
            # Basic usage
            (['https://github.com/test/repo'], {
                'url': 'https://github.com/test/repo',
                'verbose': False,
                'dry_run': False
            }),
            # Full options
            (['https://github.com/test/repo', '-o', './out', '-f', 'json', 
              '-t', 'token', '-m', 'api', '-v', '--dry-run'], {
                'url': 'https://github.com/test/repo',
                'output': './out',
                'format': 'json',
                'github_token': 'token',
                'method': 'api',
                'verbose': True,
                'dry_run': True
            }),
            # Check env only
            (['--check-env'], {
                'check_env': True,
                'url': None
            })
        ]
        
        for args_list, expected in test_cases:
            args = parser.parse_args(args_list)
            for key, value in expected.items():
                assert getattr(args, key) == value

    def test_check_env_status_import_error(self):
        """Test env status check with import error"""
        with patch('py_github_analyzer.cli.TOKEN_UTILS_AVAILABLE', False):
            result = check_env_status()
            # 실제로는 토큰이 없어도 환경 체크는 성공하므로 True
            assert result is True

        @pytest.mark.asyncio
        async def test_full_cli_workflow_mock(self):
            """Test complete CLI workflow with mocks"""
            mock_result = {
                'success': True,
                'metadata': {
                    'repo': 'test/repo',
                    'lang': ['Python'],
                    'size': '1KB'
                },
                'files': [{'path': 'main.py', 'lines': 10}],
                'output_paths': {'json': './output.json'}
            }
            
            test_args = [
                'py-github-analyzer',
                'https://github.com/test/repo',
                '--output', './test_output',
                '--format', 'json',
                '--verbose'
            ]
            
            # 👇 핵심 수정 사항: new_callable=AsyncMock 추가
            with patch('sys.argv', test_args), \
                patch('py_github_analyzer.cli.analyze_repository_async', 
                    new_callable=AsyncMock, 
                    return_value=mock_result) as mock_analyze, \
                patch('py_github_analyzer.cli.print_banner') as mock_banner, \
                patch('py_github_analyzer.cli.get_logger') as mock_get_logger:
                
                mock_get_logger .return_value = MagicMock()
                
                # async_main()을 직접 await로 호출
                result = await async_main()
                
                # Verify workflow
                assert result == 0
                mock_banner.assert_called_once()
                mock_analyze.assert_called_once()
                
                # Verify analyze call arguments
                call_kwargs = mock_analyze.call_args.kwargs
                assert call_kwargs['repo_url'] == 'https://github.com/test/repo'
                assert call_kwargs['output_dir'] == './test_output'
                assert call_kwargs['output_format'] == 'json'
                assert call_kwargs['verbose'] is True

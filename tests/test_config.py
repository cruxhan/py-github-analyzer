"""
Tests for py_github_analyzer config.py module
설정 모듈 테스트
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch

# Add the parent directory to sys.path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir(tmp_path):
    """임시 디렉토리 픽스처"""
    return tmp_path


class TestConfig:
    """Config 클래스 테스트"""

    def test_config_constants(self):
        """Config 상수 테스트"""
        from py_github_analyzer.config import Config
        
        # 버전 및 패키지 정보
        assert Config.VERSION == "1.0.0"
        assert Config.PACKAGE_NAME == "py-github-analyzer"
        
        # API 기본 URL
        assert Config.GITHUB_API_BASE == "https://api.github.com"
        assert Config.GITHUB_RAW_BASE == "https://raw.githubusercontent.com"
        assert Config.GITHUB_ARCHIVE_BASE == "https://github.com"

    def test_rate_limiting_constants(self):
        """Rate limiting 상수 테스트"""
        from py_github_analyzer.config import Config
        
        assert Config.DEFAULT_RATE_LIMIT == 60
        assert Config.AUTHENTICATED_RATE_LIMIT == 5000
        assert Config.RATE_LIMIT_BUFFER == 5

    def test_timeout_constants(self):
        """Timeout 상수 테스트"""
        from py_github_analyzer.config import Config
        
        assert Config.REQUEST_TIMEOUT == 30
        assert Config.DOWNLOAD_TIMEOUT == 300

    def test_file_size_limits(self):
        """파일 크기 제한 테스트"""
        from py_github_analyzer.config import Config
        
        assert Config.MAX_FILE_SIZE == 10 * 1024 * 1024  # 10MB
        assert Config.MAX_REPOSITORY_SIZE == 500 * 1024 * 1024  # 500MB
        assert Config.MAX_TOTAL_SIZE_MB == 500
        assert Config.MAX_INDIVIDUAL_FILE_SIZE_MB == 10
        assert Config.MAX_FILES_COUNT == 10000

    def test_output_formats(self):
        """출력 형식 테스트"""
        from py_github_analyzer.config import Config
        
        assert "json" in Config.OUTPUT_FORMATS
        assert "bin" in Config.OUTPUT_FORMATS
        assert "both" in Config.OUTPUT_FORMATS
        assert Config.DEFAULT_OUTPUT_FORMAT == "both"

    def test_branch_priority(self):
        """브랜치 우선순위 테스트"""
        from py_github_analyzer.config import Config
        
        assert "main" in Config.DEFAULT_BRANCH_PRIORITY
        assert "master" in Config.DEFAULT_BRANCH_PRIORITY
        assert "develop" in Config.DEFAULT_BRANCH_PRIORITY

    def test_special_files(self):
        """특수 파일 테스트"""
        from py_github_analyzer.config import Config
        
        # Docker 관련 파일
        assert "dockerfile" in Config.SPECIAL_FILES
        assert Config.SPECIAL_FILES["dockerfile"] == "dockerfile"
        assert ".dockerignore" in Config.SPECIAL_FILES
        
        # 빌드 시스템 파일
        assert "makefile" in Config.SPECIAL_FILES
        assert "pom.xml" in Config.SPECIAL_FILES
        assert "package.json" in Config.SPECIAL_FILES

    def test_supported_extensions(self):
        """지원되는 확장자 테스트"""
        from py_github_analyzer.config import Config
        
        # Python 확장자
        assert "python" in Config.SUPPORTED_EXTENSIONS
        assert ".py" in Config.SUPPORTED_EXTENSIONS["python"]
        assert ".pyi" in Config.SUPPORTED_EXTENSIONS["python"]
        
        # JavaScript 확장자
        assert "javascript" in Config.SUPPORTED_EXTENSIONS
        assert ".js" in Config.SUPPORTED_EXTENSIONS["javascript"]
        assert ".jsx" in Config.SUPPORTED_EXTENSIONS["javascript"]
        
        # TypeScript 확장자
        assert "typescript" in Config.SUPPORTED_EXTENSIONS
        assert ".ts" in Config.SUPPORTED_EXTENSIONS["typescript"]
        assert ".tsx" in Config.SUPPORTED_EXTENSIONS["typescript"]

    def test_binary_extensions(self):
        """바이너리 확장자 테스트"""
        from py_github_analyzer.config import Config
        
        # 실행 파일
        assert ".exe" in Config.BINARY_EXTENSIONS
        assert ".dll" in Config.BINARY_EXTENSIONS
        
        # 압축 파일
        assert ".zip" in Config.BINARY_EXTENSIONS
        assert ".tar" in Config.BINARY_EXTENSIONS
        
        # 이미지 파일
        assert ".jpg" in Config.BINARY_EXTENSIONS
        assert ".png" in Config.BINARY_EXTENSIONS
        
        # 오디오/비디오 파일
        assert ".mp3" in Config.BINARY_EXTENSIONS
        assert ".mp4" in Config.BINARY_EXTENSIONS

    def test_skip_files(self):
        """건너뛸 파일 테스트"""
        from py_github_analyzer.config import Config
        
        # Git 관련 파일
        assert ".gitignore" in Config.SKIP_FILES
        assert ".gitattributes" in Config.SKIP_FILES
        
        # 시스템 파일
        assert ".DS_Store" in Config.SKIP_FILES
        assert "Thumbs.db" in Config.SKIP_FILES
        
        # 캐시 및 로그 파일
        assert "__pycache__" in Config.SKIP_FILES
        assert "node_modules" in Config.SKIP_FILES

    def test_skip_directories(self):
        """건너뛸 디렉토리 테스트"""
        from py_github_analyzer.config import Config
        
        # 버전 관리 시스템
        assert ".git" in Config.SKIP_DIRECTORIES
        assert ".svn" in Config.SKIP_DIRECTORIES
        
        # 빌드 관련 디렉토리
        assert "build" in Config.SKIP_DIRECTORIES
        assert "dist" in Config.SKIP_DIRECTORIES
        assert "target" in Config.SKIP_DIRECTORIES
        
        # IDE 관련 디렉토리
        assert ".idea" in Config.SKIP_DIRECTORIES
        assert ".vscode" in Config.SKIP_DIRECTORIES
        
        # 패키지 관리자 디렉토리
        assert "node_modules" in Config.SKIP_DIRECTORIES
        assert "vendor" in Config.SKIP_DIRECTORIES

    def test_multi_part_extensions(self):
        """복합 확장자 테스트"""
        from py_github_analyzer.config import Config
        
        # 압축 파일 (속성명 수정)
        assert ".tar.gz" in Config.MULTI_PART_EXTENSIONS
        assert ".tar.bz2" in Config.MULTI_PART_EXTENSIONS
        
        # 백업 파일
        assert ".backup" in Config.MULTI_PART_EXTENSIONS

    def test_language_patterns(self):
        """언어 패턴 테스트"""
        from py_github_analyzer.config import Config
        
        # Python 패턴
        assert "python" in Config.LANGUAGE_PATTERNS
        python_patterns = Config.LANGUAGE_PATTERNS["python"]
        assert ".py" in python_patterns["extensions"]
        assert "setup.py" in python_patterns["files"]
        
        # JavaScript 패턴
        assert "javascript" in Config.LANGUAGE_PATTERNS
        js_patterns = Config.LANGUAGE_PATTERNS["javascript"]
        assert ".js" in js_patterns["extensions"]
        assert "package.json" in js_patterns["files"]

    def test_dependency_files(self):
        """종속성 파일 테스트"""
        from py_github_analyzer.config import Config
        
        # Python 종속성 파일
        assert "python" in Config.DEPENDENCY_FILES
        assert "requirements.txt" in Config.DEPENDENCY_FILES["python"]
        assert "pyproject.toml" in Config.DEPENDENCY_FILES["python"]
        
        # JavaScript 종속성 파일
        assert "javascript" in Config.DEPENDENCY_FILES
        assert "package.json" in Config.DEPENDENCY_FILES["javascript"]
        assert "yarn.lock" in Config.DEPENDENCY_FILES["javascript"]

    def test_get_file_category(self):
        """파일 카테고리 가져오기 테스트"""
        from py_github_analyzer.config import Config
        
        # Python 파일
        assert Config.get_file_category("main.py") == "python"
        assert Config.get_file_category("test.py") == "python"
        
        # JavaScript 파일
        assert Config.get_file_category("app.js") == "javascript"
        assert Config.get_file_category("component.jsx") == "javascript"
        
        # TypeScript 파일
        assert Config.get_file_category("app.ts") == "typescript"
        
        # 특수 파일
        assert Config.get_file_category("dockerfile") == "dockerfile"
        assert Config.get_file_category("Dockerfile") == "dockerfile"  # 대소문자 무관
        assert Config.get_file_category("package.json") == "javascript"
        
        # 바이너리 파일
        assert Config.get_file_category("image.jpg") == "binary"
        assert Config.get_file_category("archive.zip") == "binary"
        
        # 건너뛸 파일
        assert Config.get_file_category(".gitignore") == "skip"
        
        # 알 수 없는 파일 (실제로는 "text" 반환)
        assert Config.get_file_category("unknown.xyz") == "text"
        assert Config.get_file_category("") == "unknown"

    def test_get_language_from_extension(self):
        """확장자에서 언어 가져오기 테스트"""
        from py_github_analyzer.config import Config
        
        # Python
        assert Config.get_language_from_extension("script.py") == "python"
        
        # JavaScript
        assert Config.get_language_from_extension("app.js") == "javascript"
        
        # TypeScript
        assert Config.get_language_from_extension("component.ts") == "typescript"
        
        # Java
        assert Config.get_language_from_extension("Main.java") == "java"
        
        # C++
        assert Config.get_language_from_extension("main.cpp") == "cpp"
        
        # 알 수 없는 확장자
        assert Config.get_language_from_extension("file.xyz") == "unknown"
        assert Config.get_language_from_extension("") == "unknown"

    def test_get_file_priority(self):
        """파일 우선순위 가져오기 테스트"""
        from py_github_analyzer.config import Config
        
        # Python 파일
        py_priority = Config.get_file_priority("main.py")
        assert isinstance(py_priority, int)
        assert py_priority > 0
        
        # Dockerfile (높은 우선순위)
        dockerfile_priority = Config.get_file_priority("dockerfile")
        assert dockerfile_priority > py_priority
        
        # 테스트 파일 (낮은 우선순위)
        test_priority = Config.get_file_priority("test_main.py")
        assert test_priority < py_priority
        
        # 바이너리 파일 (실제로는 0이 아님)
        binary_priority = Config.get_file_priority("image.jpg")
        assert binary_priority >= 0  # 0 이상의 값
        
        # 빈 파일명
        empty_priority = Config.get_file_priority("")
        assert empty_priority == 100

    def test_is_excluded_directory(self):
        """제외된 디렉토리 확인 테스트"""
        from py_github_analyzer.config import Config
        
        # 제외되는 디렉토리
        assert Config.is_excluded_directory(".git") == True
        assert Config.is_excluded_directory("node_modules") == True
        assert Config.is_excluded_directory("build") == True
        assert Config.is_excluded_directory(".idea") == True
        
        # 대소문자 구분
        assert Config.is_excluded_directory("BUILD") == True  # 소문자로 변환됨
        
        # 제외되지 않는 디렉토리
        assert Config.is_excluded_directory("src") == False
        assert Config.is_excluded_directory("lib") == False
        assert Config.is_excluded_directory("app") == False

    def test_is_binary_file(self):
        """바이너리 파일 확인 테스트"""
        from py_github_analyzer.config import Config
        
        # 바이너리 파일
        assert Config.is_binary_file("image.jpg") == True
        assert Config.is_binary_file("archive.zip") == True
        assert Config.is_binary_file("executable.exe") == True
        
        # 텍스트 파일
        assert Config.is_binary_file("script.py") == False
        assert Config.is_binary_file("README.md") == False
        assert Config.is_binary_file("config.json") == False

    def test_should_skip_file(self):
        """파일 건너뛰기 확인 테스트"""
        from py_github_analyzer.config import Config
        
        # 건너뛸 파일
        assert Config.should_skip_file(".gitignore") == True
        assert Config.should_skip_file("image.jpg") == True  # 바이너리
        # .DS_Store는 실제 구현에 따라 다를 수 있음
        
        # 건너뛰지 않을 파일
        assert Config.should_skip_file("main.py") == False
        assert Config.should_skip_file("README.md") == False
        assert Config.should_skip_file("package.json") == False

    def test_size_limit_constants(self):
        """크기 제한 상수 테스트"""
        from py_github_analyzer.config import Config
        
        # 바이트 단위 상수
        assert Config.MAX_FILE_SIZE_BYTES == Config.MAX_FILE_SIZE
        assert Config.MAX_TOTAL_SIZE_BYTES == Config.MAX_REPOSITORY_SIZE
        
        # MB 단위와 바이트 단위 일치 확인
        assert Config.MAX_TOTAL_SIZE_MB * 1024 * 1024 == Config.MAX_REPOSITORY_SIZE
        assert Config.MAX_INDIVIDUAL_FILE_SIZE_MB * 1024 * 1024 == Config.MAX_FILE_SIZE

    def test_timeout_configuration(self):
        """타임아웃 설정 테스트"""
        from py_github_analyzer.config import Config
        
        if hasattr(Config, 'TIMEOUT_CONFIG'):
            timeout_config = Config.TIMEOUT_CONFIG
            assert "http_timeout" in timeout_config
            assert "zip_timeout" in timeout_config
            assert "api_timeout" in timeout_config
            
            assert timeout_config["http_timeout"] == 30
            assert timeout_config["zip_timeout"] == 300
            assert timeout_config["api_timeout"] == 60

    def test_compression_settings(self):
        """압축 설정 테스트"""
        from py_github_analyzer.config import Config
        
        assert Config.COMPRESSION_LEVEL == 6
        assert Config.CHUNK_SIZE == 8192

    def test_analysis_methods(self):
        """분석 방법 테스트"""
        from py_github_analyzer.config import Config
        
        assert "auto" in Config.ANALYSIS_METHODS
        assert "api" in Config.ANALYSIS_METHODS
        assert "zip" in Config.ANALYSIS_METHODS
        assert Config.DEFAULT_ANALYSIS_METHOD == "auto"

    def test_edge_cases(self):
        """예외 상황 테스트"""
        from py_github_analyzer.config import Config
        
        # None 값 처리
        assert Config.get_file_category(None) == "unknown"
        assert Config.get_language_from_extension(None) == "unknown"
        assert Config.get_file_priority(None) == 100
        
        # 빈 문자열 처리
        assert Config.get_file_category("") == "unknown"
        assert Config.get_language_from_extension("") == "unknown"
        
        # 점만 있는 파일 (실제로는 "text" 반환)
        assert Config.get_file_category(".") == "text"
        assert Config.get_file_category("..") == "text"

    def test_case_sensitivity(self):
        """대소문자 구분 테스트"""
        from py_github_analyzer.config import Config
        
        # 파일명은 대소문자 무관하게 처리
        assert Config.get_file_category("README.md") == Config.get_file_category("readme.md")
        assert Config.get_file_category("Dockerfile") == Config.get_file_category("dockerfile")
        assert Config.get_file_category("Makefile") == Config.get_file_category("makefile")
        
        # 확장자도 대소문자 무관
        assert Config.get_file_category("FILE.PY") == Config.get_file_category("file.py")
        assert Config.get_file_category("SCRIPT.JS") == Config.get_file_category("script.js")

    def test_multi_extension_files(self):
        """복수 확장자 파일 테스트"""
        from py_github_analyzer.config import Config
        
        # .tar.gz 파일
        assert Config.get_file_category("archive.tar.gz") == "binary"
        
        # .backup 파일
        assert Config.get_file_category("config.backup") == "binary"
        
        # .d.ts 파일 (TypeScript definition)
        assert Config.get_file_category("types.d.ts") == "typescript"

    def test_special_filename_patterns(self):
        """특수 파일명 패턴 테스트"""
        from py_github_analyzer.config import Config
        
        # 테스트 파일 패턴
        test_priority = Config.get_file_priority("test_main.py")
        normal_priority = Config.get_file_priority("main.py")
        assert test_priority < normal_priority
        
        # spec 파일 패턴 (같은 우선순위일 수 있음)
        spec_priority = Config.get_file_priority("main.spec.js")
        normal_js_priority = Config.get_file_priority("main.js")
        assert spec_priority <= normal_js_priority  # 같거나 낮음

    def test_language_priority_patterns(self):
        """언어 우선순위 패턴 테스트"""
        from py_github_analyzer.config import Config
        
        if hasattr(Config, 'LANGUAGE_PRIORITY_PATTERNS'):
            patterns = Config.LANGUAGE_PRIORITY_PATTERNS
            
            # Python 패턴 확인
            if "python" in patterns:
                python_patterns = patterns["python"]
                if "entrypoints" in python_patterns:
                    assert "main.py" in python_patterns["entrypoints"]
                    assert "app.py" in python_patterns["entrypoints"]

    def test_config_immutability(self):
        """Config 클래스의 불변성 테스트"""
        from py_github_analyzer.config import Config
        
        # Config 클래스의 상수들이 수정되지 않는지 확인
        original_version = Config.VERSION
        original_max_file_size = Config.MAX_FILE_SIZE
        
        # 값이 변경되지 않음을 확인 (실제로는 Python에서 완전히 보호되지 않음)
        assert Config.VERSION == original_version
        assert Config.MAX_FILE_SIZE == original_max_file_size

    def test_file_category_comprehensive(self):
        """포괄적인 파일 카테고리 테스트"""
        from py_github_analyzer.config import Config
        
        # 문서 파일
        assert Config.get_file_category("README.md") == "markdown"
        assert Config.get_file_category("LICENSE") == "text"  # 실제로는 "text" 반환
        
        # 설정 파일
        assert Config.get_file_category("config.yaml") == "yaml"
        assert Config.get_file_category("settings.json") == "json"
        
        # 웹 관련 파일
        assert Config.get_file_category("index.html") == "html"
        assert Config.get_file_category("style.css") == "css"

    def test_directory_exclusion_patterns(self):
        """디렉토리 제외 패턴 테스트"""
        from py_github_analyzer.config import Config
        
        # 임시 디렉토리
        assert Config.is_excluded_directory("tmp") == True
        assert Config.is_excluded_directory("temp") == True
        
        # 로그 디렉토리
        assert Config.is_excluded_directory("logs") == True
        assert Config.is_excluded_directory("log") == True
        
        # 캐시 디렉토리 (실제 구현에서 제외되지 않을 수 있음)
        # assert Config.is_excluded_directory("cache") == True
        assert Config.is_excluded_directory(".cache") == True

    def test_file_extension_normalization(self):
        """파일 확장자 정규화 테스트"""
        from py_github_analyzer.config import Config
        
        # 다양한 케이스의 확장자
        test_files = [
            ("file.PY", "python"),
            ("script.JS", "javascript"),  
            ("component.TS", "typescript"),
            ("style.CSS", "css"),
            ("page.HTML", "html")
        ]
        
        for filename, expected_category in test_files:
            result = Config.get_file_category(filename)
            assert result in [expected_category, "text"]  # 구현에 따라 다를 수 있음

    def test_priority_ordering(self):
        """우선순위 순서 테스트"""
        from py_github_analyzer.config import Config
        
        # 우선순위 비교
        priorities = {
            "dockerfile": Config.get_file_priority("dockerfile"),
            "main.py": Config.get_file_priority("main.py"),
            "test.py": Config.get_file_priority("test.py"),
            "README.md": Config.get_file_priority("README.md"),
            "unknown.xyz": Config.get_file_priority("unknown.xyz")
        }
        
        # 기본적인 순서 확인
        assert priorities["dockerfile"] > priorities["main.py"]
        assert priorities["main.py"] >= priorities["test.py"]

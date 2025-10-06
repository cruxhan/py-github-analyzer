"""
pytest configuration and shared fixtures for py-github-analyzer tests
테스트 공통 설정 및 fixture 정의
"""

import asyncio
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# 테스트용 상수 및 설정
TEST_REPO_URL = "https://github.com/testuser/testrepo"
TEST_OWNER = "testuser"
TEST_REPO = "testrepo"
TEST_TOKEN = "ghp_" + "x" * 36  # 40자 테스트 토큰

@pytest.fixture(scope="session")
def event_loop():
    """Session-wide event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """임시 디렉토리 생성 및 정리"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def mock_env_vars():
    """환경 변수 모킹"""
    with patch.dict(os.environ, {}, clear=True):
        yield

@pytest.fixture
def mock_github_token():
    """GitHub 토큰 모킹"""
    with patch.dict(os.environ, {"GITHUB_TOKEN": TEST_TOKEN}):
        yield TEST_TOKEN

@pytest.fixture
def sample_repo_info():
    """샘플 레포지토리 정보"""
    return {
        "name": TEST_REPO,
        "full_name": f"{TEST_OWNER}/{TEST_REPO}",
        "description": "Test repository",
        "language": "Python",
        "size": 1024,
        "default_branch": "main",
        "private": False,
        "archived": False,
        "disabled": False,
        "topics": ["test", "python"],
        "license": {"name": "MIT"},
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-12-31T23:59:59Z",
        "clone_url": f"https://github.com/{TEST_OWNER}/{TEST_REPO}.git",
        "html_url": f"https://github.com/{TEST_OWNER}/{TEST_REPO}",
        "stargazers_count": 100,
        "watchers_count": 50,
        "forks_count": 25,
        "open_issues_count": 5,
    }

@pytest.fixture
def sample_file_contents():
    """샘플 파일 컨텐츠"""
    return [
        {
            "name": "main.py",
            "path": "main.py",
            "type": "file",
            "size": 500,
            "download_url": f"https://raw.githubusercontent.com/{TEST_OWNER}/{TEST_REPO}/main/main.py",
            "git_url": f"https://api.github.com/repos/{TEST_OWNER}/{TEST_REPO}/git/blobs/abc123",
            "html_url": f"https://github.com/{TEST_OWNER}/{TEST_REPO}/blob/main/main.py",
            "sha": "abc123"
        },
        {
            "name": "requirements.txt",
            "path": "requirements.txt", 
            "type": "file",
            "size": 200,
            "download_url": f"https://raw.githubusercontent.com/{TEST_OWNER}/{TEST_REPO}/main/requirements.txt",
            "git_url": f"https://api.github.com/repos/{TEST_OWNER}/{TEST_REPO}/git/blobs/def456",
            "html_url": f"https://github.com/{TEST_OWNER}/{TEST_REPO}/blob/main/requirements.txt",
            "sha": "def456"
        },
        {
            "name": "src",
            "path": "src",
            "type": "dir"
        }
    ]

@pytest.fixture
def sample_file_data():
    """샘플 파일 데이터"""
    return {
        "name": "main.py",
        "path": "main.py",
        "content": "aW1wb3J0IG9zCgpkZWYgbWFpbigpOgogICAgcHJpbnQoIkhlbGxvLCBXb3JsZCEiKQoKaWYgX19uYW1lX18gPT0gIl9fbWFpbl9fIjoKICAgIG1haW4oKQ==",  # base64 encoded Python code
        "encoding": "base64",
        "size": 89,
        "sha": "abc123",
        "download_url": f"https://raw.githubusercontent.com/{TEST_OWNER}/{TEST_REPO}/main/main.py"
    }

@pytest.fixture
def mock_async_github_client():
    """AsyncGitHubClient 모킹"""
    mock_client = AsyncMock()
    
    # 기본 메서드들 모킹
    mock_client.get_repository_info = AsyncMock()
    mock_client.get_repository_contents = AsyncMock()
    mock_client.get_file_content = AsyncMock()
    mock_client.batch_download_files = AsyncMock()
    mock_client.download_zip_archive = AsyncMock()
    mock_client.close = AsyncMock()
    mock_client.rate_limit_manager = Mock()
    
    return mock_client

@pytest.fixture
def sample_processed_files():
    """처리된 파일 샘플"""
    return [
        {
            "path": "main.py",
            "content": "import os\n\ndef main():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    main()",
            "size": 89,
            "type": "file",
            "language": "python",
            "lines": 6,
            "complexity": 1.5,
            "priority": 950
        },
        {
            "path": "requirements.txt",
            "content": "requests>=2.25.0\nclick>=8.0.0\naiohttp>=3.8.0",
            "size": 45,
            "type": "file", 
            "language": "text",
            "lines": 3,
            "complexity": 1.0,
            "priority": 600
        }
    ]

@pytest.fixture
def mock_httpx_response():
    """httpx Response 모킹"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.headers = {
        "x-ratelimit-limit": "5000", 
        "x-ratelimit-remaining": "4999",
        "x-ratelimit-reset": "1640995200"
    }
    mock_response.json = Mock()
    mock_response.content = b"test content"
    mock_response.text = "test content"
    return mock_response

@pytest.fixture  
def mock_httpx_client():
    """httpx AsyncClient 모킹"""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock()
    mock_client.post = AsyncMock()
    mock_client.aclose = AsyncMock()
    return mock_client

class MockLogger:
    """테스트용 로거 클래스"""
    def __init__(self):
        self.messages = []
        self.debug_enabled = True
        self.verbose = False
    
    def debug(self, message, *args, **kwargs):
        self.messages.append(f"DEBUG: {message}")
    
    def info(self, message, *args, **kwargs):
        self.messages.append(f"INFO: {message}")
    
    def warning(self, message, *args, **kwargs):
        self.messages.append(f"WARNING: {message}")
    
    def error(self, message, *args, **kwargs):
        self.messages.append(f"ERROR: {message}")
    
    def success(self, message, *args, **kwargs):
        self.messages.append(f"SUCCESS: {message}")
    
    def progress_start(self, total, description="Processing"):
        return MockProgress()
    
    def format_size(self, size):
        return f"{size} bytes"
    
    def format_duration(self, seconds):
        return f"{seconds:.2f}s"

class MockProgress:
    """테스트용 진행률 표시기"""
    def __init__(self):
        self.current = 0
        self.total = 100
    
    def update(self, advance=1):
        self.current += advance
    
    def finish(self):
        self.current = self.total

@pytest.fixture
def mock_logger():
    """Mock 로거 fixture"""
    return MockLogger()

@pytest.fixture
def sample_zip_content():
    """샘플 ZIP 파일 컨텐츠"""
    import zipfile
    import io
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('testrepo-main/main.py', 'print("Hello World")')
        zip_file.writestr('testrepo-main/requirements.txt', 'requests>=2.25.0')
        zip_file.writestr('testrepo-main/README.md', '# Test Repository')
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

@pytest.fixture
def sample_metadata():
    """샘플 메타데이터"""
    return {
        "repository": {
            "name": TEST_REPO,
            "owner": TEST_OWNER,
            "description": "Test repository",
            "language": "Python",
            "topics": ["test", "python"],
            "size": 1024,
            "default_branch": "main"
        },
        "analysis": {
            "total_files": 3,
            "total_size": 745,
            "languages": {"Python": 500, "Markdown": 200, "Text": 45},
            "complexity_score": 2.5,
            "priority_files": ["main.py", "requirements.txt"]
        },
        "files": []
    }

# 환경 변수 리셋을 위한 fixture
@pytest.fixture(autouse=True)
def reset_environment():
    """각 테스트 후 환경 변수 리셋"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)

# 비동기 테스트를 위한 마커
pytest_plugins = ["pytest_asyncio"]

# 테스트용 파일 경로 상수
TEST_FILES_DIR = Path(__file__).parent / "test_files"
SAMPLE_PYTHON_FILE = """
import os
import sys
from typing import List, Dict

class TestClass:
    def __init__(self, name: str):
        self.name = name
    
    def process_data(self, data: List[Dict]) -> Dict:
        result = {}
        for item in data:
            if 'key' in item:
                result[item['key']] = item.get('value', None)
        return result

def main():
    test = TestClass("example")
    sample_data = [
        {'key': 'a', 'value': 1},
        {'key': 'b', 'value': 2}
    ]
    result = test.process_data(sample_data)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
"""

SAMPLE_JAVASCRIPT_FILE = """
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.json({ message: 'Hello World' });
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
"""

SAMPLE_CONFIG_FILE = """
[settings]
debug = true
max_workers = 4
timeout = 30

[database]
host = localhost
port = 5432
name = testdb
"""

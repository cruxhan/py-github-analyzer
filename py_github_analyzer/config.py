"""

Configuration module for py-github-analyzer v1.0.0

Central configuration and constants

"""

from pathlib import Path
from typing import Dict, List, Set


class Config:
    """Central configuration class"""

    VERSION = "1.0.0"
    PACKAGE_NAME = "py-github-analyzer"

    # GitHub API configuration
    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com"
    GITHUB_ARCHIVE_BASE = "https://github.com"

    # Branch priority for repository analysis
    DEFAULT_BRANCH_PRIORITY = [
        "main",
        "master",
        "develop",
        "dev",
        "development",
        "trunk",
    ]

    # Rate limiting
    DEFAULT_RATE_LIMIT = 60  # requests per hour without token
    AUTHENTICATED_RATE_LIMIT = 5000  # requests per hour with token
    RATE_LIMIT_BUFFER = 5  # safety buffer for rate limits

    # Timeouts (in seconds)
    REQUEST_TIMEOUT = 30
    DOWNLOAD_TIMEOUT = 300  # 5 minutes for large repositories

    # File processing
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
    MAX_REPOSITORY_SIZE = 500 * 1024 * 1024  # 500MB total
    MAX_TOTAL_SIZE_MB = 500  # Maximum total repository size in MB
    MAX_INDIVIDUAL_FILE_SIZE_MB = 10  # Maximum individual file size in MB
    MAX_FILES_COUNT = 10000  # maximum files to process

    # Output formats
    OUTPUT_FORMATS = ["json", "bin", "both"]
    DEFAULT_OUTPUT_FORMAT = "both"

    # Special filename patterns - files identified by exact name (case-insensitive)
    SPECIAL_FILES = {
        # Docker related
        "dockerfile": "dockerfile",
        "dockerfile.dev": "dockerfile",
        "dockerfile.prod": "dockerfile",
        "dockerfile.test": "dockerfile",
        ".dockerignore": "config",
        "docker-compose.yml": "config",
        "docker-compose.yaml": "config",
        # Build systems
        "makefile": "config",
        "cmake": "config",
        "cmakelists.txt": "config",
        "build.gradle": "java",
        "build.gradle.kts": "kotlin",
        "pom.xml": "java",
        "cargo.toml": "rust",
        "cargo.lock": "rust",
        # Package management
        "package.json": "javascript",
        "package-lock.json": "javascript",
        "yarn.lock": "javascript",
        "requirements.txt": "python",
        "pipfile": "python",
        "pipfile.lock": "python",
        "setup.py": "python",
        "setup.cfg": "python",
        "pyproject.toml": "python",
        "poetry.lock": "python",
        "gemfile": "ruby",
        "gemfile.lock": "ruby",
        "composer.json": "php",
        "composer.lock": "php",
        "go.mod": "go",
        "go.sum": "go",
        # CI/CD
        "jenkinsfile": "config",
        "vagrantfile": "config",
        ".travis.yml": "config",
        ".github": "config",
        "appveyor.yml": "config",
        "circle.yml": "config",
        "azure-pipelines.yml": "config",
        # Configuration files
        "webpack.config.js": "javascript",
        "rollup.config.js": "javascript",
        "babel.config.js": "javascript",
        "jest.config.js": "javascript",
        "tsconfig.json": "typescript",
        "tslint.json": "typescript",
        "eslint.json": "javascript",
        ".eslintrc": "config",
        ".eslintrc.js": "javascript",
        ".eslintrc.json": "config",
        ".prettierrc": "config",
        ".editorconfig": "config",
        # License and docs
        "license": "text",
        "licence": "text",
        "readme": "markdown",
        "readme.md": "markdown",
        "readme.txt": "text",
        "changelog": "text",
        "changelog.md": "markdown",
        "changes": "text",
        "authors": "text",
        "contributors": "text",
    }

    # Multi-part extensions (handled in order of specificity)
    MULTI_PART_EXTENSIONS = {
        # Archives
        ".tar.gz": "binary",
        ".tar.bz2": "binary",
        ".tar.xz": "binary",
        ".tar.Z": "binary",
        # Backup files
        ".backup": "binary",
        ".bak": "binary",
        ".old": "binary",
        ".orig": "binary",
        # Templates and samples
        ".sample": "config",
        ".template": "config",
        ".example": "config",
        # Version control
        ".gitkeep": "config",
        ".gitattributes": "config",
        ".gitignore": "config",
        ".gitmodules": "config",
    }

    # Supported file extensions for analysis
    SUPPORTED_EXTENSIONS = {
        "python": [".py", ".pyx", ".pyi", ".pyw"],
        "javascript": [".js", ".jsx", ".mjs", ".cjs"],
        "typescript": [".ts", ".tsx", ".d.ts"],
        "java": [".java"],
        "kotlin": [".kt", ".kts"],
        "scala": [".scala"],
        "cpp": [".cpp", ".cxx", ".cc", ".c", ".hpp", ".h", ".hxx"],
        "csharp": [".cs", ".csx"],
        "go": [".go"],
        "rust": [".rs"],
        "php": [".php", ".phtml", ".php3", ".php4", ".php5", ".phps"],
        "ruby": [".rb", ".rbw", ".rake"],
        "swift": [".swift"],
        "shell": [".sh", ".bash", ".zsh", ".fish", ".csh", ".tcsh"],
        "powershell": [".ps1", ".psm1", ".psd1"],
        "sql": [".sql"],
        "html": [".html", ".htm", ".xhtml"],
        "css": [".css", ".scss", ".sass", ".less", ".styl"],
        "markdown": [".md", ".markdown", ".mdown", ".mkd"],
        "yaml": [".yml", ".yaml"],
        "json": [".json", ".jsonc", ".json5"],
        "xml": [".xml", ".xsd", ".xsl", ".xslt"],
        "toml": [".toml"],
        "ini": [".ini", ".cfg", ".conf"],
        "dockerfile": [".dockerfile"],
        "text": [".txt", ".text", ".readme"],
        "perl": [".pl", ".pm", ".t"],
        "lua": [".lua"],
        "r": [".r", ".R"],
        "matlab": [".m"],
        "haskell": [".hs", ".lhs"],
        "erlang": [".erl", ".hrl"],
        "elixir": [".ex", ".exs"],
        "clojure": [".clj", ".cljs", ".cljc"],
        "scheme": [".scm", ".ss"],
        "lisp": [".lisp", ".lsp"],
        "fortran": [".f", ".for", ".f90", ".f95"],
        "pascal": [".pas"],
        "ada": [".adb", ".ads"],
        "dart": [".dart"],
        "julia": [".jl"],
        "nim": [".nim"],
        "crystal": [".cr"],
        "zig": [".zig"],
    }

    # Binary extensions to skip
    BINARY_EXTENSIONS = {
        # Executables
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".a",
        ".lib",
        ".o",
        ".obj",
        ".com",
        ".bat",
        ".cmd",
        ".msi",
        ".dmg",
        ".pkg",
        ".deb",
        ".rpm",
        # Archives
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".ace",
        ".arj",
        ".cab",
        ".lzh",
        ".lha",
        ".sit",
        ".sea",
        ".bin",
        ".hqx",
        ".uu",
        # Images
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".svg",
        ".ico",
        ".tiff",
        ".tif",
        ".webp",
        ".psd",
        ".ai",
        ".eps",
        ".raw",
        ".cr2",
        ".nef",
        ".orf",
        ".sr2",
        # Audio/Video
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".mkv",
        ".webm",
        ".m4v",
        ".3gp",
        ".ogv",
        ".wav",
        ".flac",
        ".aac",
        ".ogg",
        ".wma",
        # Documents
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".odt",
        ".ods",
        ".odp",
        ".rtf",
        ".pages",
        ".numbers",
        ".key",
        # Fonts
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".otf",
        ".pfb",
        ".pfm",
        # Other
        ".class",
        ".jar",
        ".war",
        ".ear",
        ".pyc",
        ".pyo",
        ".pyd",
        ".node",
        ".so",
        ".bundle",
    }

    # Files to always skip
    SKIP_FILES = {
        ".gitignore",
        ".gitattributes",
        ".gitmodules",
        ".gitkeep",
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        ".npmrc",
        ".yarnrc",
        ".bowerrc",
        ".travis.yml",
        ".appveyor.yml",
        ".circleci",
        ".gitlab-ci.yml",
        ".buildkite",
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".coverage",
        "coverage.xml",
        ".nyc_output",
        "node_modules",
        "bower_components",
        "vendor",
        ".sass-cache",
        ".tmp",
        ".temp",
        "logs",
        "*.log",
        "npm-debug.log*",
        "yarn-debug.log*",
        "yarn-error.log*",
    }

    # Directories to skip
    SKIP_DIRECTORIES = {
        ".git",
        ".svn",
        ".hg",
        ".bzr",
        ".fossil-settings",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "venv",
        "env",
        ".env",
        ".venv",
        "virtualenv",
        "build",
        "dist",
        "target",
        "out",
        "bin",
        "obj",
        ".idea",
        ".vscode",
        ".vs",
        ".eclipse",
        ".netbeans",
        "coverage",
        ".coverage",
        ".nyc_output",
        "logs",
        "log",
        "tmp",
        "temp",
        ".tmp",
        ".temp",
        ".sass-cache",
        ".parcel-cache",
        ".cache",
        "vendor",
        "packages",
        "bower_components",
    }

    # Language detection patterns
    LANGUAGE_PATTERNS = {
        "python": {
            "extensions": [".py"],
            "files": ["setup.py", "requirements.txt", "pyproject.toml"],
        },
        "javascript": {
            "extensions": [".js", ".jsx"],
            "files": ["package.json", "yarn.lock"],
        },
        "typescript": {
            "extensions": [".ts", ".tsx"],
            "files": ["tsconfig.json", "tslint.json"],
        },
        "java": {"extensions": [".java"], "files": ["pom.xml", "build.gradle"]},
        "cpp": {
            "extensions": [".cpp", ".c", ".hpp", ".h"],
            "files": ["Makefile", "CMakeLists.txt"],
        },
        "csharp": {"extensions": [".cs"], "files": [".csproj", ".sln"]},
        "go": {"extensions": [".go"], "files": ["go.mod", "go.sum"]},
        "rust": {"extensions": [".rs"], "files": ["Cargo.toml", "Cargo.lock"]},
        "php": {"extensions": [".php"], "files": ["composer.json"]},
        "ruby": {"extensions": [".rb"], "files": ["Gemfile", "Rakefile"]},
    }

    # Dependency detection patterns
    DEPENDENCY_FILES = {
        "python": [
            "requirements.txt",
            "Pipfile",
            "pyproject.toml",
            "setup.py",
            "poetry.lock",
        ],
        "javascript": ["package.json", "yarn.lock", "package-lock.json"],
        "typescript": ["package.json", "yarn.lock", "package-lock.json"],
        "java": ["pom.xml", "build.gradle", "gradle.properties"],
        "csharp": [".csproj", "packages.config", ".nuspec"],
        "go": ["go.mod", "go.sum", "Gopkg.toml"],
        "rust": ["Cargo.toml", "Cargo.lock"],
        "php": ["composer.json", "composer.lock"],
        "ruby": ["Gemfile", "Gemfile.lock", ".gemspec"],
    }

    # Priority patterns for different languages
    LANGUAGE_PRIORITY_PATTERNS = {
        "python": {
            "entry_points": ["main.py", "app.py", "__init__.py", "manage.py"],
            "config_files": [
                "setup.py",
                "setup.cfg",
                "pyproject.toml",
                "requirements.txt",
            ],
            "important_dirs": ["src/", "lib/", "app/"],
            "framework_files": {
                "django": ["settings.py", "urls.py", "wsgi.py", "asgi.py", "manage.py"],
                "flask": ["app.py", "wsgi.py", "config.py"],
                "fastapi": ["main.py", "app.py"],
            },
        },
        "javascript": {
            "entry_points": ["index.js", "main.js", "app.js", "server.js"],
            "config_files": ["package.json", "webpack.config.js", ".eslintrc.js"],
            "important_dirs": ["src/", "lib/", "app/"],
            "framework_files": {
                "react": ["index.jsx", "App.jsx", "package.json"],
                "vue": ["main.js", "App.vue", "vue.config.js"],
                "express": ["server.js", "app.js", "index.js"],
            },
        },
    }

    # Analysis methods
    ANALYSIS_METHODS = ["auto", "api", "zip"]
    DEFAULT_ANALYSIS_METHOD = "auto"

    # Compression settings
    COMPRESSION_LEVEL = 6  # balance between speed and size
    CHUNK_SIZE = 8192  # 8KB chunks for streaming

    # Timeout configuration
    TIMEOUT_CONFIG = {"http_timeout": 30, "zip_timeout": 300, "api_timeout": 60}

    # Size limits
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE
    MAX_TOTAL_SIZE_BYTES = MAX_REPOSITORY_SIZE

    @classmethod
    def get_file_category(cls, filename: str) -> str:
        """Enhanced file category detection with special file handling"""
        if not filename:
            return "unknown"

        # Normalize filename
        normalized_name = filename.lower().strip()

        # Check if file should be skipped
        if normalized_name in cls.SKIP_FILES:
            return "skip"

        # Step 1: Check special files by exact name (highest priority)
        if normalized_name in cls.SPECIAL_FILES:
            return cls.SPECIAL_FILES[normalized_name]

        # Step 2: Check multi-part extensions (e.g., .tar.gz)
        for multi_ext, category in cls.MULTI_PART_EXTENSIONS.items():
            if normalized_name.endswith(multi_ext.lower()):
                return category

        # Step 3: Check single extensions
        # Use pathlib to get all suffixes
        path_obj = Path(filename)
        suffixes = path_obj.suffixes

        if suffixes:
            # Try the last suffix first (most specific)
            last_suffix = suffixes[-1].lower()

            # Check if it's a binary extension
            if last_suffix in cls.BINARY_EXTENSIONS:
                return "binary"

            # Check supported extensions
            for category, extensions in cls.SUPPORTED_EXTENSIONS.items():
                if last_suffix in extensions:
                    return category

            # If multiple suffixes, try combinations
            if len(suffixes) > 1:
                combined_suffix = "".join(suffixes).lower()
                for category, extensions in cls.SUPPORTED_EXTENSIONS.items():
                    if combined_suffix in extensions:
                        return category

        # Step 4: Fallback for files without extensions
        # Check if filename contains language keywords
        filename_lower = normalized_name

        # Common patterns
        if any(keyword in filename_lower for keyword in ["test", "spec"]):
            return "text"
        if any(keyword in filename_lower for keyword in ["config", "conf", "cfg"]):
            return "config"
        if any(
            keyword in filename_lower
            for keyword in ["readme", "license", "changelog"]
        ):
            return "text"

        return "text"  # Default to text for unknown files

    @classmethod
    def get_language_from_extension(cls, filename: str) -> str:
        """Get programming language from file extension"""
        if not filename:
            return "unknown"

        category = cls.get_file_category(filename)

        # Map categories to languages
        category_to_language = {
            "python": "python",
            "javascript": "javascript",
            "typescript": "typescript",
            "java": "java",
            "kotlin": "kotlin",
            "scala": "scala",
            "cpp": "cpp",
            "csharp": "csharp",
            "go": "go",
            "rust": "rust",
            "php": "php",
            "ruby": "ruby",
            "swift": "swift",
            "shell": "shell",
            "powershell": "powershell",
            "sql": "sql",
            "html": "html",
            "css": "css",
            "markdown": "markdown",
            "yaml": "yaml",
            "json": "json",
            "xml": "xml",
            "dockerfile": "dockerfile",
        }

        return category_to_language.get(category, "unknown")

    @classmethod
    def get_file_priority(cls, filepath: str) -> int:
        """Calculate file priority for analysis"""
        if not filepath:
            return 100

        filename = Path(filepath).name.lower()
        category = cls.get_file_category(filename)

        # Base priority by category
        category_priorities = {
            "python": 800,
            "javascript": 750,
            "typescript": 750,
            "java": 700,
            "cpp": 650,
            "csharp": 650,
            "go": 650,
            "rust": 650,
            "php": 600,
            "ruby": 600,
            "dockerfile": 900,  # Very important
            "config": 550,
            "markdown": 400,
            "yaml": 500,
            "json": 500,
            "xml": 400,
            "text": 300,
            "binary": 0,
            "skip": 0,
        }

        base_priority = category_priorities.get(category, 200)

        # Bonus for special files
        special_bonuses = {
            "readme.md": 300,
            "package.json": 200,
            "requirements.txt": 200,
            "dockerfile": 400,
            "makefile": 300,
            "setup.py": 200,
            "main.py": 300,
            "index.js": 300,
            "app.py": 300,
            "server.js": 300,
        }

        if filename in special_bonuses:
            base_priority += special_bonuses[filename]

        # Penalty for deep nesting
        depth = filepath.count("/")
        if depth > 3:
            base_priority -= (depth - 3) * 50

        # Penalty for test files (unless very important)
        if "test" in filename or "spec" in filename:
            if base_priority < 600:
                base_priority = max(base_priority - 200, 50)

        return max(base_priority, 10)

    @classmethod
    def is_excluded_directory(cls, dirname: str) -> bool:
        """Check if directory should be excluded"""
        return dirname.lower() in cls.SKIP_DIRECTORIES

    @classmethod
    def is_binary_file(cls, filepath: str) -> bool:
        """Check if file is binary and should be skipped"""
        category = cls.get_file_category(filepath)
        return category in ["binary", "skip"]

    @classmethod
    def should_skip_file(cls, filename: str) -> bool:
        """Check if file should be skipped completely"""
        category = cls.get_file_category(filename)
        return category in ["skip", "binary"]

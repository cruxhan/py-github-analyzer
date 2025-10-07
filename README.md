# 🚀 py-github-analyzer

High-performance async GitHub repository analyzer with AI-optimized code extraction and smart .env file support

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/py-github-analyzer.svg)](https://badge.fury.io/py/py-github-analyzer)

## ✨ Features

### 🔐 **Advanced Authentication**
- **✅ Fine-grained Token Support**: Latest GitHub token standard with `Bearer` authentication
- **✅ Classic Token Support**: Traditional `ghp_` tokens with `token` authentication  
- **🔄 Auto Token Detection**: Automatically detects token type and uses appropriate authentication
- **📁 Multi-source Token Loading**: Environment variables, .env files, CLI parameters
- **🔒 Private Repository Access**: Full access to private repositories with proper permissions

### ⚡ **High Performance**
- **🎯 ZIP-first Strategy**: Optimal download method with intelligent API fallback
- **📊 Smart Rate Limit Management**: Adaptive strategies for different token types
- **🚀 Pure Async Architecture**: Built with modern async/await patterns for maximum performance
- **🔄 Intelligent Fallback**: Graceful degradation when ZIP access fails

### 📋 **Smart Analysis**
- **🔍 Automatic Language Detection**: Accurate detection and dependency mapping
- **📊 Intelligent File Filtering**: Skip binaries, focus on source code with priority scoring
- **📦 Multiple Output Formats**: JSON metadata and structured code extraction
- **🎯 Framework Detection**: Identifies popular frameworks and patterns

### 🌐 **Cross-Platform**
- **💻 Windows, macOS, and Linux**: Full compatibility across all platforms
- **🛡️ Smart Error Handling**: Comprehensive error messages and recovery strategies
- **📁 Smart .env Support**: Automatically finds and loads tokens from .env files

## 📦 Installation

### From PyPI (Recommended)

```pip install py-github-analyzer

From Source

git clone [https://github.com/cruxhan/py-github-analyzer.git](https://github.com/cruxhan/py-github-analyzer.git)
cd py-github-analyzer
pip install -e .
🔑 GitHub Token Setup (Recommended)
Supported Token Types
py-github-analyzer supports all GitHub token types with automatic detection:

🔑 Fine-grained Personal Access Tokens (Latest)
Prefix: github_pat_

Authentication: Bearer header

Permissions: Repository-specific granular access

Security: ✅ Enhanced security with minimal required permissions

Performance: ⚠️ API-only access for private repos (ZIP may fail)

Setup: GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens

🔑 Classic Personal Access Tokens (Traditional)
Prefix: ghp_

Authentication: token header

Permissions: Broad scope-based access

Security: ⚠️ Wide access permissions

Performance: ✅ Full ZIP and API access

Setup: GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)

Creating Tokens
For Fine-grained Tokens (Recommended for Security):
Visit GitHub Settings → Personal Access Tokens → Fine-grained tokens

Select Repository access: Choose specific repositories or all repositories

Set Repository permissions:

Contents: Read (required for file access)

Actions: Read (required for ZIP downloads)

Metadata: Read (required for repository info)

Copy the token (starts with github_pat_)

For Classic Tokens (Faster for Bulk Analysis):
Visit GitHub Settings → Personal Access Tokens → Tokens (classic)

Click Generate new token (classic)

Select repo scope for private repository access

Copy the token (starts with ghp_)

Setting Up Your Token
Option 1: Environment Variable (Recommended)

Bash

# For Linux/macOS
export GITHUB_TOKEN=your_token_here

# For Windows (Command Prompt)
set GITHUB_TOKEN=your_token_here
Option 2: .env file in your project directory

Bash

echo "GITHUB_TOKEN=your_token_here" > .env
Option 3: CLI parameter

Bash

py-github-analyzer [https://github.com/owner/repo](https://github.com/owner/repo) --github-token your_token_here
📋 Usage Examples
Basic Usage
Analyze a public repository

Bash

py-github-analyzer [https://github.com/octocat/Hello-World](https://github.com/octocat/Hello-World)
Analyze with verbose output

Bash

py-github-analyzer [https://github.com/owner/repo](https://github.com/owner/repo) --verbose
Specify output directory and format

Bash

py-github-analyzer [https://github.com/owner/repo](https://github.com/owner/repo) --output-dir ./results --output-format json
Advanced Options
Force specific analysis method

Bash

py-github-analyzer [https://github.com/owner/repo](https://github.com/owner/repo) --method api
py-github-analyzer [https://github.com/owner/repo](https://github.com/owner/repo) --method zip
Multiple output formats

Bash

py-github-analyzer [https://github.com/owner/repo](https://github.com/owner/repo) --output-format both
Dry run (test without processing)

Bash

py-github-analyzer [https://github.com/owner/repo](https://github.com/owner/repo) --dry-run
📖 Output Format
JSON Structure
JSON

{
  "metadata": {
    "repo": "owner/repository-name",
    "desc": "Repository description",
    "lang": ["Primary", "Secondary", "Languages"],
    "size": {
      "repo_size": "288KB",
      "source_size": "294.2KB",
      "display_size": "288KB"
    },
    "files": 117,
    "main": ["main.py", "app.py", "index.js"],
    "deps": ["dependency1", "dependency2"],
    "created": 1634567890,
    "version": "1.0.0"
  },
  "files": [
    {
      "path": "src/main.py",
      "content": "file content here",
      "size": 1234,
      "lines": 45,
      "language": "Python",
      "priority": 950
    }
  ]
}
🤝 Contributing
We welcome contributions! Please see our Contributing Guidelines for details.

Development Setup
Bash

git clone [https://github.com/cruxhan/py-github-analyzer.git](https://github.com/cruxhan/py-github-analyzer.git)
cd py-github-analyzer

# Create virtual environment
python -m venv venv
# On Windows: venv\Scripts\activate
# On Linux/macOS: source venv/bin/activate
source venv/bin/activate 

# Install development dependencies
pip install -e .[dev]

# Run tests
poe test
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

📞 Support
Issues: GitHub Issues

Discussions: GitHub Discussions

Made with ❤️ for developers who need fast, reliable GitHub repository analysis

py-github-analyzer v1.0.0

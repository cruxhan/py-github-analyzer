"""

Command Line Interface for py-github-analyzer v1.0.0

High-performance async GitHub repository analyzer CLI with .env support

"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Windows UTF-8 encoding setup
if os.name == 'nt':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSFSENCODING'] = '0'
    os.environ['PYTHONUTF8'] = '1'
    
    try:
        import locale
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, '')
        except:
            pass

    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

    try:
        import subprocess
        subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
    except:
        pass

from .core import analyze_repository_async
from .config import Config
from .logger import set_verbose, get_logger
from .exceptions import GitHubAnalyzerError, ValidationError

# Import TokenUtils with fallback
try:
    from .utils import TokenUtils
    TOKEN_UTILS_AVAILABLE = True
except ImportError:
    TOKEN_UTILS_AVAILABLE = False
    class TokenUtils:
        """Fallback TokenUtils for when utils module is not available"""
        @staticmethod
        def get_github_token(token=None):
            return token or os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
        
        @staticmethod
        def get_token_info(token):
            if token:
                return {
                    'status': 'provided',
                    'masked': f"{token[:8]}..." if len(token) > 8 else "***",
                    'source': 'parameter' if token else 'environment',
                    'type': 'unknown',
                    'valid': True
                }
            return {'status': 'not_provided'}
        
        @staticmethod
        def _find_env_files():
            return []
        
        @staticmethod
        def _load_env_variables():
            return {}


def create_argument_parser():
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        prog="py-github-analyzer",
        description="High-performance async GitHub repository analyzer with smart .env support",
        epilog="""Example:
  py-github-analyzer https://github.com/user/repo --output ./results

GitHub Token Auto-Detection Priority:
  1. --github-token parameter
  2. GITHUB_TOKEN environment variable
  3. GH_TOKEN environment variable
  4. .env file GITHUB_TOKEN (NEW!)
  5. .env file GH_TOKEN (NEW!)
  6. Anonymous access (rate limited)

Create .env file with: GITHUB_TOKEN=your_token_here
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Positional arguments
    parser.add_argument(
        'url',
        nargs='?',
        help='GitHub repository URL (required unless using --check-env)'
    )

    # Optional arguments
    parser.add_argument(
        '-o', '--output',
        default='./results',
        help='Output directory (default: ./results)'
    )

    parser.add_argument(
        '-f', '--format',
        choices=['json', 'bin', 'both'],
        default='both',
        help='Output format (default: both)'
    )

    parser.add_argument(
        '-t', '--github-token',
        help='GitHub personal access token (or set GITHUB_TOKEN env var or create .env file)'
    )

    parser.add_argument(
        '-m', '--method',
        choices=['auto', 'api', 'zip'],
        default='auto',
        help='Analysis method (default: auto)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate analysis without actual processing'
    )

    parser.add_argument(
        '--no-fallback',
        action='store_true',
        help='Disable fallback mode on errors'
    )

    parser.add_argument(
        '--check-env',
        action='store_true',
        help='Check .env file status and token sources'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'py-github-analyzer {Config.VERSION}'
    )

    return parser


def print_banner():
    """Print application banner"""
    print(f"""
═══════════════════════════════════════════════════════════════════════════════
🔍 py-github-analyzer v{Config.VERSION}
   High-Performance Async GitHub Analyzer with .env Support
═══════════════════════════════════════════════════════════════════════════════
""")


def check_env_status():
    """Check and display .env file status"""
    try:
        print("🔍 Checking .env file status...")
        print("=" * 50)
        
        # Find .env files
        env_files = TokenUtils._find_env_files()
        if env_files:
            print(f"📁 Found .env files:")
            for env_file in env_files:
                print(f"   {env_file}")
        else:
            print("📁 No .env files found")
        
        # Load environment variables
        env_vars = TokenUtils._load_env_variables()
        
        print(f"\n🔑 Token source analysis:")
        for env_var in ['GITHUB_TOKEN', 'GH_TOKEN']:
            sys_token = os.environ.get(env_var)
            env_token = env_vars.get(env_var)
            
            if sys_token:
                print(f"   {env_var}: Found in system environment")
            elif env_token:
                print(f"   {env_var}: Found in .env file")
            else:
                print(f"   {env_var}: Not found")
        
        # Final token detection
        final_token = TokenUtils.get_github_token()
        token_info = TokenUtils.get_token_info(final_token)
        
        print(f"\n🎯 Final token status:")
        if token_info['status'] == 'provided':
            print(f"   Token detected: {token_info['masked']}")
            print(f"   Source: {token_info['source']}")
            print(f"   Type: {token_info['type']}")
            print(f"   Valid format: {token_info['valid']}")
            print(f"   Rate limit: 5000 requests/hour")
        else:
            print(f"   No token detected")
            print(f"   Rate limit: 60 requests/hour (anonymous)")
        
        return True
        
    except ImportError:
        print("⚠️  TokenUtils not available - .env support disabled")
        return False
    except Exception as e:
        print(f"❌ Error checking .env status: {e}")
        return False


def print_analysis_info(args):
    """Print analysis configuration info"""
    logger = get_logger()
    
    logger.info(f"🔍 Repository: {args.url}")
    logger.info(f"📁 Output directory: {args.output}")
    logger.info(f"📄 Output format: {args.format}")
    logger.info(f"🔧 Analysis method: {args.method}")
    
    # Token detection
    try:
        active_token = TokenUtils.get_github_token(args.github_token)
        token_info = TokenUtils.get_token_info(active_token)
        
        if token_info['status'] == 'provided':
            source_info = f"{token_info['type']} from {token_info['source']}"
            if token_info['valid']:
                logger.info(f"🔑 GitHub token: {token_info['masked']} ({source_info})")
                logger.info("⚡ Rate limit: 5000 requests/hour (authenticated)")
                
                if '.env' in token_info['source']:
                    logger.info("✅ Token loaded from .env file - great choice for security!")
            else:
                logger.warning(f"🔑 GitHub token: {token_info['masked']} ({source_info})")
                logger.warning("⚠️  Token format may be invalid - please check your token")
        else:
            logger.info("🔑 GitHub token: Not provided (anonymous access)")
            logger.warning("⚡ Rate limit: 60 requests/hour without token")
            
            logger.info("💡 To increase rate limit and access private repos:")
            logger.info("   Option 1 (Recommended): Create .env file with GITHUB_TOKEN=yourtoken")
            logger.info("   Option 2: Set GITHUB_TOKEN environment variable")
            logger.info("   Option 3: Use --github-token parameter")
            logger.info("   Get token at: https://github.com/settings/tokens")
            
    except ImportError:
        if args.github_token:
            logger.info(f"🔑 GitHub token: Provided via parameter")
        else:
            logger.info("🔑 GitHub token: Not provided (anonymous access)")
            logger.warning("⚡ Limited to 60 requests/hour without token")
    
    if args.dry_run:
        logger.info("🧪 Mode: Dry-run simulation")
    
    print()


def print_results_summary(result):
    """Print analysis results summary"""
    logger = get_logger()
    
    if result.get('success'):
        metadata = result.get('metadata', {})
        files = result.get('files', [])
        
        print("=" * 80)
        print("📊 ANALYSIS RESULTS")
        print("=" * 80)
        
        logger.info(f"🏪 Repository: {metadata.get('repo', 'Unknown')}")
        
        languages = metadata.get('lang', [])
        if languages:
            if isinstance(languages, list) and len(languages) > 0:
                logger.info(f"🐍 Primary language: {languages[0]}")
            else:
                logger.info(f"🐍 Primary language: {languages}")
        
        logger.info(f"📊 Total files analyzed: {len(files)}")
        logger.info(f"💾 Repository size: {metadata.get('size', 'Unknown')}")
        
        deps = metadata.get('deps', [])
        if deps:
            logger.info(f"📦 Dependencies found: {len(deps)}")
        
        # Calculate total lines of code
        total_lines = sum(f.get('lines', 0) for f in files if isinstance(f, dict))
        if total_lines > 0:
            logger.info(f"📝 Total lines of code: {total_lines}")
        
        # Output paths
        output_paths = result.get('output_paths', {})
        if output_paths:
            print("\n💾 Output files:")
            for output_type, path in output_paths.items():
                if path:
                    print(f"   {output_type}: {path}")
        
        if result.get('fallback_mode'):
            print("\n⚠️  Analysis completed in fallback mode (limited information)")
            if 'error_message' in result:
                logger.warning(f"Original error: {result['error_message']}")
            logger.info("💡 Consider adding a GitHub token for full analysis")
        else:
            print("\n✅ Analysis completed successfully")
    else:
        print("\n❌ Analysis failed")
        if 'error_message' in result:
            logger.error(f"Error: {result['error_message']}")


def print_token_help():
    """Print comprehensive token setup help"""
    print("=" * 80)
    print("🔑 GITHUB TOKEN SETUP GUIDE")
    print("=" * 80)
    
    print("\n🎯 Recommended: Create .env file (safest & easiest)")
    print("1. Create .env file in your project directory:")
    print("   echo 'GITHUB_TOKEN=your_token_here' > .env")
    print("2. Add .env to .gitignore to prevent accidental commits:")
    print("   echo '.env' >> .gitignore")
    print("3. Run analyzer - token will be auto-detected!")
    
    print("\n🌍 Alternative: Environment Variables")
    if os.name == 'nt':  # Windows
        print("   set GITHUB_TOKEN=your_token_here")
        print("   # or PowerShell:")
        print("   $env:GITHUB_TOKEN='your_token_here'")
    else:  # Linux/macOS
        print("   export GITHUB_TOKEN=your_token_here")
    
    print("\n⚡ Quick: Command Line Parameter")
    print("   py-github-analyzer https://github.com/user/repo --github-token yourtoken")
    
    print("\n📋 Creating a GitHub Token:")
    print("1. Visit: https://github.com/settings/tokens")
    print("2. Click 'Generate new token (classic)'")
    print("3. Select 'repo' scope for private repository access")
    print("4. Copy the generated token (starts with 'ghp_' or 'github_pat_')")
    
    print("\n🎁 Benefits of using tokens:")
    print("• 5000 requests/hour vs 60 without token")
    print("• Access to private repositories")
    print("• Better rate limit management")
    print("• Full repository analysis (no fallback mode)")


async def async_main():
    """Main async entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    if args.verbose:
        set_verbose(True)
    
    # Handle --check-env flag
    if args.check_env:
        print_banner()
        success = check_env_status()
        return 0 if success else 1
    
    if not args.url:
        parser.error("URL is required unless using --check-env")
    
    logger = get_logger()
    
    try:
        print_banner()
        print_analysis_info(args)
        
        # Check for token if accessing potentially private repo or on verbose mode
        try:
            active_token = TokenUtils.get_github_token(args.github_token)
            if not active_token and ('private' in args.url.lower() or args.verbose):
                print_token_help()
                print()
        except ImportError:
            pass
        
        result = await analyze_repository_async(
            repo_url=args.url,
            output_dir=args.output,
            output_format=args.format,
            github_token=args.github_token,
            method=args.method,
            verbose=args.verbose,
            dry_run=args.dry_run,
            fallback=not args.no_fallback
        )
        
        print_results_summary(result)
        
        if result.get('success'):
            if result.get('fallback_mode'):
                return 2  # Success with warnings
            else:
                return 0  # Complete success
        else:
            return 1  # Failure
            
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        print_token_help()
        return 1
    except GitHubAnalyzerError as e:
        logger.error(f"Analysis error: {e}")
        if 'private' in str(e).lower() or 'authentication' in str(e).lower():
            print_token_help()
        return 1
    except KeyboardInterrupt:
        logger.warning("Analysis interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def main():
    """Main entry point for CLI"""
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        exit_code = asyncio.run(async_main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

"""
Logger module for py-github-analyzer
Enhanced logging with Rich formatting and progress tracking
"""

import logging
import os
import sys
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

# Windows UTF-8 environment setup
if os.name == "nt":  # Windows
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONLEGACYWINDOWSFSENCODING"] = "0"

# Force console to UTF-8 encoding
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    # reconfigure method doesn't exist in Python 3.7
    pass
except Exception:
    # Ignore other errors and continue
    pass


class AnalyzerLogger:
    """Enhanced logger with Rich formatting and progress tracking"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

        # Windows compatible Console setup
        console_kwargs = {
            "width": 100,
            "force_terminal": True,
            "no_color": False,
            "tab_size": 4,
            "stderr": False,  # Use stdout
        }

        try:
            self.console = Console(**console_kwargs)
        except Exception:
            # Fallback to basic console if Rich fails
            self.console = Console(force_terminal=False, no_color=True)

        # Setup Python logger with Rich handler
        self._setup_python_logger()

        # Progress tracking
        self._current_progress = None
        self._progress_tasks = {}

    def _setup_python_logger(self):
        """Setup underlying Python logger with Rich formatting"""
        # Create or get logger for py-github-analyzer
        self.logger = logging.getLogger("py-github-analyzer")

        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Set logging level
        level = logging.DEBUG if self.verbose else logging.INFO
        self.logger.setLevel(level)

        try:
            # Rich handler with custom formatting
            rich_handler = RichHandler(
                console=self.console,
                show_time=True,
                show_path=self.verbose,
                rich_tracebacks=True,
                tracebacks_show_locals=self.verbose,
                markup=True,
                show_level=True,
            )

            # Format for log messages
            formatter = logging.Formatter(fmt="%(message)s", datefmt="%H:%M:%S")
            rich_handler.setFormatter(formatter)

            self.logger.addHandler(rich_handler)

        except Exception:
            # Fallback to basic logging if Rich handler fails
            basic_handler = logging.StreamHandler()
            basic_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            self.logger.addHandler(basic_handler)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        if self.verbose:
            self.logger.debug(f"[dim]🔍 {message}[/dim]", **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(f"ℹ️  {message}", **kwargs)

    def success(self, message: str, **kwargs):
        """Log success message"""
        self.logger.info(f"[green]✅ {message}[/green]", **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(f"[yellow]⚠️  {message}[/yellow]", **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(f"[red]❌ {message}[/red]", **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(f"[bold red]🚨 {message}[/bold red]", **kwargs)

    def progress_start(self, description: str = "Processing...") -> "Progress":
        """Start progress tracking"""
        try:
            self._current_progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console,
                transient=True,
            )
            self._current_progress.start()
            return self._current_progress
        except Exception:
            # Return None if progress tracking fails
            return None

    def progress_add_task(self, description: str, total: int = 100) -> int:
        """Add a progress task"""
        if self._current_progress:
            try:
                task_id = self._current_progress.add_task(description, total=total)
                self._progress_tasks[description] = task_id
                return task_id
            except Exception:
                return -1
        return -1

    def progress_update(self, task_id: int, advance: int = 1):
        """Update progress"""
        if self._current_progress and task_id >= 0:
            try:
                self._current_progress.update(task_id, advance=advance)
            except Exception:
                pass

    def progress_stop(self):
        """Stop progress tracking"""
        if self._current_progress:
            try:
                self._current_progress.stop()
            except Exception:
                pass
            finally:
                self._current_progress = None
                self._progress_tasks = {}

    def print_summary_table(
        self, data: Dict[str, Any], title: str = "Analysis Results"
    ):
        """Print formatted summary table"""
        try:
            table = Table(title=title, show_header=True, header_style="bold blue")
            table.add_column("Property", style="cyan", no_wrap=True)
            table.add_column("Value", style="white")

            for key, value in data.items():
                # Format different value types
                if isinstance(value, (list, tuple)):
                    formatted_value = f"{len(value)} items"
                elif isinstance(value, dict):
                    formatted_value = f"{len(value)} entries"
                elif isinstance(value, (int, float)):
                    formatted_value = str(value)
                else:
                    formatted_value = str(value)[:50]  # Truncate long strings

                table.add_row(key.replace("_", " ").title(), formatted_value)

            self.console.print(table)
        except Exception:
            # Fallback to simple print if Rich table fails
            self.info(f"\n{title}:")
            for key, value in data.items():
                self.info(f"  {key}: {value}")

    def print_panel(self, message: str, title: str = None, style: str = "blue"):
        """Print message in a panel"""
        try:
            panel = Panel(message, title=title, style=style)
            self.console.print(panel)
        except Exception:
            # Fallback to simple message
            if title:
                self.info(f"{title}: {message}")
            else:
                self.info(message)

    def print_file_list(self, files: list, title: str = "Files"):
        """Print formatted file list"""
        if not files:
            self.info(f"No {title.lower()} found")
            return

        try:
            self.console.print(f"\n[bold]{title} ({len(files)} total):[/bold]")
            for i, file_info in enumerate(files[:20]):  # Show first 20
                if isinstance(file_info, dict):
                    name = file_info.get("name", "Unknown")
                    size = file_info.get("size", 0)
                    size_str = f"({size} bytes)" if size > 0 else ""
                else:
                    name = str(file_info)
                    size_str = ""

                self.console.print(
                    f"  {i+1:2d}. [cyan]{name}[/cyan] [dim]{size_str}[/dim]"
                )

            if len(files) > 20:
                self.console.print(f"  ... and {len(files) - 20} more files")

        except Exception:
            # Fallback to simple list
            self.info(f"{title} ({len(files)} total):")
            for file_info in files[:10]:
                if isinstance(file_info, dict):
                    self.info(f"  - {file_info.get('name', 'Unknown')}")
                else:
                    self.info(f"  - {file_info}")

    def log_rate_limit(self, remaining: int, limit: int, reset_time: int):
        """Log rate limit information"""
        if remaining < 10:
            self.warning(f"API rate limit low: {remaining}/{limit} remaining")
        else:
            self.debug(f"API rate limit: {remaining}/{limit} remaining")

    def log_download_progress(self, filename: str, downloaded: int, total: int):
        """Log download progress"""
        if total > 0:
            percent = (downloaded / total) * 100
            self.debug(
                f"Downloading {filename}: {percent:.1f}% ({downloaded}/{total} bytes)"
            )
        else:
            self.debug(f"Downloading {filename}: {downloaded} bytes")

    def log_processing_stats(self, stats: Dict[str, Any]):
        """Log processing statistics"""
        self.info("Processing Statistics:")
        for key, value in stats.items():
            self.info(f"  {key.replace('_', ' ').title()}: {value}")


# Global logger instance
_global_logger: Optional[AnalyzerLogger] = None
_verbose_mode: bool = False


def get_logger(verbose: bool = None) -> AnalyzerLogger:
    """Get or create global logger instance"""
    global _global_logger, _verbose_mode

    if verbose is not None:
        _verbose_mode = verbose

    if _global_logger is None or (_global_logger.verbose != _verbose_mode):
        _global_logger = AnalyzerLogger(_verbose_mode)

    return _global_logger


def set_verbose(verbose: bool):
    """Set global verbose mode"""
    global _verbose_mode, _global_logger
    _verbose_mode = verbose

    # Force recreation of logger with new verbose setting
    if _global_logger is not None:
        _global_logger = AnalyzerLogger(verbose)


def get_progress() -> Optional["Progress"]:
    """Get current progress tracker"""
    logger = get_logger()
    return logger._current_progress


def log_exception(exception: Exception, context: str = ""):
    """Log exception with context"""
    logger = get_logger()

    if context:
        logger.error(f"Error in {context}: {exception}")
    else:
        logger.error(f"Error: {exception}")

    if logger.verbose:
        import traceback

        logger.debug("Full traceback:")
        logger.debug(traceback.format_exc())


# Convenience functions for direct logging
def debug(message: str, **kwargs):
    """Log debug message"""
    get_logger().debug(message, **kwargs)


def info(message: str, **kwargs):
    """Log info message"""
    get_logger().info(message, **kwargs)


def success(message: str, **kwargs):
    """Log success message"""
    get_logger().success(message, **kwargs)


def warning(message: str, **kwargs):
    """Log warning message"""
    get_logger().warning(message, **kwargs)


def error(message: str, **kwargs):
    """Log error message"""
    get_logger().error(message, **kwargs)


def critical(message: str, **kwargs):
    """Log critical message"""
    get_logger().critical(message, **kwargs)

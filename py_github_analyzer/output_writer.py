# py_github_analyzer/output_writer.py
import json
import pickle
from pathlib import Path
from typing import Any, Dict, List

import aiofiles

from .config import Config
from .logger import AnalyzerLogger


class OutputWriter:
    def __init__(self, logger: AnalyzerLogger):
        self._logger = logger

    async def write(
        self,
        output_dir: str,
        output_format: str,
        metadata: Dict[str, Any],
        files: List[Dict[str, Any]],
        filename_prefix: str,
    ) -> Dict[str, str]:
        try:
            output_dir_path = Path(output_dir)
            output_dir_path.mkdir(parents=True, exist_ok=True)

            import asyncio
            output_data = {
                "metadata": metadata,
                "files": files,
                "generated_at": asyncio.get_running_loop().time(),
                "version": Config.VERSION,
            }

            output_paths: Dict[str, str] = {}

            if output_format in ("json", "both"):
                json_path = output_dir_path / f"{filename_prefix}.json"
                async with aiofiles.open(json_path, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(output_data, indent=2, ensure_ascii=False))
                output_paths["json"] = str(json_path)
                self._logger.debug(f"Saved JSON output: {json_path}")

            if output_format in ("bin", "both"):
                bin_path = output_dir_path / f"{filename_prefix}.bin"
                async with aiofiles.open(bin_path, "wb") as f:
                    await f.write(pickle.dumps(output_data))
                output_paths["bin"] = str(bin_path)
                self._logger.debug(f"Saved binary output: {bin_path}")

            return output_paths
        except Exception as e:
            self._logger.error(f"Failed to save output files: {e}")
            return {"error": f"Output save failed: {e}"}

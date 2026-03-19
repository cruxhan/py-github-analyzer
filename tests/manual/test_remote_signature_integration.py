# tests/manual/test_remote_signature_integration.py
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from py_github_analyzer.core import analyze_repository_async, analyze_signatures_async

TARGET_REPO_URL = "https://github.com/cruxhan/py-github-analyzer.git"


def _print_header(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def _load_json_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_json_outputs(output_paths: dict) -> list[str]:
    results = []
    for _, value in output_paths.items():
        if isinstance(value, str) and value.endswith(".json") and os.path.exists(value):
            results.append(value)
    return results


def _summarize_full_analysis(data: dict) -> None:
    metadata = data.get("metadata", {})
    files = data.get("files", [])

    print(f"repository  : {metadata.get('repo')}")
    print(f"languages   : {metadata.get('lang')}")
    print(f"files       : {len(files)}")
    print(f"deps        : {len(metadata.get('deps', []))}")
    print(f"main        : {metadata.get('main', [])[:10]}")

    if files:
        print("\n[file preview]")
        for file_entry in files[:5]:
            print(
                f"  - {file_entry.get('path')} "
                f"(lang={file_entry.get('language')}, "
                f"lines={file_entry.get('lines')}, "
                f"size={file_entry.get('size')})"
            )


def _summarize_signature_result(result: dict) -> None:
    summary = result.get("summary", {})
    files = result.get("files", [])

    print(f"repository      : {result.get('repository')}")
    print(f"files_analyzed  : {summary.get('files_analyzed')}")
    print(f"files_skipped   : {summary.get('files_skipped')}")
    print(f"classes         : {summary.get('classes')}")
    print(f"functions       : {summary.get('functions')}")
    print(f"methods         : {summary.get('methods')}")

    print("\n[signature preview]")
    shown = 0
    for file_entry in files:
        classes = file_entry.get("classes", [])
        functions = file_entry.get("functions", [])
        if not classes and not functions:
            continue

        print(f"\n  file: {file_entry.get('path')}")
        for cls in classes[:2]:
            bases = cls.get("bases", [])
            print(f"    class {cls.get('name')} bases={bases}")
            if cls.get("docstring"):
                print(f"      docstring: {cls['docstring']}")
            for method in cls.get("methods", [])[:5]:
                params = ", ".join(method.get("params", []))
                returns = method.get("return_type")
                prefix = "async " if method.get("is_async") else ""
                print(f"      {prefix}def {method.get('name')}({params}) -> {returns}")
                if method.get("docstring"):
                    print(f"        docstring: {method['docstring']}")
        for func in functions[:3]:
            params = ", ".join(func.get("params", []))
            returns = func.get("return_type")
            prefix = "async " if func.get("is_async") else ""
            print(f"    {prefix}def {func.get('name')}({params}) -> {returns}")
            if func.get("docstring"):
                print(f"      docstring: {func['docstring']}")

        shown += 1
        if shown >= 5:
            break


def _save_signature_result(result: dict, output_path: Path) -> str:
    output_path.mkdir(parents=True, exist_ok=True)
    repo_slug = result.get("repository", "unknown").replace("/", "_")
    file_path = output_path / f"{repo_slug}_signatures_full.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return str(file_path)


def _assert_signature_expectations(result: dict) -> None:
    summary = result.get("summary", {})
    files = result.get("files", [])

    assert result.get("success") is True, f"success flag missing or False: {result}"
    assert summary.get("files_analyzed", 0) > 0, f"No Python files analyzed. summary={summary}"
    assert summary.get("classes", 0) > 0 or summary.get("functions", 0) > 0, \
        "No signatures extracted"
    assert len(files) > 0, "Signature result files list is empty"

    has_expected_file = any(
        isinstance(f.get("path"), str) and any(
            f["path"].endswith(target)
            for target in ("core.py", "cli.py", "utils.py", "ast_extractor.py")
        )
        for f in files
    )
    assert has_expected_file, \
        f"Expected files (core/cli/utils/ast_extractor) not found. paths={[f.get('path') for f in files]}"


async def main() -> int:
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    with tempfile.TemporaryDirectory(prefix="py_github_analyzer_manual_") as temp_root:
        temp_root_path = Path("D:\kdic\Desktop")
        full_output_dir = temp_root_path / "full_analysis"
        sig_output_dir = temp_root_path / "signature_json"

        _print_header("1) FULL REPOSITORY ANALYSIS")
        full_result = await analyze_repository_async(
            repo_url=TARGET_REPO_URL,
            output_dir=str(full_output_dir),
            output_format="json",
            github_token=github_token,
            method="auto",
            verbose=True,
            dry_run=False,
            fallback=True,
        )

        assert full_result.get("success") is True, \
            f"Full analysis failed: {full_result.get('error_message')}"

        full_json_outputs = _find_json_outputs(full_result.get("output_paths", {}))
        assert full_json_outputs, "No full analysis JSON output file produced"

        full_json_data = _load_json_file(full_json_outputs[0])
        print(f"full json output: {full_json_outputs[0]}")
        _summarize_full_analysis(full_json_data)

        _print_header("2) AST SIGNATURE ANALYSIS")
        signature_result = await analyze_signatures_async(
            repo_url=TARGET_REPO_URL,
            github_token=github_token,
            method="auto",
            verbose=True,
            fallback=True,
            include_docstring=True,
            public_only=True,
            include_private_magic_methods=True,
        )

        sig_json_path = _save_signature_result(signature_result, sig_output_dir)
        print(f"signature json output: {sig_json_path}")
        _summarize_signature_result(signature_result)
        _assert_signature_expectations(signature_result)

        _print_header("3) OUTPUT PATHS")
        print("[full analysis outputs]")
        for key, value in full_result.get("output_paths", {}).items():
            if value:
                print(f"  - {key}: {value}")

        print("\n[signature output]")
        print(f"  - json: {sig_json_path}")

        _print_header("4) RESULT")
        summary = signature_result.get("summary", {})
        print("Remote repository analysis completed successfully.")
        print(
            f"Signature extraction: "
            f"{summary.get('files_analyzed')} files / "
            f"{summary.get('classes')} classes / "
            f"{summary.get('methods')} methods / "
            f"{summary.get('functions')} top-level functions"
        )
        print("All assertions passed.")

    return 0


if __name__ == "__main__":
    if sys.platform == "win32" and sys.version_info < (3, 14):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nCancelled by user")
        raise SystemExit(130)

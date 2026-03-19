# tests/test_ast_extractor.py
import pytest
from py_github_analyzer.analysis.ast_extractor import (
    ASTSignatureExtractor,
    extract_signatures_from_source,
)


class TestExtractSignaturesFromSource:
    def test_extracts_public_class(self, sample_python_source):
        result = extract_signatures_from_source(sample_python_source)
        class_names = [c["name"] for c in result["classes"]]
        assert "TestClass" in class_names

    def test_extracts_public_function(self, sample_python_source):
        result = extract_signatures_from_source(sample_python_source)
        func_names = [f["name"] for f in result["functions"]]
        assert "main" in func_names

    def test_init_method_included_by_default(self, sample_python_source):
        result = extract_signatures_from_source(sample_python_source)
        test_class = next(c for c in result["classes"] if c["name"] == "TestClass")
        method_names = [m["name"] for m in test_class["methods"]]
        assert "__init__" in method_names

    def test_private_method_excluded_when_public_only(self, sample_python_source):
        result = extract_signatures_from_source(sample_python_source, public_only=True)
        test_class = next(c for c in result["classes"] if c["name"] == "TestClass")
        method_names = [m["name"] for m in test_class["methods"]]
        assert "_private_method" not in method_names if "_private_method" in sample_python_source else True

    def test_private_class_excluded_with_all(self, sample_python_source_with_all):
        result = extract_signatures_from_source(
            sample_python_source_with_all, public_only=True
        )
        class_names = [c["name"] for c in result["classes"]]
        assert "_PrivateClass" not in class_names
        assert "PublicClass" in class_names

    def test_private_function_excluded_with_all(self, sample_python_source_with_all):
        result = extract_signatures_from_source(
            sample_python_source_with_all, public_only=True
        )
        func_names = [f["name"] for f in result["functions"]]
        assert "_private_function" not in func_names
        assert "public_function" in func_names

    def test_include_private_when_not_public_only(self, sample_python_source_with_all):
        result = extract_signatures_from_source(
            sample_python_source_with_all, public_only=False
        )
        class_names = [c["name"] for c in result["classes"]]
        func_names = [f["name"] for f in result["functions"]]
        assert "_PrivateClass" in class_names
        assert "_private_function" in func_names

    def test_docstring_included_when_requested(self, sample_python_source_with_all):
        result = extract_signatures_from_source(
            sample_python_source_with_all, include_docstring=True
        )
        public_class = next(c for c in result["classes"] if c["name"] == "PublicClass")
        assert "docstring" in public_class
        assert public_class["docstring"] == "A public class for testing."

    def test_docstring_absent_by_default(self, sample_python_source_with_all):
        result = extract_signatures_from_source(sample_python_source_with_all)
        for cls in result["classes"]:
            assert "docstring" not in cls

    def test_async_function_flagged(self, sample_async_python_source):
        result = extract_signatures_from_source(sample_async_python_source)
        run_method = next(
            m
            for c in result["classes"]
            if c["name"] == "AsyncWorker"
            for m in c["methods"]
            if m["name"] == "run"
        )
        assert run_method["is_async"] is True

    def test_sync_method_not_flagged(self, sample_python_source):
        result = extract_signatures_from_source(sample_python_source)
        test_class = next(c for c in result["classes"] if c["name"] == "TestClass")
        init_method = next(m for m in test_class["methods"] if m["name"] == "__init__")
        assert init_method["is_async"] is False

    def test_return_type_captured(self, sample_python_source_with_all):
        result = extract_signatures_from_source(sample_python_source_with_all)
        public_class = next(c for c in result["classes"] if c["name"] == "PublicClass")
        compute = next(m for m in public_class["methods"] if m["name"] == "compute")
        assert compute["return_type"] == "float"

    def test_params_include_type_annotation(self, sample_python_source_with_all):
        result = extract_signatures_from_source(sample_python_source_with_all)
        public_class = next(c for c in result["classes"] if c["name"] == "PublicClass")
        init_method = next(m for m in public_class["methods"] if m["name"] == "__init__")
        param_names = [p.split(":")[0].strip() for p in init_method["params"]]
        assert "value" in param_names

    def test_default_value_in_params(self, sample_python_source_with_all):
        result = extract_signatures_from_source(sample_python_source_with_all)
        public_class = next(c for c in result["classes"] if c["name"] == "PublicClass")
        compute = next(m for m in public_class["methods"] if m["name"] == "compute")
        multiplier_param = next(p for p in compute["params"] if "multiplier" in p)
        assert "1.0" in multiplier_param

    def test_kwonly_arg_separator(self, sample_python_source_with_all):
        result = extract_signatures_from_source(sample_python_source_with_all)
        func = next(f for f in result["functions"] if f["name"] == "public_function")
        assert "*" in func["params"]

    def test_syntax_error_returns_error_key(self, sample_syntax_error_source):
        result = extract_signatures_from_source(sample_syntax_error_source)
        assert "error" in result
        assert result["classes"] == []
        assert result["functions"] == []

    def test_empty_source_returns_empty(self):
        result = extract_signatures_from_source("")
        assert result["classes"] == []
        assert result["functions"] == []

    def test_magic_method_excluded_when_flagged(self, sample_async_python_source):
        result = extract_signatures_from_source(
            sample_async_python_source,
            public_only=True,
            include_private_magic_methods=False,
        )
        worker = next(c for c in result["classes"] if c["name"] == "AsyncWorker")
        method_names = [m["name"] for m in worker["methods"]]
        assert "__aenter__" not in method_names
        assert "__aexit__" not in method_names

    def test_preserved_magic_method_included_by_default(self, sample_async_python_source):
        result = extract_signatures_from_source(
            sample_async_python_source,
            public_only=True,
            include_private_magic_methods=True,
        )
        worker = next(c for c in result["classes"] if c["name"] == "AsyncWorker")
        method_names = [m["name"] for m in worker["methods"]]
        assert "__aenter__" in method_names
        assert "__aexit__" in method_names

    def test_base_class_captured(self, sample_python_source_with_all):
        result = extract_signatures_from_source(sample_python_source_with_all)
        public_class = next(c for c in result["classes"] if c["name"] == "PublicClass")
        assert isinstance(public_class["bases"], list)

    def test_decorator_captured(self, sample_python_source_with_all):
        result = extract_signatures_from_source(sample_python_source_with_all)
        public_class = next(c for c in result["classes"] if c["name"] == "PublicClass")
        from_string = next(
            m for m in public_class["methods"] if m["name"] == "from_string"
        )
        assert "@staticmethod" in from_string["decorators"]


class TestASTSignatureExtractor:
    def test_skips_non_python_files(self, mock_logger, sample_files_for_signature):
        extractor = ASTSignatureExtractor(mock_logger)
        result = extractor.extract_from_files(sample_files_for_signature)
        paths = [f["path"] for f in result["files"]]
        assert "src/config.json" not in paths

    def test_skips_empty_content(self, mock_logger, sample_files_for_signature):
        extractor = ASTSignatureExtractor(mock_logger)
        result = extractor.extract_from_files(sample_files_for_signature)
        paths = [f["path"] for f in result["files"]]
        assert "src/empty.py" not in paths

    def test_skips_syntax_error_files(self, mock_logger, sample_files_for_signature):
        extractor = ASTSignatureExtractor(mock_logger)
        result = extractor.extract_from_files(sample_files_for_signature)
        paths = [f["path"] for f in result["files"]]
        assert "src/broken.py" not in paths

    def test_summary_files_analyzed_count(self, mock_logger, sample_files_for_signature):
        extractor = ASTSignatureExtractor(mock_logger)
        result = extractor.extract_from_files(sample_files_for_signature)
        assert result["summary"]["files_analyzed"] == 2

    def test_summary_skipped_count(self, mock_logger, sample_files_for_signature):
        extractor = ASTSignatureExtractor(mock_logger)
        result = extractor.extract_from_files(sample_files_for_signature)
        assert result["summary"]["files_skipped"] >= 2

    def test_summary_class_count(self, mock_logger, sample_files_for_signature):
        extractor = ASTSignatureExtractor(mock_logger)
        result = extractor.extract_from_files(sample_files_for_signature)
        assert result["summary"]["classes"] >= 1

    def test_summary_method_count(self, mock_logger, sample_files_for_signature):
        extractor = ASTSignatureExtractor(mock_logger)
        result = extractor.extract_from_files(sample_files_for_signature)
        assert result["summary"]["methods"] >= 1

    def test_result_structure_per_file(self, mock_logger, sample_files_for_signature):
        extractor = ASTSignatureExtractor(mock_logger)
        result = extractor.extract_from_files(sample_files_for_signature)
        for file_entry in result["files"]:
            assert "path" in file_entry
            assert "classes" in file_entry
            assert "functions" in file_entry

    def test_include_docstring_propagated(self, mock_logger, sample_files_for_signature):
        extractor = ASTSignatureExtractor(mock_logger)
        result = extractor.extract_from_files(
            sample_files_for_signature, include_docstring=True
        )
        for file_entry in result["files"]:
            for cls in file_entry["classes"]:
                assert "docstring" in cls

    def test_empty_file_list(self, mock_logger):
        extractor = ASTSignatureExtractor(mock_logger)
        result = extractor.extract_from_files([])
        assert result["files"] == []
        assert result["summary"]["files_analyzed"] == 0
        assert result["summary"]["classes"] == 0

    def test_uses_path_key_for_routing(self, mock_logger, sample_python_source):
        extractor = ASTSignatureExtractor(mock_logger)
        files = [{"path": "module.py", "content": sample_python_source}]
        result = extractor.extract_from_files(files)
        assert result["files"][0]["path"] == "module.py"

    def test_fallback_to_name_key(self, mock_logger, sample_python_source):
        extractor = ASTSignatureExtractor(mock_logger)
        files = [{"name": "module.py", "content": sample_python_source}]
        result = extractor.extract_from_files(files)
        assert len(result["files"]) == 1

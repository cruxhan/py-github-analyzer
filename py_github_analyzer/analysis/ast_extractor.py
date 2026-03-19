# py_github_analyzer/analysis/ast_extractor.py
import ast
from typing import Any, Dict, List, Optional

from ..logger import AnalyzerLogger, get_logger

_PRESERVED_MAGIC_METHODS = frozenset({
    "__init__", "__call__", "__str__", "__repr__",
    "__enter__", "__exit__", "__aenter__", "__aexit__",
    "__len__", "__iter__", "__next__", "__getitem__",
    "__setitem__", "__delitem__", "__contains__",
    "__eq__", "__lt__", "__le__", "__gt__", "__ge__",
    "__add__", "__sub__", "__mul__", "__truediv__",
    "__hash__", "__bool__", "__del__", "__await__",
    "__aiter__", "__anext__",
})


def _annotation_to_str(node: Optional[ast.expr]) -> Optional[str]:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return "???"


def _extract_docstring(body: List[ast.stmt]) -> Optional[str]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        first_line = body[0].value.value.strip().splitlines()[0].strip()
        return first_line if first_line else None
    return None


def _extract_function_signature(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    include_docstring: bool,
) -> Dict[str, Any]:
    args = node.args
    params: List[str] = []

    defaults_offset = len(args.args) - len(args.defaults)
    for i, arg in enumerate(args.args):
        annotation = _annotation_to_str(arg.annotation) if arg.annotation else "???"
        param = f"{arg.arg}: {annotation}"
        default_idx = i - defaults_offset
        if default_idx >= 0:
            param += f" = {ast.unparse(args.defaults[default_idx])}"
        params.append(param)

    if args.vararg:
        annotation = _annotation_to_str(args.vararg.annotation) if args.vararg.annotation else "???"
        params.append(f"*{args.vararg.arg}: {annotation}")

    for i, arg in enumerate(args.kwonlyargs):
        annotation = _annotation_to_str(arg.annotation) if arg.annotation else "???"
        param = f"{arg.arg}: {annotation}"
        kw_default = args.kw_defaults[i] if i < len(args.kw_defaults) else None
        if kw_default is not None:
            param += f" = {ast.unparse(kw_default)}"
        params.append(param)

    if args.kwarg:
        annotation = _annotation_to_str(args.kwarg.annotation) if args.kwarg.annotation else "???"
        params.append(f"**{args.kwarg.arg}: {annotation}")

    sig: Dict[str, Any] = {
        "name": node.name,
        "params": params,
        "return_type": _annotation_to_str(node.returns),
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "decorators": [f"@{ast.unparse(d)}" for d in node.decorator_list],
    }
    if include_docstring:
        sig["docstring"] = _extract_docstring(node.body)
    return sig


def _resolve_all_names(tree: ast.Module) -> Optional[List[str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        return [
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]
    return None


def _is_public_class_or_func(name: str, all_names: Optional[List[str]], public_only: bool) -> bool:
    if not public_only:
        return True
    if all_names is not None:
        return name in all_names
    return not name.startswith("_")


def _is_included_method(
    name: str,
    public_only: bool,
    include_private_magic_methods: bool,
) -> bool:
    if not public_only:
        return True
    if name.startswith("__") and name.endswith("__"):
        return include_private_magic_methods and name in _PRESERVED_MAGIC_METHODS
    return not name.startswith("_")


def extract_signatures_from_source(
    source: str,
    include_docstring: bool = False,
    public_only: bool = True,
    include_private_magic_methods: bool = True,
) -> Dict[str, Any]:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}", "classes": [], "functions": []}

    all_names = _resolve_all_names(tree)
    classes: List[Dict[str, Any]] = []
    top_functions: List[Dict[str, Any]] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if not _is_public_class_or_func(node.name, all_names, public_only):
                continue

            methods: List[Dict[str, Any]] = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not _is_included_method(item.name, public_only, include_private_magic_methods):
                        continue
                    methods.append(_extract_function_signature(item, include_docstring))

            class_entry: Dict[str, Any] = {
                "name": node.name,
                "bases": [ast.unparse(b) for b in node.bases],
                "decorators": [f"@{ast.unparse(d)}" for d in node.decorator_list],
                "methods": methods,
            }
            if include_docstring:
                class_entry["docstring"] = _extract_docstring(node.body)
            classes.append(class_entry)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _is_public_class_or_func(node.name, all_names, public_only):
                continue
            top_functions.append(_extract_function_signature(node, include_docstring))

    return {"classes": classes, "functions": top_functions}


class ASTSignatureExtractor:
    def __init__(self, logger: Optional[AnalyzerLogger] = None):
        self._logger = logger or get_logger()

    def extract_from_files(
        self,
        files: List[Dict[str, Any]],
        include_docstring: bool = False,
        public_only: bool = True,
        include_private_magic_methods: bool = True,
    ) -> Dict[str, Any]:
        result_files: List[Dict[str, Any]] = []
        total_classes = 0
        total_functions = 0
        total_methods = 0
        skipped = 0

        for file_entry in files:
            path: str = file_entry.get("path", file_entry.get("name", ""))
            content: str = file_entry.get("content", "")

            if not path.endswith(".py"):
                continue
            if not content or not isinstance(content, str):
                skipped += 1
                continue

            parsed = extract_signatures_from_source(
                content,
                include_docstring=include_docstring,
                public_only=public_only,
                include_private_magic_methods=include_private_magic_methods,
            )

            if "error" in parsed:
                self._logger.warning(f"AST parse failed for {path}: {parsed['error']}")
                skipped += 1
                continue

            class_count = len(parsed["classes"])
            func_count = len(parsed["functions"])
            method_count = sum(len(c["methods"]) for c in parsed["classes"])

            total_classes += class_count
            total_functions += func_count
            total_methods += method_count

            result_files.append({
                "path": path,
                "classes": parsed["classes"],
                "functions": parsed["functions"],
            })

        self._logger.info(
            f"Signature extraction complete: {len(result_files)} files, "
            f"{total_classes} classes, {total_methods} methods, {total_functions} top-level functions"
        )

        return {
            "files": result_files,
            "summary": {
                "files_analyzed": len(result_files),
                "files_skipped": skipped,
                "classes": total_classes,
                "functions": total_functions,
                "methods": total_methods,
            },
        }

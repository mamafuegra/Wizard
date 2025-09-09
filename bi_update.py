import os
import ast
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple


EXCLUDE_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
}


def is_python_file(file_path: str) -> bool:
    return file_path.endswith(".py")


def read_text_safely(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def count_code_lines(lines: List[str]) -> int:
    code_line_count = 0
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        code_line_count += 1
    return code_line_count


def extract_imports(tree: ast.AST) -> Set[str]:
    modules: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                base = (alias.name or "").split(".")[0]
                if base:
                    modules.add(base)
        elif isinstance(node, ast.ImportFrom):
            # from x.y import z  -> module is x.y, we take base x
            # from .x import y    -> relative import; capture as .x to distinguish local
            if node.module:
                base = node.module.split(".")[0]
                if base:
                    modules.add(base)
            else:
                # Relative import with no module, include a dotted marker with first alias segment
                for alias in node.names:
                    alias_base = (alias.name or "").split(".")[0]
                    if alias_base:
                        modules.add(f".{alias_base}")
    return modules


def extract_definitions(tree: ast.AST) -> Tuple[List[str], List[str]]:
    function_names: List[str] = []
    class_names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if getattr(node, "name", None):
                function_names.append(node.name)
        elif isinstance(node, ast.ClassDef):
            if getattr(node, "name", None):
                class_names.append(node.name)
    return function_names, class_names


def gather_file_stats(root: str, rel_path: str) -> Dict[str, Any]:
    abs_path = os.path.join(root, rel_path)
    text = read_text_safely(abs_path)
    lines = text.splitlines()
    physical_lines = len(lines)
    code_lines = count_code_lines(lines)

    functions: List[str] = []
    classes: List[str] = []
    imports: Set[str] = set()
    try:
        tree = ast.parse(text, filename=rel_path)
        functions, classes = extract_definitions(tree)
        imports = extract_imports(tree)
    except Exception:
        # Skip AST-derived stats on parse error but keep line counts
        pass

    return {
        "path": rel_path.replace("\\", "/"),
        "physical_lines": physical_lines,
        "code_lines": code_lines,
        "num_functions": len(functions),
        "num_classes": len(classes),
        "functions": functions,
        "classes": classes,
        "imports": sorted(imports),
    }


def walk_python_files(root: str) -> List[str]:
    py_files: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded directories in-place for efficiency
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_NAMES]
        for filename in filenames:
            if is_python_file(filename):
                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, root)
                py_files.append(rel_path)
    py_files.sort()
    return py_files


def aggregate_stats(root: str) -> Dict[str, Any]:
    files = walk_python_files(root)

    per_file: List[Dict[str, Any]] = []
    unique_imports: Set[str] = set()
    import_to_file_count: Dict[str, int] = {}

    total_physical_lines = 0
    total_code_lines = 0
    total_functions = 0
    total_classes = 0

    for rel_path in files:
        stats = gather_file_stats(root, rel_path)

        total_physical_lines += stats["physical_lines"]
        total_code_lines += stats["code_lines"]
        total_functions += stats["num_functions"]
        total_classes += stats["num_classes"]

        per_file.append(stats)

        file_imports = set(stats.get("imports", []))
        for module in file_imports:
            unique_imports.add(module)
            import_to_file_count[module] = import_to_file_count.get(module, 0) + 1

    per_file.sort(key=lambda x: x["path"])  # deterministic output

    summary: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": os.path.basename(os.path.abspath(root)),
        "totals": {
            "python_files": len(files),
            "physical_lines": total_physical_lines,
            "code_lines": total_code_lines,
            "functions": total_functions,
            "classes": total_classes,
            "unique_imports": len(unique_imports),
        },
        "imports": {
            "by_module": {
                module: {
                    "files_using": import_to_file_count.get(module, 0)
                }
                for module in sorted(unique_imports)
            },
            "all": sorted(unique_imports),
        },
        "files": per_file,
    }
    return summary


def main() -> None:
    root = os.path.dirname(os.path.abspath(__file__))
    report = aggregate_stats(root)
    output_path = os.path.join(root, "bi.json")
    # If a previous report exists, compute a simple delta for totals
    try:
        if os.path.exists(output_path):
            with open(output_path, "r", encoding="utf-8") as prev_f:
                prev = json.load(prev_f)
            prev_totals = prev.get("totals", {})
            curr_totals = report.get("totals", {})
            report["totals_delta"] = {
                key: curr_totals.get(key, 0) - int(prev_totals.get(key, 0) or 0)
                for key in {
                    "python_files",
                    "physical_lines",
                    "code_lines",
                    "functions",
                    "classes",
                    "unique_imports",
                }
            }
    except Exception:
        # If delta computation fails, continue without it
        pass
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    # Small console message for convenience
    print(f"Wrote BI report to {os.path.basename(output_path)}")
    print(
        json.dumps(
            {
                "python_files": report["totals"]["python_files"],
                "physical_lines": report["totals"]["physical_lines"],
                "code_lines": report["totals"]["code_lines"],
                "functions": report["totals"]["functions"],
                "classes": report["totals"]["classes"],
                "unique_imports": report["totals"]["unique_imports"],
                "python_files_delta": report.get("totals_delta", {}).get("python_files", 0),
                "code_lines_delta": report.get("totals_delta", {}).get("code_lines", 0),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()



"""Lightweight AST-based analysis for common languages.

Uses Python's built-in `ast` module for Python files and simple regex-based
extraction for other languages.  This avoids heavy native dependencies
like tree-sitter while still being useful for structural analysis.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Python AST analysis
# ---------------------------------------------------------------------------


def analyze_python_file(source: str, filepath: str = "<unknown>") -> str:
    """Parse a Python file and extract classes, functions, imports, and globals."""
    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as exc:
        return f"SyntaxError in {filepath}: {exc}"

    imports: list[str] = []
    classes: list[str] = []
    functions: list[str] = []
    globals_found: list[str] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
        elif isinstance(node, ast.ClassDef):
            bases = ", ".join(_unparse_name(b) for b in node.bases)
            methods = [
                n.name for n in ast.iter_child_nodes(node) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
            ]
            classes.append(f"class {node.name}({bases}): methods=[{', '.join(methods)}]")
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            args = [a.arg for a in node.args.args]
            prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
            functions.append(f"{prefix}def {node.name}({', '.join(args)})")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    globals_found.append(target.id)

    sections: list[str] = [f"=== Python Structure: {filepath} ==="]
    if imports:
        sections.append(f"\nImports ({len(imports)}):")
        for imp in imports[:30]:
            sections.append(f"  - {imp}")
        if len(imports) > 30:
            sections.append(f"  ... and {len(imports) - 30} more")
    if classes:
        sections.append(f"\nClasses ({len(classes)}):")
        for cls in classes:
            sections.append(f"  - {cls}")
    if functions:
        sections.append(f"\nFunctions ({len(functions)}):")
        for fn in functions:
            sections.append(f"  - {fn}")
    if globals_found:
        sections.append(f"\nModule-level variables: {', '.join(globals_found[:20])}")

    return "\n".join(sections)


def _unparse_name(node: ast.expr) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return "?"


# ---------------------------------------------------------------------------
# Generic regex-based extraction for JS/TS, Java, Go, Rust, etc.
# ---------------------------------------------------------------------------

_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "javascript": [
        ("class", re.compile(r"(?:export\s+)?class\s+(\w+)")),
        ("function", re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)")),
        ("const/arrow", re.compile(r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(")),
        ("import", re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]")),
        ("require", re.compile(r"require\(['\"]([^'\"]+)['\"]\)")),
    ],
    "typescript": [
        ("interface", re.compile(r"(?:export\s+)?interface\s+(\w+)")),
        ("type", re.compile(r"(?:export\s+)?type\s+(\w+)")),
        ("class", re.compile(r"(?:export\s+)?class\s+(\w+)")),
        ("function", re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)")),
        ("const/arrow", re.compile(r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(")),
        ("import", re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]")),
    ],
    "java": [
        ("class", re.compile(r"(?:public|private|protected)?\s*(?:abstract\s+)?class\s+(\w+)")),
        ("interface", re.compile(r"(?:public\s+)?interface\s+(\w+)")),
        ("method", re.compile(
            r"(?:public|private|protected)\s+(?:static\s+)?(?:\w+(?:<[^>]*>)?)\s+(\w+)\s*\("
        )),
        ("import", re.compile(r"import\s+([\w.]+);")),
    ],
    "go": [
        ("function", re.compile(r"func\s+(\w+)\s*\(")),
        ("method", re.compile(r"func\s+\(\w+\s+\*?\w+\)\s+(\w+)\s*\(")),
        ("struct", re.compile(r"type\s+(\w+)\s+struct")),
        ("interface", re.compile(r"type\s+(\w+)\s+interface")),
        ("import", re.compile(r'"([\w./\-]+)"')),
    ],
    "rust": [
        ("function", re.compile(r"(?:pub\s+)?(?:async\s+)?fn\s+(\w+)")),
        ("struct", re.compile(r"(?:pub\s+)?struct\s+(\w+)")),
        ("enum", re.compile(r"(?:pub\s+)?enum\s+(\w+)")),
        ("trait", re.compile(r"(?:pub\s+)?trait\s+(\w+)")),
        ("impl", re.compile(r"impl(?:<[^>]*>)?\s+(\w+)")),
        ("use", re.compile(r"use\s+([\w:]+)")),
    ],
}

_EXT_TO_LANG: dict[str, str] = {
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
}


def analyze_file_structure(source: str, filepath: str) -> str:
    """Analyze a source file and return structural information.

    Dispatches to the Python AST parser for .py files or uses
    regex-based extraction for other supported languages.
    """
    ext = Path(filepath).suffix.lower()

    if ext == ".py":
        return analyze_python_file(source, filepath)

    lang = _EXT_TO_LANG.get(ext)
    if lang is None:
        return f"[No structural parser available for '{ext}' files]"

    patterns = _PATTERNS[lang]
    findings: dict[str, list[str]] = {}
    for category, pattern in patterns:
        matches = pattern.findall(source)
        if matches:
            findings[category] = matches

    if not findings:
        return f"[No structural elements found in {filepath}]"

    lines = [f"=== {lang.title()} Structure: {filepath} ==="]
    for category, items in findings.items():
        lines.append(f"\n{category} ({len(items)}):")
        for item in items[:30]:
            lines.append(f"  - {item}")
        if len(items) > 30:
            lines.append(f"  ... and {len(items) - 30} more")
    return "\n".join(lines)

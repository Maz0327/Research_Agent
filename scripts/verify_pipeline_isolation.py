#!/usr/bin/env python3
"""
Verify semantic pipeline doesn't import legacy modules.

This script checks that the new semantic pipeline files don't
accidentally import from legacy modules, which would break the
clean separation between old and new code.

Run: python scripts/verify_pipeline_isolation.py
"""

import ast
import sys
from pathlib import Path


# New semantic pipeline files that MUST NOT import legacy
NEW_PIPELINE_FILES = [
    "backend/pipeline/transcript_acquisition.py",
    "backend/pipeline/stages/source_identity.py",
    "backend/pipeline/stages/semantic_extraction.py",
    "backend/pipeline/stages/document_assembly.py",
    "backend/pipeline/semantic_validation.py",
    "backend/pipeline/prompts/semantic_extraction_prompt.py",
    "backend/pipeline/prompts/semantic_synthesis_prompt.py",
    "backend/models/semantic_units.py",
    "backend/models/document_outputs.py",
]

# Forbidden import patterns - these indicate legacy leakage
FORBIDDEN_IMPORTS = [
    "backend.legacy",
    "backend.pipeline.extraction",  # Should use shim sparingly or not at all
    "backend.pipeline.validation",  # v1 validation
    "backend.integrations.transcripts",  # Should use transcript_acquisition
]

# Allowed exceptions (for backwards compatibility shims only)
ALLOWED_EXCEPTIONS = {
    # Format: "file_path": ["allowed.import.path"]
}


def get_imports_from_file(file_path: Path) -> list[str]:
    """Extract all import paths from a Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except SyntaxError as e:
        print(f"  ⚠️  Syntax error in {file_path}: {e}")
        return []

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return imports


def check_file(file_path: Path, forbidden: list[str], allowed: dict) -> list[str]:
    """Check a file for forbidden imports. Returns list of violations."""
    violations = []
    imports = get_imports_from_file(file_path)

    file_key = str(file_path)
    exceptions = allowed.get(file_key, [])

    for imp in imports:
        for forbidden_pattern in forbidden:
            if imp.startswith(forbidden_pattern):
                # Check if this import is explicitly allowed
                if imp not in exceptions:
                    violations.append(f"{imp} (matches '{forbidden_pattern}')")

    return violations


def main():
    """Run pipeline isolation verification."""
    print("=" * 60)
    print("Semantic Pipeline Isolation Verification")
    print("=" * 60)
    print()

    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    all_violations = {}
    files_checked = 0
    files_missing = 0

    for rel_path in NEW_PIPELINE_FILES:
        file_path = project_root / rel_path

        if not file_path.exists():
            print(f"⚠️  Missing: {rel_path}")
            files_missing += 1
            continue

        violations = check_file(file_path, FORBIDDEN_IMPORTS, ALLOWED_EXCEPTIONS)
        files_checked += 1

        if violations:
            all_violations[rel_path] = violations
            print(f"❌ {rel_path}")
            for v in violations:
                print(f"   └─ {v}")
        else:
            print(f"✅ {rel_path}")

    print()
    print("-" * 60)

    if all_violations:
        print(f"\n❌ FAILED: {len(all_violations)} files have forbidden imports")
        print("\nForbidden import patterns:")
        for pattern in FORBIDDEN_IMPORTS:
            print(f"  - {pattern}")
        print("\nTo fix:")
        print("  1. New pipeline code should use:")
        print("     - backend.pipeline.transcript_acquisition")
        print("     - backend.pipeline.stages.source_identity")
        print("     - backend.pipeline.stages.semantic_extraction")
        print("  2. Legacy compatibility imports should go through shims")
        return 1
    else:
        print(f"\n✅ PASSED: All {files_checked} files are properly isolated")
        if files_missing > 0:
            print(f"   ({files_missing} files not yet created)")
        return 0


if __name__ == "__main__":
    sys.exit(main())

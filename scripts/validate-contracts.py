#!/usr/bin/env python3
"""Validate backend/frontend API contracts.

Compares backend Pydantic models with frontend TypeScript interfaces
to detect contract drift before it causes runtime errors.

Usage:
    python scripts/validate-contracts.py

Exit codes:
    0 - All contracts valid
    1 - Contract drift detected (missing/extra fields)
"""
import ast
import re
import sys
from pathlib import Path

# Define contract mappings: (backend_file, backend_class, frontend_file, frontend_interface)
CONTRACTS = [
    (
        "backend/models/job_record.py",
        "Artifacts",
        "frontend/store/jobs.ts",
        "JobArtifacts",
    ),
]

# Fields that are expected to be missing (deprecated but kept for backward compatibility)
DEPRECATED_FIELDS = {
    "clips",
    "quotes",
    "quality_gate_passed",
    "content_blueprints",
    "gap_analysis",
    "research_starter",
}

# Critical fields that MUST exist in frontend
CRITICAL_FIELDS = {
    "doc_0_path",
    "doc_1_path",
    "doc_2_path",
    "doc_3_path",
    "source_ledger",
    "jump_start",
    "semantic_brief",
    "booster_output",
    "booster_expansion_md",
    "producer_packet_md",
}


def extract_pydantic_fields(file_path: Path, class_name: str) -> set[str]:
    """Extract field names from a Pydantic model using AST."""
    content = file_path.read_text()
    tree = ast.parse(content)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            fields = set()
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.add(item.target.id)
            return fields

    raise ValueError(f"Class {class_name} not found in {file_path}")


def extract_typescript_fields(file_path: Path, interface_name: str) -> set[str]:
    """Extract field names from a TypeScript interface using regex."""
    content = file_path.read_text()

    # Find the interface definition
    # Match: export interface InterfaceName { ... }
    pattern = rf"export\s+interface\s+{interface_name}\s*\{{"
    match = re.search(pattern, content)
    if not match:
        raise ValueError(f"Interface {interface_name} not found in {file_path}")

    # Find the closing brace (count braces)
    start = match.end()
    brace_count = 1
    end = start

    while brace_count > 0 and end < len(content):
        if content[end] == "{":
            brace_count += 1
        elif content[end] == "}":
            brace_count -= 1
        end += 1

    interface_body = content[start:end-1]

    # Extract field names (match: fieldName?: type or fieldName: type)
    # Skip commented lines and nested objects
    fields = set()
    for line in interface_body.split("\n"):
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith("//") or line.startswith("/*") or line.startswith("*"):
            continue
        # Match field definition
        field_match = re.match(r"(\w+)\??:", line)
        if field_match:
            fields.add(field_match.group(1))

    return fields


def validate_contract(
    backend_file: str,
    backend_class: str,
    frontend_file: str,
    frontend_interface: str,
) -> tuple[bool, list[str]]:
    """Validate a single contract between backend and frontend."""
    project_root = Path(__file__).parent.parent

    backend_path = project_root / backend_file
    frontend_path = project_root / frontend_file

    if not backend_path.exists():
        return False, [f"Backend file not found: {backend_file}"]
    if not frontend_path.exists():
        return False, [f"Frontend file not found: {frontend_file}"]

    try:
        backend_fields = extract_pydantic_fields(backend_path, backend_class)
    except ValueError as e:
        return False, [str(e)]

    try:
        frontend_fields = extract_typescript_fields(frontend_path, frontend_interface)
    except ValueError as e:
        return False, [str(e)]

    issues = []

    # Fields in backend but missing in frontend (excluding deprecated)
    missing_in_frontend = backend_fields - frontend_fields - DEPRECATED_FIELDS
    if missing_in_frontend:
        for field in missing_in_frontend:
            if field in CRITICAL_FIELDS:
                issues.append(f"CRITICAL MISSING: {field} (in backend {backend_class} but not in frontend {frontend_interface})")
            else:
                issues.append(f"WARNING: {field} missing in frontend {frontend_interface}")

    # Check critical fields specifically
    missing_critical = CRITICAL_FIELDS - frontend_fields
    for field in missing_critical:
        if field not in [i.split(":")[1].strip() if ":" in i else "" for i in issues]:
            issues.append(f"CRITICAL: {field} must be in frontend {frontend_interface}")

    return len([i for i in issues if "CRITICAL" in i]) == 0, issues


def main() -> int:
    """Run contract validation."""
    print("Validating backend/frontend contracts...")
    print("=" * 60)

    all_valid = True
    all_issues = []

    for backend_file, backend_class, frontend_file, frontend_interface in CONTRACTS:
        print(f"\nChecking: {backend_class} <-> {frontend_interface}")
        valid, issues = validate_contract(
            backend_file, backend_class, frontend_file, frontend_interface
        )

        if not valid:
            all_valid = False

        if issues:
            all_issues.extend(issues)
            for issue in issues:
                if "CRITICAL" in issue:
                    print(f"  {issue}")
                else:
                    print(f"  {issue}")
        else:
            print("  All fields present")

    print("\n" + "=" * 60)

    if all_valid and not any("CRITICAL" in i for i in all_issues):
        print("All contracts valid")
        return 0
    else:
        print(f"Contract validation failed ({len([i for i in all_issues if 'CRITICAL' in i])} critical issues)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

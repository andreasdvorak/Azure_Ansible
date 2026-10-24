#!/usr/bin/env python3
"""Check the local Ansible installation, declared versions, Azure access, and SSH."""

from __future__ import annotations

import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / "bin" / "python"

if VENV_PYTHON.is_file() and os.path.realpath(sys.prefix) != os.path.realpath(VENV):
    os.execv(
        str(VENV_PYTHON),
        [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
    )

try:
    import yaml
except ImportError:
    yaml = None

try:
    from packaging.requirements import InvalidRequirement, Requirement
    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import InvalidVersion, Version
except ImportError:
    InvalidRequirement = InvalidSpecifier = InvalidVersion = None
    Requirement = SpecifierSet = Version = None


class EnvironmentCheck:
    """Run checks and collect their outcomes."""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.current_section = ""
        self.section_results: dict[str, dict[str, int]] = {}

    def section(self, title: str) -> None:
        """Print a section heading and prepare its result counters."""
        self.current_section = title
        self.section_results[title] = {"PASS": 0, "FAIL": 0, "SKIP": 0}
        print(f"\n{title}\n{'-' * len(title)}")

    def result(self, status: str, message: str) -> None:
        """Print a check result and update the summary counters."""
        marker = {"PASS": "OK", "FAIL": "FAIL", "SKIP": "SKIP"}.get(status, status)
        print(f"  [{marker:<4}] {message}")
        self.section_results[self.current_section][status] += 1
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        else:
            self.skipped += 1

    def summary(self) -> None:
        """Print per-section and overall check totals."""
        print("\nSummary")
        print("-------")
        for title, results in self.section_results.items():
            totals = ", ".join(
                f"{count} {label.lower()}"
                for label, count in (
                    ("PASS", results["PASS"]),
                    ("FAIL", results["FAIL"]),
                    ("SKIP", results["SKIP"]),
                )
                if count
            )
            print(f"  {title}: {totals or 'no checks'}")

        print(
            f"\nOverall: {self.passed} passed, {self.failed} failed, "
            f"{self.skipped} skipped"
        )

    def command(
        self,
        label: str,
        command: Sequence[str],
        timeout: int = 120,
    ) -> bool:
        """Run a subprocess, reporting its output if the check fails."""
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            self.result("FAIL", f"{label}: command not found: {command[0]}")
            return False
        except subprocess.TimeoutExpired:
            self.result("FAIL", f"{label}: timed out after {timeout} seconds")
            return False

        if completed.returncode == 0:
            self.result("PASS", label)
            return True

        self.result("FAIL", label)
        output = "\n".join(
            part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
        )
        if output:
            print(textwrap.indent(output, "    "))
        return False


def check_python_environment(checks: EnvironmentCheck) -> None:
    """Verify that the project virtual environment is present and active."""
    if not VENV_PYTHON.is_file():
        checks.result("FAIL", f"Project virtual environment is missing: {VENV_PYTHON}")
    elif Path(sys.prefix).resolve() != VENV.resolve():
        checks.result("FAIL", "The script is not running inside the project .venv")
    else:
        checks.result(
            "PASS",
            f"Python {sys.version.split()[0]} from {Path(sys.executable)}",
        )


def check_python_requirements(checks: EnvironmentCheck) -> None:
    """Compare installed Python packages with requirements.txt."""
    if not VENV_PYTHON.is_file() or Path(sys.prefix).resolve() != VENV.resolve():
        checks.result("SKIP", "Python package versions require the project .venv")
        return
    if Requirement is None or Version is None:
        checks.result("FAIL", "Cannot parse Python requirements: packaging is not installed")
        return

    requirements_file = ROOT / "requirements.txt"
    try:
        lines = requirements_file.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        checks.result("FAIL", f"Cannot read {requirements_file.name}: {exc}")
        return

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.partition("#")[0].strip()
        if not line:
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement as exc:
            checks.result(
                "FAIL",
                f"{requirements_file.name}:{line_number}: invalid requirement: {exc}",
            )
            continue

        if requirement.marker and not requirement.marker.evaluate():
            checks.result("SKIP", f"{requirement.name}: environment marker does not apply")
            continue

        try:
            installed_version = importlib.metadata.version(requirement.name)
        except importlib.metadata.PackageNotFoundError:
            checks.result("FAIL", f"{requirement.name}: not installed")
            continue

        try:
            is_satisfied = Version(installed_version) in requirement.specifier
        except InvalidVersion as exc:
            checks.result(
                "FAIL",
                f"{requirement.name}: installed version {installed_version!r} is invalid: {exc}",
            )
            continue

        if is_satisfied:
            checks.result(
                "PASS",
                f"{requirement.name} {installed_version} satisfies {requirement.specifier}",
            )
        else:
            checks.result(
                "FAIL",
                f"{requirement.name} {installed_version} does not satisfy "
                f"{requirement.specifier}",
            )


def check_collection_requirements(checks: EnvironmentCheck) -> None:
    """Compare installed Ansible collections with requirements.yml."""
    if yaml is None or SpecifierSet is None or Version is None:
        checks.result(
            "FAIL",
            "Cannot parse collection requirements: install PyYAML and packaging",
        )
        return

    requirements_file = ROOT / "requirements.yml"
    try:
        data = yaml.safe_load(requirements_file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        checks.result("FAIL", f"Cannot read {requirements_file.name}: {exc}")
        return

    collections = data.get("collections") if isinstance(data, dict) else None
    if not isinstance(collections, list):
        checks.result("FAIL", f"{requirements_file.name} must contain a collections list")
        return

    for collection in collections:
        if not isinstance(collection, dict):
            checks.result("FAIL", "Invalid collection entry in requirements.yml")
            continue

        name = collection.get("name")
        constraint = collection.get("version", "")
        if not isinstance(name, str) or name.count(".") != 1 or not isinstance(constraint, str):
            checks.result("FAIL", f"Invalid collection requirement: {collection!r}")
            continue

        try:
            specifier = SpecifierSet(constraint)
        except InvalidSpecifier as exc:
            checks.result("FAIL", f"{name}: invalid version constraint {constraint!r}: {exc}")
            continue

        namespace, collection_name = name.split(".")
        manifest_path = (
            ROOT
            / "collections"
            / "ansible_collections"
            / namespace
            / collection_name
            / "MANIFEST.json"
        )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            installed_version = manifest["collection_info"]["version"]
            parsed_version = Version(installed_version)
        except FileNotFoundError:
            checks.result("FAIL", f"{name}: collection is not installed in ./collections")
            continue
        except (OSError, json.JSONDecodeError, KeyError, InvalidVersion, TypeError) as exc:
            checks.result("FAIL", f"{name}: cannot read installed collection version: {exc}")
            continue

        if parsed_version in specifier:
            checks.result(
                "PASS",
                f"{name} {installed_version} satisfies {constraint or '(any version)'}",
            )
        else:
            checks.result(
                "FAIL",
                f"{name} {installed_version} does not satisfy {constraint or '(any version)'}",
            )


def main() -> int:
    """Run the environment checks and return a process exit code."""
    checks = EnvironmentCheck()
    print(f"Environment check\n=================\nProject: {ROOT}")

    checks.section("Python environment")
    check_python_environment(checks)

    checks.section("Requirements and dependencies")
    check_python_requirements(checks)
    check_collection_requirements(checks)
    if VENV_PYTHON.is_file():
        checks.command(
            "Python package dependencies are consistent (pip check)",
            [str(VENV_PYTHON), "-m", "pip", "check"],
        )
    else:
        checks.result("SKIP", "pip check requires the project .venv")

    checks.section("Ansible installation")
    ansible = VENV / "bin" / "ansible"
    ansible_playbook = VENV / "bin" / "ansible-playbook"
    for executable in (ansible, ansible_playbook, VENV / "bin" / "ansible-galaxy"):
        if executable.is_file() and os.access(executable, os.X_OK):
            checks.result("PASS", f"Found {executable.relative_to(ROOT)}")
        else:
            checks.result("FAIL", f"Missing executable: {executable.relative_to(ROOT)}")

    checks.section("Azure CLI and access")
    azure_cli = shutil.which("az")
    if azure_cli is None:
        checks.result("FAIL", "Azure CLI is not installed or not available on PATH")
    else:
        checks.result("PASS", f"Azure CLI is installed: {azure_cli}")
        checks.command(
            "Azure CLI can obtain an Azure Resource Manager access token",
            [
                azure_cli,
                "account",
                "get-access-token",
                "--resource",
                "https://management.azure.com/",
                "--output",
                "none",
            ],
            timeout=60,
        )

    if ansible_playbook.is_file() and os.access(ansible_playbook, os.X_OK):
        checks.command(
            "Controller, HTTPS, and Azure read-access checks",
            [
                str(ansible_playbook),
                "playbooks/environments_tests.yml",
            ],
            timeout=180,
        )
    else:
        checks.result("SKIP", "Controller and Azure checks require ansible-playbook")

    checks.section("SSH and managed hosts")
    if shutil.which("ssh") is None:
        checks.result("FAIL", "SSH client is not installed")
    elif ansible.is_file() and os.access(ansible, os.X_OK):
        checks.command(
            "SSH connectivity and remote Python check for inventory group 'azure'",
            [str(ansible), "azure", "-m", "ansible.builtin.ping"],
            timeout=180,
        )
    else:
        checks.result("SKIP", "SSH connectivity check requires the Ansible executable")

    checks.summary()
    return 1 if checks.failed else 0


if __name__ == "__main__":
    sys.exit(main())

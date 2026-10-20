#!/usr/bin/env python3
"""Report outdated dependencies declared in requirements files.

The script understands Python requirement files (``requirements*.txt``) and
Ansible Galaxy requirement files (``requirements*.yml``).  Every dependency is
looked up on PyPI or Ansible Galaxy and compared with the version declared in
the file.

Example::

    $ .venv/bin/python scripts/check_requirements.py
    File              Type  Package       Constraint  Current  Max allowed  Latest  Status
    ----------------  ----  ------------  ----------  -------  -----------  ------  ----------------
    requirements.txt  pip   ansible-core  >=2.20.1    2.20.1   2.21.5       2.21.5  update available
    requirements.txt  pip   yamllint      ==1.38.0    1.38.0   1.38.0       1.38.0  up to date

    2 dependencies checked: 1 up to date, 1 update available

Columns:

``Constraint`` is the version specifier exactly as written in the file, for
example ``==2.20.1`` (a pin) or ``>=4.1.0`` (a minimum).  ``Current`` is the
version that specifier is anchored to: the pinned version or the lower bound
of a range.  ``Max allowed`` is the newest release that still satisfies the
constraint.  ``Latest`` is the newest release on the index regardless of the
constraint.  Both differ only when the constraint has an upper bound or an
exact pin.

Without arguments the script checks ``requirements.txt`` and
``requirements.yml`` in the current directory.  Pass files or directories to
check other locations; directories are scanned recursively while vendored
trees (``.venv``, ``collections``, ...) are skipped.

The exit code is 0 on success, 1 when ``--check`` is used and an update is
available, and 2 when a requirements file could not be read or a lookup
failed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

try:
    import yaml
    from packaging.requirements import InvalidRequirement, Requirement
    from packaging.specifiers import InvalidSpecifier, SpecifierSet
    from packaging.version import InvalidVersion, Version
except ImportError as exc:  # pragma: no cover - depends on the interpreter
    sys.exit(
        "error: missing dependency "
        f"({exc.name}). Run the script with .venv/bin/python."
    )

PYPI_URL = "https://pypi.org/pypi/{name}/json"
GALAXY_COLLECTION_URL = (
    "https://galaxy.ansible.com/api/v3/plugin/ansible/content/published/"
    "collections/index/{namespace}/{name}/versions/"
)
USER_AGENT = "azure-ansible-requirements-check/1.0"
DEFAULT_FILES = ("requirements.txt", "requirements.yml")
EXCLUDED_DIRS = {
    ".ansible",
    ".git",
    ".mypy_cache",
    ".myenv",
    ".tox",
    ".venv",
    "__pycache__",
    "collections",
    "node_modules",
    "site-packages",
    "venv",
}
SKIP_PIP_PREFIXES = (
    "-c",
    "--constraint",
    "-e",
    "--editable",
    "-f",
    "--find-links",
    "-i",
    "--index-url",
    "--extra-index-url",
    "--no-index",
    "--only-binary",
    "--prefer-binary",
    "--require-hashes",
    "--trusted-host",
)
ANCHOR_RE = re.compile(r"(==|~=|>=|<=|>|<|!=)\s*([^,\s]+)")
STATUS_COLORS = {
    "up to date": "32",
    "update available": "33",
    "constraint blocks update": "36",
    "newer than index": "35",
    "unpinned": "2",
    "not found": "31",
    "error": "31",
}


class LookupFailed(RuntimeError):
    """Raised when the version index cannot be queried."""


@dataclass
class Dependency:  # pylint: disable=too-many-instance-attributes
    """A dependency declared in a requirements file."""

    file: str
    kind: str
    name: str
    constraint: str = ""
    current: str | None = None
    latest: str | None = None
    max_allowed: str | None = None
    error: str = ""
    note: str = ""


def fetch_json(url: str, timeout: float) -> dict:
    """Return a JSON document from *url*."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise LookupFailed(f"network error: {reason}") from exc
    except json.JSONDecodeError as exc:
        raise LookupFailed(f"invalid JSON response: {exc}") from exc


def fetch_pypi_versions(name: str, timeout: float) -> list[Version]:
    """Return all non-yanked releases of a PyPI project."""
    url = PYPI_URL.format(name=urllib.parse.quote(name, safe=""))
    try:
        data = fetch_json(url, timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise LookupFailed("not found on PyPI") from exc
        raise LookupFailed(f"PyPI HTTP {exc.code}") from exc

    versions: list[Version] = []
    for raw_version, files in (data.get("releases") or {}).items():
        if files and all(item.get("yanked", False) for item in files):
            continue
        try:
            versions.append(Version(raw_version))
        except InvalidVersion:
            continue
    if not versions:
        raise LookupFailed("no releases found on PyPI")
    return versions


def fetch_galaxy_versions(name: str, timeout: float) -> list[Version]:
    """Return all published versions of an Ansible collection."""
    namespace, separator, collection = name.partition(".")
    if not separator or not namespace or not collection:
        raise LookupFailed("collection name must be namespace.collection")

    url = GALAXY_COLLECTION_URL.format(
        namespace=urllib.parse.quote(namespace, safe=""),
        name=urllib.parse.quote(collection, safe=""),
    )
    versions: list[Version] = []
    offset = 0
    while True:
        try:
            data = fetch_json(f"{url}?limit=100&offset={offset}", timeout)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise LookupFailed("not found on Galaxy") from exc
            raise LookupFailed(f"Galaxy HTTP {exc.code}") from exc

        page = data.get("data") or []
        for item in page:
            try:
                versions.append(Version(str(item["version"])))
            except (KeyError, InvalidVersion):
                continue

        offset += len(page)
        total = (data.get("meta") or {}).get("count", offset)
        if not page or offset >= total:
            break
    if not versions:
        raise LookupFailed("no versions found on Galaxy")
    return versions


def normalize_spec(spec: str) -> str:
    """Turn a Galaxy version string into a PEP 440 specifier set."""
    spec = (spec or "").strip()
    if spec in ("", "*"):
        return ""
    spec = re.sub(r"\s*,\s*", ",", spec)
    spec = re.sub(r"(?<=[<>=!~])\s+", "", spec)
    spec = re.sub(r"\s+(?=[<>=!~])", "", spec)
    spec = re.sub(r"\s+", ",", spec)
    if re.fullmatch(r"[vV]?\d[0-9A-Za-z.!+_-]*", spec):
        return f"=={spec}"
    return spec


def version_from_spec(spec: str) -> str | None:
    """Return the version a constraint is anchored to, if any."""
    if not spec or spec.startswith("@"):
        return None
    anchors = ANCHOR_RE.findall(spec)
    for operator in ("==", "~=", ">=", ">"):
        for candidate_operator, version in anchors:
            if candidate_operator == operator:
                return version
    return None


def parse_version(value: str | None) -> Version | None:
    """Parse a version and ignore wildcards used by ``==1.2.*`` pins."""
    if not value:
        return None
    text = value.strip()
    if text[:1] in ("v", "V"):
        text = text[1:]
    text = text.rstrip("*").rstrip(".")
    try:
        return Version(text)
    except InvalidVersion:
        return None


def logical_lines(text: str) -> Iterable[str]:
    """Yield requirement lines with continuations and comments removed."""
    buffer = ""
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.endswith("\\"):
            buffer += f"{line[:-1]} "
            continue
        buffer += line
        line = re.sub(r"\s+#.*$", "", buffer).strip()
        if line:
            yield line
        buffer = ""
    line = re.sub(r"\s+#.*$", "", buffer).strip()
    if line:
        yield line


def display_path(path: Path) -> str:
    """Return a path relative to the current directory when possible."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())


def included_requirement(line: str) -> Path | None:
    """Return the target of a ``-r``/``--requirement`` line."""
    match = re.match(r"^(?:-r|--requirement)(?:[=\s]+)(.+)$", line)
    if not match:
        return None
    target = match.group(1).strip().strip("'\"")
    return Path(target)


def parse_pip_file(
    path: Path,
    dependencies: list[Dependency],
    visited: set[Path],
) -> None:
    """Parse a pip requirements file into *dependencies*."""
    resolved = path.resolve()
    if resolved in visited:
        return
    visited.add(resolved)

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        dependencies.append(
            Dependency(
                file=display_path(path),
                kind="pip",
                name=str(path),
                error=f"cannot read file: {exc}",
            )
        )
        return

    name = display_path(path)
    for line in logical_lines(text):
        if line.startswith("#"):
            continue
        if line.startswith(("-r ", "--requirement ")) or line.startswith("--requirement="):
            include = included_requirement(line)
            if include is not None:
                parse_pip_file(path.parent / include, dependencies, visited)
            continue
        if line.startswith("-"):
            if line.startswith(SKIP_PIP_PREFIXES):
                continue
            dependencies.append(
                Dependency(
                    file=name,
                    kind="pip",
                    name=line,
                    error="unsupported pip option",
                )
            )
            continue

        line = re.sub(r"\s+--hash=\S+", "", line).strip()
        try:
            requirement = Requirement(line)
        except InvalidRequirement as exc:
            dependencies.append(
                Dependency(
                    file=name,
                    kind="pip",
                    name=line,
                    error=f"cannot parse requirement: {exc}",
                )
            )
            continue

        constraint = str(requirement.specifier)
        note = ""
        if requirement.url:
            constraint = f"@ {requirement.url}"
            note = "skipped (direct URL)"
        dependencies.append(
            Dependency(
                file=name,
                kind="pip",
                name=requirement.name,
                constraint=constraint,
                current=version_from_spec(constraint),
                note=note,
            )
        )


def parse_galaxy_file(  # pylint: disable=too-many-branches
    path: Path, dependencies: list[Dependency]
) -> None:
    """Parse an Ansible Galaxy requirements file into *dependencies*."""
    name = display_path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        dependencies.append(
            Dependency(
                file=name,
                kind="yaml",
                name=str(path),
                error=f"cannot read file: {exc}",
            )
        )
        return
    if not isinstance(data, dict):
        dependencies.append(
            Dependency(
                file=name,
                kind="yaml",
                name=str(path),
                error="top-level YAML value must be a mapping",
            )
        )
        return

    for item in data.get("collections") or []:
        if isinstance(item, str):
            collection_name = item.strip()
            constraint = ""
            source = ""
        elif isinstance(item, dict):
            collection_name = str(item.get("name") or "").strip()
            constraint = normalize_spec(str(item.get("version") or ""))
            source = str(item.get("source") or "").strip()
        else:
            dependencies.append(
                Dependency(
                    file=name,
                    kind="collection",
                    name=str(item),
                    error="invalid collection entry",
                )
            )
            continue
        if not collection_name:
            dependencies.append(
                Dependency(
                    file=name,
                    kind="collection",
                    name=str(item),
                    error="collection entry has no name",
                )
            )
            continue

        note = ""
        if source and "galaxy.ansible.com" not in source:
            note = "skipped (custom source)"
        dependencies.append(
            Dependency(
                file=name,
                kind="collection",
                name=collection_name,
                constraint=constraint,
                current=version_from_spec(constraint),
                note=note,
            )
        )

    for item in data.get("roles") or []:
        if isinstance(item, str):
            role_name = item.strip()
            constraint = ""
        elif isinstance(item, dict):
            role_name = str(item.get("name") or item.get("src") or "").strip()
            constraint = normalize_spec(str(item.get("version") or ""))
        else:
            dependencies.append(
                Dependency(
                    file=name,
                    kind="role",
                    name=str(item),
                    error="invalid role entry",
                )
            )
            continue
        if not role_name:
            dependencies.append(
                Dependency(
                    file=name,
                    kind="role",
                    name=str(item),
                    error="role entry has no name",
                )
            )
            continue
        dependencies.append(
            Dependency(
                file=name,
                kind="role",
                name=role_name,
                constraint=constraint,
                current=version_from_spec(constraint),
                note="skipped (role)",
            )
        )


def discover_files(  # pylint: disable=too-many-nested-blocks
    paths: Sequence[Path],
) -> list[Path]:
    """Collect requirements files from the given files and directories."""
    if paths:
        candidates: list[Path] = []
        for path in paths:
            if path.is_dir():
                for directory, dirnames, filenames in os.walk(path):
                    dirnames[:] = sorted(
                        name
                        for name in dirnames
                        if name not in EXCLUDED_DIRS and not name.startswith(".")
                    )
                    for filename in sorted(filenames):
                        candidate = Path(directory) / filename
                        if (
                            filename.startswith("requirements")
                            and candidate.suffix in {".txt", ".yml", ".yaml"}
                        ):
                            candidates.append(candidate)
            elif path.is_file():
                candidates.append(path)
            else:
                raise FileNotFoundError(path)
        return sorted(set(candidates))

    return [Path(name) for name in DEFAULT_FILES if Path(name).is_file()]


def parse_files(files: Sequence[Path]) -> list[Dependency]:
    """Parse all requirements files."""
    dependencies: list[Dependency] = []
    visited: set[Path] = set()
    for path in files:
        suffix = path.suffix.lower()
        if suffix == ".txt":
            parse_pip_file(path, dependencies, visited)
        elif suffix in {".yml", ".yaml"}:
            parse_galaxy_file(path, dependencies)
        else:
            dependencies.append(
                Dependency(
                    file=display_path(path),
                    kind="unknown",
                    name=str(path),
                    error="unsupported file type",
                )
            )
    return dependencies


def resolve_versions(  # pylint: disable=too-many-branches,too-many-locals
    dependencies: Sequence[Dependency],
    allow_prereleases: bool,
    timeout: float,
) -> None:
    """Fill latest/maximum versions for every supported dependency."""
    lookups: dict[tuple[str, str], Dependency] = {}
    for dependency in dependencies:
        if dependency.error or dependency.note:
            continue
        if dependency.kind not in {"pip", "collection"}:
            continue
        lookups.setdefault((dependency.kind, dependency.name), dependency)

    results: dict[tuple[str, str], list[Version] | LookupFailed] = {}
    if lookups:
        workers = min(8, len(lookups))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    fetch_pypi_versions if kind == "pip" else fetch_galaxy_versions,
                    name,
                    timeout,
                ): (kind, name)
                for kind, name in lookups
            }
            for future, key in futures.items():
                try:
                    results[key] = future.result()
                except LookupFailed as exc:
                    results[key] = exc
                except Exception as exc:  # pylint: disable=broad-except
                    results[key] = LookupFailed(str(exc))

    for dependency in dependencies:
        if dependency.error or dependency.note:
            continue
        if dependency.kind not in {"pip", "collection"}:
            dependency.note = "skipped (unsupported type)"
            continue

        result = results.get((dependency.kind, dependency.name))
        if result is None:
            dependency.error = "no lookup result"
            continue
        if isinstance(result, LookupFailed):
            dependency.error = str(result)
            continue

        candidates = [
            version
            for version in result
            if allow_prereleases or not version.is_prerelease
        ]
        if not candidates:
            dependency.note = "no stable release"
            continue

        dependency.latest = str(max(candidates))
        try:
            specifier = (
                SpecifierSet(dependency.constraint)
                if dependency.constraint
                else SpecifierSet()
            )
        except InvalidSpecifier as exc:
            dependency.error = f"invalid constraint: {exc}"
            continue

        allowed = [
            version
            for version in candidates
            if specifier.contains(version, prereleases=True)
        ]
        dependency.max_allowed = str(max(allowed)) if allowed else None


def dependency_status(  # pylint: disable=too-many-return-statements
    dependency: Dependency,
) -> str:
    """Return a short human readable status for one dependency."""
    if dependency.error:
        return "error"
    if dependency.note:
        return dependency.note
    if dependency.latest is None:
        return "not found"
    if dependency.current is None:
        return "unpinned"

    current = parse_version(dependency.current)
    latest = parse_version(dependency.latest)
    if current is None or latest is None:
        return "unknown"
    if current > latest:
        return "newer than index"
    if current < latest:
        allowed = parse_version(dependency.max_allowed)
        if allowed is not None and allowed <= current:
            return "constraint blocks update"
        return "update available"
    return "up to date"


def colorize(text: str, code: str, enabled: bool) -> str:
    """Wrap *text* in an ANSI color when *enabled*."""
    if not enabled:
        return text
    return f"\033[{code}m{text}\033[0m"


def render_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    statuses: Sequence[str],
    color_enabled: bool,
) -> str:
    """Render an aligned plain-text table."""
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def format_row(row: Sequence[str], status: str = "") -> str:
        cells = [
            row[index].ljust(widths[index]) for index in range(len(row) - 1)
        ]
        status_cell = row[-1].ljust(widths[-1])
        if status:
            status_cell = colorize(
                status_cell, STATUS_COLORS.get(status, "0"), color_enabled
            )
        cells.append(status_cell)
        return "  ".join(cells).rstrip()

    lines = [
        format_row(headers),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        format_row(row, status)
        for row, status in zip(rows, statuses)
    )
    return "\n".join(lines)


def row_for(dependency: Dependency, status: str) -> list[str]:
    """Build the table cells for one dependency."""
    return [
        dependency.file,
        dependency.kind,
        dependency.name,
        dependency.constraint or "-",
        dependency.current or "-",
        dependency.max_allowed or "-",
        dependency.latest or "-",
        status,
    ]


def build_parser() -> argparse.ArgumentParser:
    """Create the command line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Check versions in Python and Ansible requirements files and "
            "show the newest available release."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Without PATH arguments requirements.txt and requirements.yml in "
            "the current directory are checked.\n"
            "Exit codes: 0 = success, 1 = update found with --check, "
            "2 = error.\n\n"
            "Columns:\n"
            "  Constraint   version specifier from the file, e.g. ==2.20.1 "
            "or >=4.1.0\n"
            "  Current      version the specifier is anchored to\n"
            "  Max allowed  newest release satisfying the constraint\n"
            "  Latest       newest release overall, regardless of the "
            "constraint"
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        metavar="PATH",
        help="requirements file or directory to scan",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit with code 1 when an update is available",
    )
    parser.add_argument(
        "--pre",
        action="store_true",
        help="include pre-releases when looking for the newest version",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        metavar="SECONDS",
        help="HTTP timeout per request (default: 20)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable colored status output",
    )
    return parser


def main(  # pylint: disable=too-many-branches,too-many-locals
    argv: Sequence[str] | None = None,
) -> int:
    """Run the requirements check."""
    args = build_parser().parse_args(argv)

    try:
        files = discover_files(args.paths)
    except FileNotFoundError as exc:
        print(f"error: path does not exist: {exc}", file=sys.stderr)
        return 2

    if not files:
        print("error: no requirements files found", file=sys.stderr)
        return 2

    dependencies = parse_files(files)
    if not dependencies:
        print("No dependencies found.")
        return 0

    resolve_versions(dependencies, args.pre, args.timeout)

    dependencies.sort(key=lambda item: (item.file, item.kind, item.name.lower()))
    statuses = [dependency_status(item) for item in dependencies]
    rows = [
        row_for(dependency, status)
        for dependency, status in zip(dependencies, statuses)
    ]

    use_color = (
        not args.no_color
        and not os.environ.get("NO_COLOR")
        and sys.stdout.isatty()
    )
    print(
        render_table(
            (
                "File",
                "Type",
                "Package",
                "Constraint",
                "Current",
                "Max allowed",
                "Latest",
                "Status",
            ),
            rows,
            statuses,
            use_color,
        )
    )

    counts: dict[str, int] = {}
    for status in statuses:
        counts[status] = counts.get(status, 0) + 1
    summary = ", ".join(
        f"{count} {status}" for status, count in sorted(counts.items())
    )
    print(f"\n{len(dependencies)} dependencies checked: {summary}")

    failed = [item for item in dependencies if item.error]
    if failed:
        sys.stdout.flush()
        print("\nErrors:", file=sys.stderr)
        for dependency in failed:
            print(
                f"  {dependency.file}: {dependency.name}: {dependency.error}",
                file=sys.stderr,
            )
        return 2

    if args.check:
        outdated = {
            "update available",
            "constraint blocks update",
            "newer than index",
        }
        if any(status in outdated for status in statuses):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

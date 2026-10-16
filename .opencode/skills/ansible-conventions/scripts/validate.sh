#!/usr/bin/env bash
# Validate this repository:
#   1. ansible-playbook --syntax-check for one or every playbook
#   2. yamllint inventory playbooks roles
#   3. ansible-lint inventory playbooks roles
#
# Usage:
#   scripts/validate.sh                 # syntax-check every playbook
#   scripts/validate.sh create_vm.yml   # syntax-check one playbook
#
# Run from the repository root. yamllint and ansible-lint come from
# requirements.txt; activate the project virtualenv if they are not on PATH.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$repo_root"

status=0

# --- 1. Syntax check ---------------------------------------------------------

if [[ "$#" -gt 0 ]]; then
  playbooks=()
  for name in "$@"; do
    case "$name" in
      playbooks/*) playbooks+=("$name") ;;
      *) playbooks+=("playbooks/$name") ;;
    esac
  done
else
  shopt -s nullglob
  playbooks=(playbooks/*.yml)
fi

if [[ "${#playbooks[@]}" -eq 0 ]]; then
  echo "No playbooks found in playbooks/." >&2
  exit 1
fi

for playbook in "${playbooks[@]}"; do
  echo "==> syntax-check $playbook"
  if ! ansible-playbook "$playbook" --syntax-check; then
    status=1
  fi
done

# --- 2. yamllint --------------------------------------------------------------

echo "==> yamllint inventory playbooks roles"
if command -v yamllint >/dev/null 2>&1; then
  if ! yamllint inventory playbooks roles; then
    status=1
  fi
else
  echo "yamllint not found on PATH, skipping (install with: pip install -r requirements.txt)." >&2
  status=1
fi

# --- 3. ansible-lint ----------------------------------------------------------

echo "==> ansible-lint inventory playbooks roles"
if command -v ansible-lint >/dev/null 2>&1; then
  if ! ansible-lint inventory playbooks roles; then
    status=1
  fi
else
  echo "ansible-lint not found on PATH, skipping (install with: pip install -r requirements.txt)." >&2
  status=1
fi

# --- Summary ------------------------------------------------------------------

if [[ "$status" -eq 0 ]]; then
  echo "==> validate: OK"
else
  echo "==> validate: FAILED - fix the findings above." >&2
fi

exit "$status"

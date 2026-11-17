#!/usr/bin/env bash
# Deliberately omit errexit so the aggregate reports every failing target before
# exiting non-zero.
set -uo pipefail

# Sync the environment ONCE per aggregate pass, then run every target with
# UV_NO_SYNC=1 so per-target `uv run` invocations skip redundant re-syncs.
if ! uv sync --all-groups; then
    echo "ERROR: up-front 'uv sync --all-groups' failed; aborting the check aggregate" >&2
    exit 1
fi
export UV_NO_SYNC=1

skip_targets=("$@")
repo_root="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
aggregate_targets() {
    awk '
        !marker && index($0, "LIVESPEC_AGGREGATE_TARGETS") {
            marker = 1
            next
        }
        marker && !in_targets && $0 ~ /^[[:space:]]*targets=\([[:space:]]*$/ {
            in_targets = 1
            next
        }
        in_targets && $0 ~ /^[[:space:]]*\)[[:space:]]*$/ {
            exit
        }
        in_targets {
            line = $0
            sub(/[[:space:]]*#.*/, "", line)
            sub(/^[[:space:]]+/, "", line)
            sub(/[[:space:]]+$/, "", line)
            if (line ~ /^check-/) {
                print line
            }
        }
    ' "$repo_root/justfile"
}

if [[ ${1:-} == "--list-targets" ]]; then
    aggregate_targets
    exit 0
fi

mapfile -t targets < <(aggregate_targets)
if [[ ${#targets[@]} -eq 0 ]]; then
    echo "ERROR: justfile LIVESPEC_AGGREGATE_TARGETS declares no check aggregate members" >&2
    exit 1
fi

# Each member declares whether the committed tree alone decides its verdict.
# Refuse before dispatch when one does not: an undeclared member is safely
# treated as world-reading by the token resolver, but without this refusal the
# token's saving can silently shrink whenever a new aggregate member is added.
if ! undeclared_members=$(uv run python -m livespec_dev_tooling.green_token \
    undeclared "${targets[@]}"); then
    printf 'ERROR: these check aggregate members carry no purity declaration: %s\n' \
        "${undeclared_members//$'\n'/ }" >&2
    printf 'Declare a shipped check with CHECK_PURITY or a repository-private member with a # purity: tree-pure or # purity: world-reading annotation in check-targets.txt.\n' >&2
    exit 1
fi

failed=()
ran=0
for target in "${targets[@]}"; do
    skip_this=0
    for skip_target in "${skip_targets[@]}"; do
        if [[ "$target" == "$skip_target" ]]; then
            skip_this=1
            break
        fi
    done
    if [[ "$skip_this" -eq 1 ]]; then
        printf '\n::: just %s (skipped)\n' "$target"
        continue
    fi
    ran=$((ran + 1))
    printf '\n::: just %s\n' "$target"
    if ! just "$target"; then
        failed+=("$target")
    fi
done

if [[ ${#failed[@]} -gt 0 ]]; then
    printf '\nFailed targets (%d):\n' "${#failed[@]}"
    printf '  - %s\n' "${failed[@]}"
    exit 1
fi
printf '\nAll %d targets passed.\n' "${#targets[@]}"
if [[ ${#skip_targets[@]} -eq 0 ]]; then
    uv run python -m livespec_dev_tooling.green_token write || true
fi

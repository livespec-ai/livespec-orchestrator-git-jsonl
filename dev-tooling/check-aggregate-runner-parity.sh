#!/usr/bin/env bash
set -euo pipefail

heredoc_targets() {
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
    ' justfile
}

contains_target() {
    local wanted="$1"
    shift
    local target
    for target in "$@"; do
        if [[ "$target" == "$wanted" ]]; then
            return 0
        fi
    done
    return 1
}

mapfile -t declared < <(heredoc_targets)
mapfile -t runner < <(bash dev-tooling/just-check.sh --list-targets)

if [[ ${#declared[@]} -eq 0 ]]; then
    echo "ERROR: justfile LIVESPEC_AGGREGATE_TARGETS declares no check aggregate members" >&2
    exit 1
fi

failed=0
for target in "${declared[@]}"; do
    if ! contains_target "$target" "${runner[@]}"; then
        printf 'ERROR: runner omits aggregate target: %s\n' "$target" >&2
        failed=1
    fi
done
for target in "${runner[@]}"; do
    if ! contains_target "$target" "${declared[@]}"; then
        printf 'ERROR: runner adds aggregate target absent from heredoc: %s\n' "$target" >&2
        failed=1
    fi
done
for index in "${!declared[@]}"; do
    observed="${runner[index]:-<missing>}"
    if [[ "${declared[index]}" != "$observed" ]]; then
        printf 'ERROR: runner target differs at index %s: heredoc=%s runner=%s\n' \
            "$index" "${declared[index]}" "$observed" >&2
        failed=1
    fi
done
for index in "${!runner[@]}"; do
    if [[ "$index" -ge "${#declared[@]}" ]]; then
        printf 'ERROR: runner has extra aggregate target at index %s: %s\n' \
            "$index" "${runner[index]}" >&2
        failed=1
    fi
done
exit "$failed"

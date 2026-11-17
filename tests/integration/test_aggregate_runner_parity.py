"""Integration coverage for aggregate runner target parity."""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

__all__: list[str] = []

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_executable(*, path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_aggregate_runner_parity_names_each_differing_target(tmp_path: Path) -> None:
    """The parity check reports every member absent from either target source."""
    tooling = tmp_path / "dev-tooling"
    tooling.mkdir()
    parity = tooling / "check-aggregate-runner-parity.sh"
    parity.write_text(
        (_REPO_ROOT / "dev-tooling" / "check-aggregate-runner-parity.sh").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    _write_executable(
        path=tooling / "just-check.sh",
        body="#!/usr/bin/env bash\nprintf '%s\\n' check-runner-only\n",
    )
    (tmp_path / "justfile").write_text(
        """check:
    : <<'LIVESPEC_AGGREGATE_TARGETS'
    targets=(
        check-heredoc-only
    )
    LIVESPEC_AGGREGATE_TARGETS
""",
        encoding="utf-8",
    )

    completed = subprocess.run(
        ["bash", str(parity)],
        cwd=tmp_path,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    assert "check-heredoc-only" in completed.stderr
    assert "check-runner-only" in completed.stderr

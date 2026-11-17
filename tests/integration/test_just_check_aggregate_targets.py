"""Acceptance controls for the local ``just check`` aggregate runner."""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

__all__: list[str] = []

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TARGETS = re.compile(
    r"LIVESPEC_AGGREGATE_TARGETS'\n    targets=\(\n(?P<targets>.*?)^    \)\n"
    r"    LIVESPEC_AGGREGATE_TARGETS",
    re.MULTILINE | re.DOTALL,
)


def _write_executable(*, path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _aggregate_targets(*, justfile: Path) -> list[str]:
    match = _TARGETS.search(justfile.read_text(encoding="utf-8"))
    assert match is not None
    return [
        line.strip()
        for line in match.group("targets").splitlines()
        if line.strip().startswith("check-")
    ]


def test_local_aggregate_runner_reads_the_justfile_target_heredoc(tmp_path: Path) -> None:
    """The justfile registry is the runner's sole aggregate target source."""
    root = tmp_path / "repository"
    tooling = root / "dev-tooling"
    tooling.mkdir(parents=True)
    runner = tooling / "just-check.sh"
    shutil.copy2(_REPO_ROOT / "dev-tooling" / "just-check.sh", runner)

    justfile = root / "justfile"
    justfile.write_text(
        (_REPO_ROOT / "justfile")
        .read_text(encoding="utf-8")
        .replace(
            "        check-format\n", "        check-fixture-from-heredoc\n        check-format\n"
        ),
        encoding="utf-8",
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    invoked = tmp_path / "just.log"
    _write_executable(
        path=bin_dir / "uv",
        body="""#!/usr/bin/env bash
case "$*" in
  "sync --all-groups"|*"green_token undeclared"*|*"green_token write"*) exit 0 ;;
  *) echo "unexpected uv invocation: $*" >&2; exit 99 ;;
esac
""",
    )
    _write_executable(
        path=bin_dir / "just",
        body=f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "{invoked}"
exit 0
""",
    )
    bash = shutil.which("bash")
    assert bash is not None
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    completed = subprocess.run(
        [bash, str(runner)],
        cwd=tmp_path,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    invoked_targets = [
        target
        for target in invoked.read_text(encoding="utf-8").splitlines()
        if target.startswith("check-")
    ]
    assert invoked_targets == _aggregate_targets(justfile=justfile)
    assert "check-branch-protection" not in invoked_targets

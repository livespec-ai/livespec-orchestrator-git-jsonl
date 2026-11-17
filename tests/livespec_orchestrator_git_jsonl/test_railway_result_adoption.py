"""Regression coverage for the public-API Result-railway adoption."""

from pathlib import Path

import livespec_orchestrator_git_jsonl.checks.work_item_merge_evidence as merge_check
import livespec_orchestrator_git_jsonl.migration.merge_evidence_backfill as backfill
import pytest
from returns.io import IO, IOFailure


def test_check_canonical_branch_helper_uses_explicit_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An explicit CLI flag remains outside the fallible git-resolution boundary."""

    def _unexpected_resolution(*, repo_dir: Path) -> object:
        _ = repo_dir
        raise AssertionError("check resolution must not run")

    monkeypatch.setattr(merge_check, "resolve_canonical_branch", _unexpected_resolution)
    monkeypatch.chdir(tmp_path)
    assert merge_check.main(argv=["--canonical-branch", "trunk"]) == 0
    assert "absent — skipped" in capsys.readouterr().out


def test_backfill_canonical_branch_helper_uses_explicit_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The migration CLI keeps an explicit branch outside its I/O boundary too."""

    def _unexpected_resolution(*, repo_dir: Path) -> object:
        _ = repo_dir
        raise AssertionError("backfill resolution must not run")

    monkeypatch.setattr(backfill, "resolve_canonical_branch", _unexpected_resolution)
    target = tmp_path / "work-items.jsonl"
    _ = target.write_text("", encoding="utf-8")
    assert (
        backfill.main(argv=["--path", str(target), "--canonical-branch", "trunk", "--dry-run"]) == 0
    )
    assert "would apply" in capsys.readouterr().out


def test_check_canonical_branch_helper_reports_iofailure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The check CLI renders a Result failure rather than treating it as a branch."""

    def _failed_resolution(*, repo_dir: Path) -> IOFailure[IO[OSError]]:
        _ = repo_dir
        return IOFailure(IO(OSError("git unavailable")))

    monkeypatch.setattr(merge_check, "resolve_canonical_branch", _failed_resolution)
    monkeypatch.chdir(tmp_path)
    assert merge_check.main(argv=[]) == 1
    captured = capsys.readouterr()
    assert "unable to resolve canonical branch" in captured.out


def test_backfill_canonical_branch_helper_reports_iofailure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The migration CLI renders a Result failure rather than treating it as a branch."""

    def _failed_resolution(*, repo_dir: Path) -> IOFailure[IO[OSError]]:
        _ = repo_dir
        return IOFailure(IO(OSError("git unavailable")))

    monkeypatch.setattr(backfill, "resolve_canonical_branch", _failed_resolution)
    target = tmp_path / "work-items.jsonl"
    _ = target.write_text("", encoding="utf-8")
    assert backfill.main(argv=["--path", str(target)]) == 1
    assert "unable to resolve canonical branch" in capsys.readouterr().err

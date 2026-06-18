"""Regression tests for rollback checkpoint diff symlink disclosure."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from api import rollback
import api.workspace as workspace_mod


def _commit_checkpoint_file(repo: Path, rel: str, content: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", rel], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "checkpoint"], check=True)


def _init_checkpoint(tmp_path, monkeypatch):
    hermes_home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    hermes_home.mkdir()
    workspace.mkdir()
    ws_hash = rollback._workspace_hash(str(workspace.resolve()))
    checkpoint = "abc123"
    ckpt_dir = hermes_home / "checkpoints" / ws_hash / checkpoint
    ckpt_dir.mkdir(parents=True)
    subprocess.run(["git", "-C", str(ckpt_dir), "init"], check=True)
    subprocess.run(["git", "-C", str(ckpt_dir), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(ckpt_dir), "config", "user.name", "Test"], check=True)
    monkeypatch.setattr(rollback, "_hermes_home", lambda: hermes_home)
    monkeypatch.setattr(workspace_mod, "load_workspaces", lambda: [{"path": str(workspace)}])
    return workspace, ckpt_dir, checkpoint


def test_checkpoint_diff_does_not_follow_checkpoint_symlink(tmp_path, monkeypatch):
    workspace, ckpt_dir, checkpoint = _init_checkpoint(tmp_path, monkeypatch)
    secret = tmp_path / "outside-secret.txt"
    secret.write_text("SAFE_SECRET_MARKER_SHOULD_NOT_APPEAR\n", encoding="utf-8")

    os.symlink(secret, ckpt_dir / "leak.txt")
    subprocess.run(["git", "-C", str(ckpt_dir), "add", "leak.txt"], check=True)
    subprocess.run(["git", "-C", str(ckpt_dir), "commit", "-m", "checkpoint"], check=True)

    result = rollback.get_checkpoint_diff(str(workspace), checkpoint)

    assert result["files_changed"] == []
    assert "SAFE_SECRET_MARKER_SHOULD_NOT_APPEAR" not in result["diff"]
    assert "leak.txt" not in result["diff"]


def test_checkpoint_diff_does_not_follow_workspace_symlink_escape(tmp_path, monkeypatch):
    workspace, ckpt_dir, checkpoint = _init_checkpoint(tmp_path, monkeypatch)
    _commit_checkpoint_file(ckpt_dir, "leak.txt", "checkpoint content\n")
    secret = tmp_path / "outside-secret.txt"
    secret.write_text("WORKSPACE_SECRET_MARKER_SHOULD_NOT_APPEAR\n", encoding="utf-8")
    os.symlink(secret, workspace / "leak.txt")

    result = rollback.get_checkpoint_diff(str(workspace), checkpoint)

    assert "WORKSPACE_SECRET_MARKER_SHOULD_NOT_APPEAR" not in result["diff"]
    assert "checkpoint content" in result["diff"]


def test_restore_checkpoint_skips_checkpoint_symlink_sources(tmp_path, monkeypatch):
    workspace, ckpt_dir, checkpoint = _init_checkpoint(tmp_path, monkeypatch)
    secret = tmp_path / "outside-secret.txt"
    secret.write_text("RESTORE_SECRET_MARKER_SHOULD_NOT_COPY\n", encoding="utf-8")

    os.symlink(secret, ckpt_dir / "leak.txt")
    subprocess.run(["git", "-C", str(ckpt_dir), "add", "leak.txt"], check=True)
    subprocess.run(["git", "-C", str(ckpt_dir), "commit", "-m", "checkpoint"], check=True)

    result = rollback.restore_checkpoint(str(workspace), checkpoint)

    assert result["files_restored"] == []
    assert not (workspace / "leak.txt").exists()
    assert "RESTORE_SECRET_MARKER_SHOULD_NOT_COPY" not in "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in workspace.rglob("*")
        if p.is_file()
    )


def test_restore_checkpoint_reads_git_blob_after_worktree_symlink_swap(tmp_path, monkeypatch):
    workspace, ckpt_dir, checkpoint = _init_checkpoint(tmp_path, monkeypatch)
    _commit_checkpoint_file(ckpt_dir, "file.txt", "checkpoint blob content\n")
    secret = tmp_path / "outside-secret.txt"
    secret.write_text("POST_COMMIT_SECRET_MARKER_SHOULD_NOT_COPY\n", encoding="utf-8")

    (ckpt_dir / "file.txt").unlink()
    os.symlink(secret, ckpt_dir / "file.txt")

    result = rollback.restore_checkpoint(str(workspace), checkpoint)

    assert result["files_restored"] == ["file.txt"]
    assert (workspace / "file.txt").read_text(encoding="utf-8") == "checkpoint blob content\n"
    assert "POST_COMMIT_SECRET_MARKER_SHOULD_NOT_COPY" not in (workspace / "file.txt").read_text(
        encoding="utf-8"
    )

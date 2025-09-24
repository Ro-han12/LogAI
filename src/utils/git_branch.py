"""
Utilities for preparing a post-merge branch and pushing it to a remote.

Supports two strategies:
- Merge a source ref (branch/SHA) into a base branch
- Apply a patch file (e.g., PR patch URL) onto a base branch

Requires: GitPython
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from git import Repo, GitCommandError, Remote


@dataclass
class BranchPrepResult:
    """Result of preparing and pushing a post-merge branch."""
    repository_path: str
    new_branch: str
    remote_name: str
    remote_ref: str
    pushed: bool


def _ensure_remote(repo: Repo, remote_name: str, remote_url: Optional[str]) -> Remote:
    """Ensure a remote exists, creating/updating it if a URL is provided."""
    try:
        remote = repo.remote(remote_name)
        if remote_url and remote.urls and remote_url not in list(remote.urls):
            remote.set_url(remote_url)
        return remote
    except ValueError:
        if not remote_url:
            raise ValueError(f"Remote '{remote_name}' not found and no URL provided to create it.")
        return repo.create_remote(remote_name, remote_url)


def _checkout_new_branch_from_base(repo: Repo, base_branch: str, new_branch: str) -> None:
    """Checkout base and create new branch from it, resetting worktree."""
    repo.git.fetch("--all")
    repo.git.checkout(base_branch)
    # Create or reset branch
    existing = new_branch in repo.branches
    if existing:
        repo.git.branch("-D", new_branch)
    repo.git.checkout("-b", new_branch)


def _merge_source_ref(repo: Repo, source_ref: str, commit_message: Optional[str]) -> None:
    """Merge a source ref into the current HEAD (no fast-forward to preserve a merge commit)."""
    try:
        repo.git.merge("--no-ff", "--no-edit", source_ref) if commit_message is None else repo.git.merge("--no-ff", "-m", commit_message, source_ref)
    except GitCommandError as e:
        # If merge conflicts arise, abort and raise
        try:
            repo.git.merge("--abort")
        except Exception:
            pass
        raise e


def _apply_patch(repo: Repo, patch_bytes: bytes, commit_message: Optional[str]) -> None:
    """Apply a patch onto the current HEAD and commit it.

    Attempts `git am` first (for mail-formatted patches). Falls back to `git apply` + manual commit.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        patch_path = os.path.join(tmpdir, "change.patch")
        with open(patch_path, "wb") as f:
            f.write(patch_bytes)

        # Try git am
        try:
            repo.git.am(patch_path)
            return
        except GitCommandError:
            # Fallback: apply to index and commit
            try:
                repo.git.apply("--index", patch_path)
                # Commit with provided message or a default
                msg = commit_message or "Apply patch"
                repo.index.commit(msg)
            except GitCommandError as e:
                # Cleanup in case am left state
                try:
                    repo.git.am("--abort")
                except Exception:
                    pass
                raise e


def prepare_and_push_post_merge_branch(
    repository_path: str,
    base_branch: str,
    new_branch: str,
    *,
    source_ref: Optional[str] = None,
    patch_bytes: Optional[bytes] = None,
    remote_name: str = "origin",
    remote_url: Optional[str] = None,
    push_force: bool = False,
    commit_message: Optional[str] = None,
) -> BranchPrepResult:
    """Create a branch representing post-merge state and push it.

    One of `source_ref` or `patch_bytes` must be provided.
    """
    if not source_ref and not patch_bytes:
        raise ValueError("Either source_ref or patch_bytes must be provided.")

    repo = Repo(repository_path)

    # Ensure remote
    remote = _ensure_remote(repo, remote_name, remote_url)

    # Make sure base exists locally (fetch first)
    try:
        repo.git.fetch(remote_name, base_branch)
    except GitCommandError:
        # If fetch fails, continue; branch may be local-only
        pass

    _checkout_new_branch_from_base(repo, base_branch, new_branch)

    # Apply change
    if source_ref:
        # Ensure we have the source ref locally
        try:
            repo.git.fetch(remote_name, source_ref)
        except GitCommandError:
            # Non-fatal; source_ref could be local or a SHA already present
            pass
        _merge_source_ref(repo, source_ref, commit_message)
    else:
        _apply_patch(repo, patch_bytes or b"", commit_message)

    # Push branch
    push_args = [f"{new_branch}:{new_branch}"]
    if push_force:
        remote.push(push_args, force=True)
    else:
        remote.push(push_args)

    return BranchPrepResult(
        repository_path=repository_path,
        new_branch=new_branch,
        remote_name=remote.name,
        remote_ref=f"{remote.name}/{new_branch}",
        pushed=True,
    )



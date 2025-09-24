"""
Tests for git branch preparation utilities.
"""

import os
import tempfile
from pathlib import Path

import pytest
from git import Repo

from src.utils.git_branch import prepare_and_push_post_merge_branch


def _init_bare_repo(tmpdir: str) -> str:
    bare_path = os.path.join(tmpdir, "remote.git")
    Repo.init(bare_path, bare=True)
    return bare_path


def _init_work_repo(tmpdir: str, bare_url: str) -> Repo:
    work_path = os.path.join(tmpdir, "work")
    repo = Repo.init(work_path)
    # create initial commit on main
    (Path(work_path) / "README.md").write_text("hello\n")
    repo.index.add(["README.md"])
    repo.index.commit("init")
    repo.create_head("main")
    repo.git.checkout("main")
    repo.create_remote("origin", bare_url)
    repo.git.push("-u", "origin", "main")
    return repo


def _create_feature_commit(repo: Repo, filename: str, content: str, branch: str) -> str:
    repo.git.checkout("-b", branch)
    Path(repo.working_tree_dir, filename).write_text(content)
    repo.index.add([filename])
    commit = repo.index.commit(f"add {filename}")
    return commit.hexsha


def test_prepare_and_push_post_merge_branch_merge_ref(tmp_path):
    tmpdir = str(tmp_path)
    bare = _init_bare_repo(tmpdir)
    repo = _init_work_repo(tmpdir, bare)

    # Create feature branch and push
    feature_sha = _create_feature_commit(repo, "feature.txt", "data\n", "feature-1")
    repo.git.push("-u", "origin", "feature-1")

    # Prepare post-merge branch by merging feature into main
    result = prepare_and_push_post_merge_branch(
        repository_path=repo.working_tree_dir,
        base_branch="main",
        new_branch="post-merge/feature-1",
        source_ref="origin/feature-1",
        remote_name="origin",
        push_force=False,
    )

    assert result.pushed is True
    # Verify remote has the branch
    remote_heads = Repo(bare).refs
    assert any(ref.name.endswith("post-merge/feature-1") for ref in remote_heads)


def test_prepare_and_push_post_merge_branch_apply_patch(tmp_path):
    tmpdir = str(tmp_path)
    bare = _init_bare_repo(tmpdir)
    repo = _init_work_repo(tmpdir, bare)

    # Create a patch by adding a file and generating diff
    repo.git.checkout("-b", "tmp-change")
    Path(repo.working_tree_dir, "patch.txt").write_text("patch\n")
    repo.index.add(["patch.txt"])
    commit = repo.index.commit("add patch.txt")
    patch_bytes = repo.git.format_patch("-1", commit.hexsha, stdout=True).encode()

    # Reset back to main before applying patch via utility
    repo.git.checkout("main")

    result = prepare_and_push_post_merge_branch(
        repository_path=repo.working_tree_dir,
        base_branch="main",
        new_branch="post-merge/patch",
        patch_bytes=patch_bytes,
        remote_name="origin",
        push_force=False,
    )

    assert result.pushed is True
    remote_heads = Repo(bare).refs
    assert any(ref.name.endswith("post-merge/patch") for ref in remote_heads)



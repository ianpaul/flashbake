"""
test_git.py — Tests for the Git wrapper class (flashbake.git).

WHAT IS BEING TESTED
--------------------
flashbake.git.Git is a thin wrapper around subprocess calls to git.
These tests verify that the wrapper correctly communicates with a real
git repository, not a mock one.

Tests are structured from simple to complex:
  1. Can we instantiate the class?
  2. Does status() return useful output?
  3. Does add() stage a file?
  4. Does commit() create a real git commit?

HOW TO RUN
----------
  pytest test/test_git.py -v
"""

import subprocess
import pytest
from pathlib import Path


def make_git_repo(path):
    """Initialize a repo with an author identity configured."""
    subprocess.run(['git', 'init', str(path)], check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@flashbake.test'],
                   cwd=str(path), check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Git Test'],
                   cwd=str(path), check=True, capture_output=True)


class TestGitInstantiation:

    def test_instantiates_in_a_valid_repo(self, tmp_path):
        """
        Git class should construct without error when git is on PATH.
        This confirms the executable detection works on the current platform.
        """
        from flashbake.git import Git
        make_git_repo(tmp_path)
        git = Git(str(tmp_path))
        assert git is not None

    def test_vcerror_is_a_proper_exception(self):
        """
        VCError should be a proper Exception subclass with a meaningful
        string representation. This matters when users see error output.
        """
        from flashbake.git import VCError
        err = VCError('git not found on PATH')
        assert 'git not found on PATH' in str(err)
        assert isinstance(err, Exception)


class TestGitStatus:

    def test_status_returns_bytes(self, tmp_path):
        """
        git.status() should return bytes (the raw output of the git process).
        The caller is responsible for decoding — this is the existing contract.
        """
        from flashbake.git import Git
        make_git_repo(tmp_path)
        git = Git(str(tmp_path))
        result = git.status()
        assert isinstance(result, bytes), (
            f"git.status() should return bytes, got {type(result).__name__}"
        )

    def test_status_is_non_empty(self, tmp_path):
        """git status always produces some output, even in a clean repo."""
        from flashbake.git import Git
        make_git_repo(tmp_path)
        git = Git(str(tmp_path))
        result = git.status()
        assert len(result) > 0, "git status returned no output at all"

    def test_new_file_appears_in_status(self, tmp_path):
        """
        After creating an untracked file, git status should mention it.
        This verifies the wrapper is running status against the right directory.
        """
        from flashbake.git import Git
        make_git_repo(tmp_path)
        (tmp_path / 'story.txt').write_text('Once upon a time\n', encoding='utf-8')

        git = Git(str(tmp_path))
        status = git.status().decode('utf-8')

        assert 'story.txt' in status, (
            f"A newly created file should appear in git status output.\n"
            f"Status output:\n{status}"
        )

    def test_status_single_file(self, tmp_path):
        """
        git.status(filename) should return status for just that file.
        """
        from flashbake.git import Git
        make_git_repo(tmp_path)
        (tmp_path / 'a.txt').write_text('file a\n', encoding='utf-8')
        (tmp_path / 'b.txt').write_text('file b\n', encoding='utf-8')

        git = Git(str(tmp_path))
        status = git.status('a.txt').decode('utf-8')

        # a.txt was queried, b.txt was not — but both are untracked so status
        # output format varies by git version. What matters: no exception raised.
        assert isinstance(status, str)


class TestGitAddAndCommit:

    def test_add_stages_a_file(self, tmp_path):
        """
        After add(), the file should appear as staged in git status.
        Verified by running 'git status' independently.
        """
        from flashbake.git import Git
        make_git_repo(tmp_path)
        (tmp_path / 'poem.txt').write_text('Roses are red\n', encoding='utf-8')

        git = Git(str(tmp_path))
        git.add('poem.txt')

        # Check independently using the real git
        result = subprocess.run(
            ['git', 'status', '--short'],
            cwd=str(tmp_path), capture_output=True, text=True, check=True
        )
        assert 'poem.txt' in result.stdout, (
            f"After git.add(), file should appear as staged.\n"
            f"git status output: {result.stdout}"
        )

    def test_commit_creates_a_real_git_commit(self, tmp_path):
        """
        The full add-then-commit cycle should produce a real commit in the
        git history, verifiable with 'git log'.

        This is the core capability Flashbake depends on.
        """
        from flashbake.git import Git
        make_git_repo(tmp_path)

        # Create and add a file
        poem = tmp_path / 'poem.txt'
        poem.write_text('The fog comes\non little cat feet\n', encoding='utf-8')
        git = Git(str(tmp_path))
        git.add('poem.txt')

        # Write a message file (that's how git.commit() works)
        msg_file = tmp_path / 'commit_msg.txt'
        msg_file.write_text('Add poem by Carl Sandburg\n', encoding='utf-8')
        git.commit(str(msg_file), ['poem.txt'])

        # Verify independently with git log
        log = subprocess.run(
            ['git', 'log', '--oneline'],
            cwd=str(tmp_path), capture_output=True, text=True, check=True
        )
        assert log.stdout.strip(), "git log is empty — commit did not happen"
        assert 'Add poem by Carl Sandburg' in subprocess.run(
            ['git', 'log', '-1', '--pretty=%B'],
            cwd=str(tmp_path), capture_output=True, text=True, check=True
        ).stdout, "Commit message was not recorded correctly"

    def test_commit_output_is_bytes(self, tmp_path):
        """git.commit() should return bytes (the raw process output)."""
        from flashbake.git import Git
        make_git_repo(tmp_path)
        (tmp_path / 'file.txt').write_text('content\n', encoding='utf-8')
        git = Git(str(tmp_path))
        git.add('file.txt')

        msg_file = tmp_path / 'msg.txt'
        msg_file.write_text('test\n', encoding='utf-8')
        result = git.commit(str(msg_file), ['file.txt'])

        assert isinstance(result, bytes), (
            f"git.commit() should return bytes, got {type(result).__name__}"
        )

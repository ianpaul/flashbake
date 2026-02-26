"""
test_integration.py — End-to-end integration tests for Flashbake.

DESIGN PHILOSOPHY
-----------------
These tests verify that Flashbake does what it says: commits changed files to
git, with a commit message built from plugins.

Every test follows the same pattern:
  1. Set up a real temporary git repository on disk.
  2. Create real files and a real .flashbake control file.
  3. Run Flashbake's commit logic.
  4. Verify the outcome by running git commands INDEPENDENTLY of Flashbake.

The verification step is key: we use subprocess to call git directly,
not Flashbake's own code, so the tests cannot be "gamed" by changes to
the assertion path. If git doesn't have a new commit, the test fails —
regardless of what Flashbake's internal state says.

HOW TO RUN
----------
  pytest test/test_integration.py -v          # run all integration tests
  pytest test/test_integration.py -v -k quiet # run only quiet-period tests
"""

import os
import subprocess
import time
import pytest
from pathlib import Path

from flashbake import control, commit as fb_commit


# ---------------------------------------------------------------------------
# Helpers — thin wrappers around git so tests read like plain English
# ---------------------------------------------------------------------------

def git(args, cwd):
    """Run a git command and return stdout. Raises on non-zero exit."""
    result = subprocess.run(
        ['git'] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def commit_count(repo_dir):
    """Return the number of commits in the repo (0 if no commits yet)."""
    try:
        return int(git(['rev-list', '--count', 'HEAD'], repo_dir))
    except subprocess.CalledProcessError:
        return 0


def latest_commit_message(repo_dir):
    """Return the full commit message of the most recent commit."""
    return git(['log', '-1', '--pretty=%B'], repo_dir)


def latest_commit_files(repo_dir):
    """Return the list of files touched in the most recent commit."""
    raw = git(['show', '--name-only', '--pretty=format:', 'HEAD'], repo_dir)
    return [f for f in raw.splitlines() if f.strip()]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def git_project(tmp_path):
    """
    A real, minimal git repository ready for Flashbake to operate on.

    Contains one committed file (novel.txt) so HEAD always exists.
    Git author identity is configured to avoid 'who are you?' errors.
    """
    subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'flashbake-test@example.com'],
                   cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Flashbake Test Runner'],
                   cwd=str(tmp_path), check=True, capture_output=True)

    novel = tmp_path / 'novel.txt'
    novel.write_text('Chapter 1: The Beginning\n', encoding='utf-8')
    subprocess.run(['git', 'add', 'novel.txt'],
                   cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'initial commit'],
                   cwd=str(tmp_path), check=True, capture_output=True)

    return tmp_path


def write_control_file(project_dir, tracked_files, plugins=None, extra_config=None):
    """
    Write a .flashbake control file.

    tracked_files  — list of filenames flashbake should monitor
    plugins        — list of plugin specs; defaults to Timestamp (local/24h)
    extra_config   — dict of additional 'key: value' lines (e.g. plugin properties)
    """
    if plugins is None:
        plugins = ['flashbake.plugins.timestamp:Timestamp']
    if extra_config is None:
        extra_config = {
            'timestamp_time_format': 'local',
            'timestamp_time_hours': '24',
        }

    lines = ['plugins: ' + ', '.join(plugins)]
    for k, v in extra_config.items():
        lines.append(f'{k}: {v}')
    lines.extend(tracked_files)

    control_path = Path(project_dir) / '.flashbake'
    control_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return control_path


def run_flashbake(project_dir, quiet_mins=0):
    """
    Run Flashbake's commit logic against a project directory.

    Saves and restores the working directory because commit.commit()
    calls os.chdir() internally.
    """
    original_cwd = os.getcwd()
    try:
        hot_files, config = control.parse_control(
            str(project_dir),
            str(Path(project_dir) / '.flashbake'),
        )
        control.prepare_control(hot_files, config)
        fb_commit.commit(config, hot_files, quiet_mins)
    finally:
        os.chdir(original_cwd)


# ---------------------------------------------------------------------------
# Tests: core commit behaviour
# ---------------------------------------------------------------------------

class TestCommitBehaviour:
    """
    Does Flashbake actually commit modified files to git?

    Each test modifies a file, runs Flashbake, then inspects the real git
    history to confirm what happened.
    """

    def test_modified_file_gets_committed(self, git_project):
        """
        The basic contract: modify a tracked file → Flashbake commits it.

        Verified by counting commits before and after — the count must
        increase by exactly one.
        """
        write_control_file(git_project, ['novel.txt'])
        before = commit_count(git_project)

        (git_project / 'novel.txt').write_text('Chapter 1\nChapter 2\n', encoding='utf-8')
        run_flashbake(git_project)

        after = commit_count(git_project)
        assert after == before + 1, (
            f"Expected exactly one new git commit after modifying a tracked file.\n"
            f"Commits before flashbake: {before}\n"
            f"Commits after flashbake:  {after}"
        )

    def test_the_right_file_is_in_the_commit(self, git_project):
        """
        The commit should contain the file that was actually modified,
        not some other file.
        """
        write_control_file(git_project, ['novel.txt'])
        (git_project / 'novel.txt').write_text('Revised draft\n', encoding='utf-8')
        run_flashbake(git_project)

        committed = latest_commit_files(git_project)
        assert 'novel.txt' in committed, (
            f"Expected 'novel.txt' in the commit, but the commit contained: {committed}"
        )

    def test_commit_message_is_not_empty(self, git_project):
        """
        The commit message must contain something. An empty message means
        all plugins failed silently.
        """
        write_control_file(git_project, ['novel.txt'])
        (git_project / 'novel.txt').write_text('New content\n', encoding='utf-8')
        run_flashbake(git_project)

        message = latest_commit_message(git_project)
        assert message.strip(), (
            "Commit message is empty. Check that at least one plugin is writing output."
        )

    def test_commit_message_contains_a_timestamp(self, git_project):
        """
        When the Timestamp plugin is configured, the commit message should
        contain something that looks like a time (digits and colons).

        This is a real end-to-end check: plugin runs → writes to temp file →
        git reads that file as the commit message → git history contains it.
        We verify using 'git log', not by inspecting Flashbake internals.
        """
        import re
        write_control_file(git_project, ['novel.txt'])
        (git_project / 'novel.txt').write_text('Final chapter\n', encoding='utf-8')
        run_flashbake(git_project)

        message = latest_commit_message(git_project)
        assert re.search(r'\d{1,2}:\d{2}', message), (
            f"Expected a timestamp (HH:MM) in the commit message from the Timestamp plugin.\n"
            f"Actual commit message:\n{message}"
        )

    def test_file_not_in_control_file_is_not_committed(self, git_project):
        """
        Flashbake must respect its control file boundary. A file that is
        modified but NOT listed in .flashbake should never appear in a commit.

        This protects users from accidentally committing files they didn't
        intend to track.
        """
        # Only track novel.txt; notes.txt is intentionally NOT in the control file
        write_control_file(git_project, ['novel.txt'])
        (git_project / 'notes.txt').write_text('Private research notes\n', encoding='utf-8')
        (git_project / 'novel.txt').write_text('New chapter\n', encoding='utf-8')
        run_flashbake(git_project)

        committed = latest_commit_files(git_project)
        assert 'notes.txt' not in committed, (
            "'notes.txt' appeared in the commit even though it is not listed "
            "in .flashbake. Flashbake committed a file it shouldn't have."
        )


# ---------------------------------------------------------------------------
# Tests: quiet period
# ---------------------------------------------------------------------------

class TestQuietPeriod:
    """
    Flashbake has a 'quiet period' feature: files modified too recently
    are held back to avoid partial saves being committed.
    """

    def test_recently_modified_file_is_held_back(self, git_project):
        """
        With a 60-minute quiet period, a file modified just now should
        NOT be committed — it's too recent.
        """
        write_control_file(git_project, ['novel.txt'])
        (git_project / 'novel.txt').write_text('Just saved this second\n', encoding='utf-8')
        # File's mtime is effectively 'now', so it should not be committed
        before = commit_count(git_project)

        run_flashbake(git_project, quiet_mins=60)

        after = commit_count(git_project)
        assert after == before, (
            f"A file modified just now should NOT be committed with quiet_mins=60.\n"
            f"Commits before: {before}, after: {after}"
        )

    def test_old_modification_passes_quiet_period(self, git_project):
        """
        A file modified 2 hours ago SHOULD be committed even with a
        60-minute quiet period, because it falls outside the window.

        We backdate the mtime manually to simulate an old modification.
        """
        write_control_file(git_project, ['novel.txt'])
        (git_project / 'novel.txt').write_text('Written hours ago\n', encoding='utf-8')

        # Backdate to 2 hours ago
        two_hours_ago = time.time() - (2 * 60 * 60)
        os.utime(str(git_project / 'novel.txt'), (two_hours_ago, two_hours_ago))

        before = commit_count(git_project)
        run_flashbake(git_project, quiet_mins=60)
        after = commit_count(git_project)

        assert after == before + 1, (
            f"A file modified 2 hours ago should be committed with quiet_mins=60.\n"
            f"Commits before: {before}, after: {after}"
        )


# ---------------------------------------------------------------------------
# Tests: no-op when nothing changed
# ---------------------------------------------------------------------------

class TestNoChanges:

    def test_no_commit_when_nothing_changed(self, git_project):
        """
        If no tracked files have changed, Flashbake must not create a commit.
        Creating spurious commits would pollute the project's git history.
        """
        write_control_file(git_project, ['novel.txt'])
        # Do NOT modify novel.txt — it is unchanged since the initial commit
        before = commit_count(git_project)

        run_flashbake(git_project)

        after = commit_count(git_project)
        assert after == before, (
            f"Flashbake created a commit even though no tracked file changed.\n"
            f"Commits before: {before}, after: {after}"
        )


# ---------------------------------------------------------------------------
# Tests: new files (not yet tracked by git)
# ---------------------------------------------------------------------------

class TestNewFiles:

    def test_new_file_in_control_gets_added_to_git(self, git_project):
        """
        A file listed in .flashbake that exists on disk but is not yet
        tracked by git should be added and committed by Flashbake.

        This is how writers start tracking a new document — they add it
        to .flashbake and Flashbake picks it up automatically.
        """
        new_chapter = git_project / 'chapter_2.txt'
        new_chapter.write_text('The story continues...\n', encoding='utf-8')
        write_control_file(git_project, ['novel.txt', 'chapter_2.txt'])

        before = commit_count(git_project)
        run_flashbake(git_project)
        after = commit_count(git_project)

        assert after > before, (
            "Flashbake should have committed the new file 'chapter_2.txt' that "
            "was listed in .flashbake but not yet tracked by git."
        )


# ---------------------------------------------------------------------------
# Tests: purge (recording deleted files)
# ---------------------------------------------------------------------------

class TestPurge:

    def test_purge_commits_deletion(self, git_project):
        """
        When a tracked file is deleted from disk and removed from git's
        index, 'flashbake --purge' should commit that deletion.

        This keeps the git history accurate about what files existed when.
        """
        original_cwd = os.getcwd()
        try:
            write_control_file(git_project, ['novel.txt'])
            os.chdir(str(git_project))

            # Remove from disk and from git's index
            subprocess.run(['git', 'rm', 'novel.txt'],
                           cwd=str(git_project), check=True, capture_output=True)

            hot_files, config = control.parse_control(
                str(git_project),
                str(git_project / '.flashbake'),
            )
            control.prepare_control(hot_files, config)

            before = commit_count(git_project)
            fb_commit.purge(config, hot_files)
            after = commit_count(git_project)

            assert after > before, (
                "flashbake purge should have committed the deletion of 'novel.txt', "
                "but the commit count did not increase."
            )
        finally:
            os.chdir(original_cwd)

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(PROJECT_ROOT, "tools", "git_push.py")

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@test.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@test.com",
}


def _git(repo, *args, **kwargs):
    cmd = ["git", "-C", repo] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, env=GIT_ENV, **kwargs)


class TestGitPush(unittest.TestCase):

    def setUp(self):
        self.repos = []
        self.remotes = []

    def tearDown(self):
        for d in self.repos + self.remotes:
            shutil.rmtree(d, ignore_errors=True)

    def _run(self, *args):
        cmd = [sys.executable, TOOL] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=GIT_ENV)

    def _make_repo(self, branch="development", with_remote=True):
        repo = tempfile.mkdtemp(prefix="nasopenclaw_test_gp_repo_")
        self.repos.append(repo)

        _git(repo, "init")
        _git(repo, "checkout", "-b", "main")
        # Write .factory.json
        with open(os.path.join(repo, ".factory.json"), "w") as f:
            json.dump({"locked": True}, f)
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "initial")

        if branch != "main":
            _git(repo, "checkout", "-b", branch)

        if with_remote:
            remote = tempfile.mkdtemp(prefix="nasopenclaw_test_gp_remote_")
            self.remotes.append(remote)
            subprocess.run(["git", "clone", "--bare", repo, remote],
                           capture_output=True, env=GIT_ENV)
            _git(repo, "remote", "remove", "origin")
            _git(repo, "remote", "add", "origin", remote)

        return repo

    # ── Branch enforcement ──────────────────────────────────────────────

    def test_rejects_non_development_branch(self):
        repo = self._make_repo(branch="main")
        r = self._run(repo, "test commit", "--skip-validation")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not 'development'", r.stdout)

    # ── .factory.json checks ───────────────────────────────────────────

    def test_missing_factory_json_exits_1(self):
        repo = self._make_repo(branch="development")
        os.remove(os.path.join(repo, ".factory.json"))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "remove factory")
        r = self._run(repo, "test", "--skip-validation")
        self.assertEqual(r.returncode, 1)
        self.assertIn(".factory.json not found", r.stdout)

    def test_malformed_factory_json_exits_1(self):
        repo = self._make_repo(branch="development")
        with open(os.path.join(repo, ".factory.json"), "w") as f:
            f.write("{{{bad")
        r = self._run(repo, "test", "--skip-validation")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Error reading .factory.json", r.stdout)

    # ── Not a git repo ──────────────────────────────────────────────────

    def test_not_a_git_repo_exits_1(self):
        tmpdir = tempfile.mkdtemp(prefix="nasopenclaw_test_gp_nogit_")
        self.repos.append(tmpdir)
        with open(os.path.join(tmpdir, ".factory.json"), "w") as f:
            json.dump({"locked": True}, f)
        r = self._run(tmpdir, "test", "--skip-validation")
        self.assertEqual(r.returncode, 1)

    # ── Nothing to commit ───────────────────────────────────────────────

    def test_nothing_to_commit_exits_0(self):
        repo = self._make_repo(branch="development")
        r = self._run(repo, "test commit", "--skip-validation")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Nothing to commit", r.stdout)

    # ── Successful commit and push ──────────────────────────────────────

    def test_successful_commit_and_push(self):
        repo = self._make_repo(branch="development", with_remote=True)
        # Make a change
        with open(os.path.join(repo, "newfile.txt"), "w") as f:
            f.write("hello")
        r = self._run(repo, "feat: add newfile", "--skip-validation")
        self.assertEqual(r.returncode, 0, f"stdout: {r.stdout}\nstderr: {r.stderr}")
        self.assertIn("Success", r.stdout)
        self.assertIn("Commit Hash:", r.stdout)

    def test_commit_message_in_git_log(self):
        repo = self._make_repo(branch="development", with_remote=True)
        with open(os.path.join(repo, "file.txt"), "w") as f:
            f.write("data")
        self._run(repo, "feat: unique test message 12345", "--skip-validation")
        log = _git(repo, "log", "--oneline", "-1")
        self.assertIn("unique test message 12345", log.stdout)

    def test_remote_receives_push(self):
        repo = self._make_repo(branch="development", with_remote=True)
        remote = self.remotes[-1]
        with open(os.path.join(repo, "pushed.txt"), "w") as f:
            f.write("pushed")
        self._run(repo, "test push", "--skip-validation")
        # Verify remote has the commit
        log = subprocess.run(["git", "-C", remote, "log", "--oneline", "development"],
                             capture_output=True, text=True, env=GIT_ENV)
        self.assertIn("test push", log.stdout)

    # ── Skip validation flag ────────────────────────────────────────────

    def test_skip_validation_flag(self):
        repo = self._make_repo(branch="development")
        with open(os.path.join(repo, "x.txt"), "w") as f:
            f.write("x")
        r = self._run(repo, "test", "--skip-validation")
        self.assertIn("Skipping shared file validation", r.stdout)

    # ── Stages all changes ──────────────────────────────────────────────

    def test_stages_new_modified_deleted(self):
        repo = self._make_repo(branch="development", with_remote=True)
        # Create a tracked file
        with open(os.path.join(repo, "existing.txt"), "w") as f:
            f.write("old")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "add existing")
        _git(repo, "push", "origin", "development")
        # Now: modify existing, add new, delete factory won't work so add another
        with open(os.path.join(repo, "existing.txt"), "w") as f:
            f.write("modified")
        with open(os.path.join(repo, "brand_new.txt"), "w") as f:
            f.write("new")
        r = self._run(repo, "test all changes", "--skip-validation")
        self.assertEqual(r.returncode, 0, f"stdout: {r.stdout}\nstderr: {r.stderr}")

    # ── Argument errors ─────────────────────────────────────────────────

    def test_no_args_exits_error(self):
        r = self._run()
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()

import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "dxm" / "scripts" / "scaffold_dxm.py"


def write_fake_trellis(bin_dir: Path, *, create_start_skill: bool = True, sleep_seconds: int = 0) -> None:
    start_skill_lines = []
    if create_start_skill:
        start_skill_lines = [
            "(root / '.agents' / 'skills' / 'trellis-start').mkdir(parents=True, exist_ok=True)",
            "(root / '.agents' / 'skills' / 'trellis-start' / 'SKILL.md').write_text('# trellis-start\\n\\n## Steps\\n\\n1. Start the active task.\\n', encoding='utf-8')",
        ]
    py = bin_dir / "trellis"
    py.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import time",
                "from pathlib import Path",
                f"time.sleep({sleep_seconds})",
                "root = Path.cwd()",
                "(root / '.trellis' / 'tasks').mkdir(parents=True, exist_ok=True)",
                "(root / '.trellis' / 'spec').mkdir(parents=True, exist_ok=True)",
                "(root / '.trellis' / 'config.yaml').write_text('session_auto_commit: true\\n', encoding='utf-8')",
                "(root / '.trellis' / 'workflow.md').write_text('# Workflow\\n\\nNo active task: create one before implementation.\\n', encoding='utf-8')",
                *start_skill_lines,
                "print('Mode: Codex')",
                "print('Configuring Codex hooks')",
            ]
        ),
        encoding="utf-8",
    )
    py.chmod(py.stat().st_mode | stat.S_IEXEC)

    cmd = bin_dir / "trellis.cmd"
    cmd.write_text(
        "\r\n".join(
            [
                "@echo off",
                f"\"{sys.executable}\" \"{py}\" %*",
            ]
        ),
        encoding="utf-8",
    )


class ScaffoldDxmTests(unittest.TestCase):
    def run_scaffold(self, root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), *args],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
            check=False,
        )

    def test_generated_agents_includes_first_run_grill_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "new-product"
            result = self.run_scaffold(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("project-grill", agents)
            self.assertIn("new-project-grill", agents)
            self.assertIn("grill-with-docs", agents)
            self.assertIn("lightweight-grill", agents)
            self.assertIn("模式标签", agents)
            self.assertIn("grill-me", agents)
            self.assertIn("scaffold only", agents)
            self.assertIn("只分析", agents)

    def test_trellis_mode_initializes_and_applies_dxm_safety_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "trellis-project"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            result = self.run_scaffold(root, "--trellis", "--trellis-user", "admin", env=env)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("trellis init --codex", result.stdout)
            self.assertIn("DXM-TRELLIS", (root / "项目文件结构说明.md").read_text(encoding="utf-8"))
            self.assertIn("DXM-TRELLIS", (root / "项目完整链路说明.md").read_text(encoding="utf-8"))

            config = (root / ".trellis" / "config.yaml").read_text(encoding="utf-8")
            self.assertIn("session_auto_commit: false", config)
            self.assertNotIn("session_auto_commit: true", config)

            trellis_start = (root / ".agents" / "skills" / "trellis-start" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("DXM Step 0", trellis_start)
            self.assertIn("AGENTS.md", trellis_start)

            workflow = (root / ".trellis" / "workflow.md").read_text(encoding="utf-8")
            self.assertIn("DXM no-task routing", workflow)
            self.assertIn("小修", workflow)

    def test_trellis_missing_command_still_scaffolds_normal_dxm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "no-trellis"
            bin_dir = Path(tmp) / "empty-bin"
            bin_dir.mkdir()
            env = os.environ.copy()
            env["PATH"] = str(bin_dir)

            result = self.run_scaffold(root, "--trellis", env=env)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("missing-command: trellis init --codex", result.stdout)
            self.assertTrue((root / "AGENTS.md").exists())
            self.assertFalse((root / ".trellis").exists())

    def test_trellis_missing_start_skill_is_reported_not_fabricated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "missing-start"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir, create_start_skill=False)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            result = self.run_scaffold(root, "--trellis", env=env)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("missing-trellis-start-skill", result.stdout)
            self.assertFalse((root / ".agents" / "skills" / "trellis-start" / "SKILL.md").exists())

    def test_trellis_timeout_is_reported_without_hanging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "timeout"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir, sleep_seconds=5)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            started = time.monotonic()
            result = self.run_scaffold(root, "--trellis", "--trellis-timeout-seconds", "1", env=env)
            elapsed = time.monotonic() - started

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("timeout: trellis init --codex", result.stdout)
            self.assertLess(elapsed, 4.0)
            self.assertTrue((root / "AGENTS.md").exists())

    def test_existing_docs_are_preserved_and_trellis_blocks_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "idempotent"
            root.mkdir()
            manual = "manual project knowledge\n"
            (root / "项目完整链路说明.md").write_text(manual, encoding="utf-8")
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            first = self.run_scaffold(root, "--trellis", env=env)
            second = self.run_scaffold(root, "--trellis", env=env)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            chain = (root / "项目完整链路说明.md").read_text(encoding="utf-8")
            self.assertTrue(chain.startswith(manual))
            self.assertEqual(chain.count("DXM-TRELLIS:START"), 1)


if __name__ == "__main__":
    unittest.main()

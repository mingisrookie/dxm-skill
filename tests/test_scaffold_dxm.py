import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "dxm" / "scripts" / "scaffold_dxm.py"
DXM_FILES = [
    "AGENTS.md",
    "项目开发规范（AI协作）.md",
    "项目完整链路说明.md",
    "项目文件结构说明.md",
    "开发者AI开发与PR提交流程.md",
]


def assert_lf_only(testcase: unittest.TestCase, path: Path) -> None:
    data = path.read_bytes()
    testcase.assertNotIn(b"\r\n", data, f"{path.name} contains CRLF line endings")
    testcase.assertNotIn(b"\r", data, f"{path.name} contains bare CR line endings")


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

    def test_scaffold_creates_all_files_with_lf_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "lf-project"
            result = self.run_scaffold(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            for name in DXM_FILES:
                path = root / name
                self.assertTrue(path.exists(), name)
                assert_lf_only(self, path)

    def test_trellis_append_keeps_lf_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "trellis-lf"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            result = self.run_scaffold(root, "--trellis", env=env)

            self.assertEqual(result.returncode, 0, result.stderr)
            assert_lf_only(self, root / "项目完整链路说明.md")
            assert_lf_only(self, root / "项目文件结构说明.md")

    def test_dry_run_reports_actions_without_writing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "dry-run-project"
            result = self.run_scaffold(root, "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DXM scaffold root:", result.stdout)
            self.assertIn("would-create: AGENTS.md", result.stdout)
            self.assertFalse(root.exists())

    def test_existing_non_utf8_file_fails_without_mutating_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "gbk-project"
            root.mkdir()
            agents = root / "AGENTS.md"
            original = "人工维护：中文\n".encode("gbk")
            agents.write_bytes(original)

            result = self.run_scaffold(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not valid UTF-8", result.stderr)
            self.assertEqual(agents.read_bytes(), original)
            self.assertFalse((root / "项目开发规范（AI协作）.md").exists())

    def test_sensitive_inventory_matches_common_secret_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "secrets-project"
            root.mkdir()
            for name in [".env.production", "server.pem", "id_rsa", "credentials.json", "normal.txt"]:
                (root / name).write_text("placeholder\n", encoding="utf-8")

            result = self.run_scaffold(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            structure = (root / "项目文件结构说明.md").read_text(encoding="utf-8")
            for name in [".env.production", "server.pem", "id_rsa", "credentials.json"]:
                self.assertRegex(structure, rf"`{re.escape(name)}`：运行态或敏感数据")
            self.assertRegex(structure, r"`normal\.txt`：项目文件")

    def test_sensitive_inventory_avoids_false_positives_and_covers_more_secret_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "sensitive-boundary-project"
            root.mkdir()
            sensitive = [".npmrc", ".pypirc", ".netrc", "service-account.json", "prod.secret.yaml", "app.keystore"]
            safe = ["tokenizer.py", "passwordless.md", "secretary-notes.md", "normal.txt"]
            for name in [*sensitive, *safe]:
                (root / name).write_text("placeholder\n", encoding="utf-8")

            result = self.run_scaffold(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            structure = (root / "项目文件结构说明.md").read_text(encoding="utf-8")
            for name in sensitive:
                self.assertRegex(structure, rf"`{re.escape(name)}`：运行态或敏感数据")
            for name in safe:
                self.assertRegex(structure, rf"`{re.escape(name)}`：项目文件")

    def test_existing_start_marker_without_end_marker_is_not_duplicated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "marker-project"
            root.mkdir()
            agents = root / "AGENTS.md"
            agents.write_text("manual\n<!-- DXM-RULES:START -->\npartial\n", encoding="utf-8", newline="\n")

            result = self.run_scaffold(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            content = agents.read_text(encoding="utf-8")
            self.assertEqual(content.count("<!-- DXM-RULES:START -->"), 1)
            self.assertIn("skipped-existing-marker-start: AGENTS.md", result.stdout)

    def test_refresh_blocks_updates_managed_block_and_preserves_manual_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "refresh-project"
            first = self.run_scaffold(root)
            self.assertEqual(first.returncode, 0, first.stderr)

            chain = root / "项目完整链路说明.md"
            content = chain.read_text(encoding="utf-8")
            start = "<!-- DXM-DOC-RULES:START -->"
            end = "<!-- DXM-DOC-RULES:END -->"
            start_index = content.index(start)
            end_index = content.index(end, start_index) + len(end)
            stale = content[:start_index] + start + "\n旧版规则块\n" + end + content[end_index:] + "\n\n## 手工补充\nmanual note\n"
            chain.write_text(stale, encoding="utf-8", newline="\n")

            result = self.run_scaffold(root, "--refresh-blocks")

            self.assertEqual(result.returncode, 0, result.stderr)
            refreshed = chain.read_text(encoding="utf-8")
            self.assertIn("refreshed-managed-block: 项目完整链路说明.md", result.stdout)
            self.assertNotIn("旧版规则块", refreshed)
            self.assertIn("## 手工补充\nmanual note", refreshed)
            self.assertIn("DXM 文档维护规则", refreshed)

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

    def test_trellis_preflight_rejects_non_utf8_docs_before_mutating_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "trellis-preflight"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            first = self.run_scaffold(root)
            self.assertEqual(first.returncode, 0, first.stderr)
            agents_before = (root / "AGENTS.md").read_bytes()
            bad_doc = root / "项目开发规范（AI协作）.md"
            original = "人工维护：中文\n".encode("gbk")
            bad_doc.write_bytes(original)

            result = self.run_scaffold(root, "--trellis", env=env)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not valid UTF-8", result.stderr)
            self.assertEqual(bad_doc.read_bytes(), original)
            self.assertEqual((root / "AGENTS.md").read_bytes(), agents_before)
            self.assertFalse((root / ".trellis").exists())

    def test_dry_run_trellis_reports_existing_safety_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "dry-run-trellis-existing"
            first = self.run_scaffold(root)
            self.assertEqual(first.returncode, 0, first.stderr)
            (root / ".trellis").mkdir()
            (root / ".trellis" / "config.yaml").write_text("session_auto_commit: true\n", encoding="utf-8")
            (root / ".trellis" / "workflow.md").write_text("# Workflow\n", encoding="utf-8")
            (root / ".agents" / "skills" / "trellis-start").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-start" / "SKILL.md").write_text("# trellis-start\n", encoding="utf-8")

            result = self.run_scaffold(root, "--trellis", "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("would-run: trellis init --codex", result.stdout)
            self.assertIn("would-append-trellis-block: 项目完整链路说明.md", result.stdout)
            self.assertIn("would-update: .trellis/config.yaml session_auto_commit", result.stdout)
            self.assertIn("would-append-trellis-block: .trellis/workflow.md DXM no-task routing", result.stdout)

    def test_broad_root_guard_requires_explicit_override(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("scaffold_dxm", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)

        broad_root = Path(Path.cwd().anchor)
        self.assertTrue(module.is_broad_root(broad_root))
        self.assertFalse(module.is_broad_root(Path.cwd()))

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

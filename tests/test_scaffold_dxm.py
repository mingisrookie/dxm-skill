import os
import json
import io
import re
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
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


def write_fake_trellis(
    bin_dir: Path,
    *,
    create_start_skill: bool = True,
    create_trellis: bool = True,
    sleep_seconds: int = 0,
    exit_code: int = 0,
) -> None:
    start_skill_lines = []
    if create_trellis and create_start_skill:
        start_skill_lines = [
            "(root / '.agents' / 'skills' / 'trellis-start').mkdir(parents=True, exist_ok=True)",
            "start_skill = root / '.agents' / 'skills' / 'trellis-start' / 'SKILL.md'",
            "if not start_skill.exists():",
            "    start_skill.write_text('# trellis-start\\n\\n## Steps\\n\\n1. Start the active task.\\n', encoding='utf-8')",
        ]
    trellis_lines = []
    if create_trellis:
        trellis_lines = [
            "(root / '.trellis' / 'tasks').mkdir(parents=True, exist_ok=True)",
            "(root / '.trellis' / 'spec').mkdir(parents=True, exist_ok=True)",
            "config = root / '.trellis' / 'config.yaml'",
            "if not config.exists():",
            "    config.write_text('session_auto_commit: true\\n', encoding='utf-8')",
            "workflow = root / '.trellis' / 'workflow.md'",
            "if not workflow.exists():",
            "    workflow.write_text('# Workflow\\n\\nNo active task: create one before implementation.\\n', encoding='utf-8')",
            *start_skill_lines,
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
                *trellis_lines,
                "print('Mode: Codex')",
                "print('Configuring Codex hooks')",
                f"raise SystemExit({exit_code})",
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

    def load_scaffold_module(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("scaffold_dxm", SCRIPT)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        return module

    def write_baseline(self, path: Path, root: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project_root": str(root.resolve()),
                    "goal": "Provide a deterministic DXM workflow.",
                    "primary_users": ["maintainers", "agentic developers"],
                    "deliverables": ["governed project docs", "validated completion receipt"],
                    "non_goals": ["automatic Git publication"],
                    "runtime": {
                        "entry_points": ["python skills/dxm/scripts/scaffold_dxm.py"],
                        "facts": ["Python standard library only"],
                    },
                    "acceptance_criteria": [
                        {
                            "id": "AC-01",
                            "description": "The scaffold is auditable.",
                            "evidence_kinds": ["unit-test", "cli"],
                        }
                    ],
                    "validation_commands": ["python -m unittest discover -s tests -v"],
                    "assumptions": ["Python 3.10+ is available"],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
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
            self.assertIn("四模式状态机", agents)
            self.assertIn("grilling", agents)
            self.assertIn("domain-modeling", agents)
            self.assertIn("grill-me", agents)  # legacy alias remains documented
            self.assertIn("第一性原理", agents)
            self.assertIn("质疑隐藏假设", agents)
            self.assertIn("scaffold only", agents)
            self.assertIn("只分析", agents)

    def test_generated_docs_include_release_publication_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "release-project"
            result = self.run_scaffold(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            workflow = (root / "开发者AI开发与PR提交流程.md").read_text(encoding="utf-8")
            dev_rules = (root / "项目开发规范（AI协作）.md").read_text(encoding="utf-8")
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")

            for expected in [
                "发布工作不是只 push main",
                "VERSION",
                "CHANGELOG.md",
                "GitHub Release",
                "中文更新日志",
                "Latest",
                "GitHub Release URL",
                "中文 Release notes",
                "对比链接",
                "真实变更、修复、验证和已知风险",
                "规则沉淀或踩坑复盘",
                "$repo = gh repo view --json nameWithOwner --jq .nameWithOwner",
                '$tag = "v$(Get-Content VERSION)"',
                "gh api repos/$repo/releases/latest --jq .tag_name",
                "未获明确授权时",
                "本地 HEAD、远端分支和 tag 指向的提交必须一致",
            ]:
                self.assertIn(expected, workflow)
            self.assertIn("发布 / Release", dev_rules)
            self.assertIn("### 0.6 开发方案与开发清单", dev_rules)
            self.assertIn("### 0.7 阶段化开发硬要求", dev_rules)
            self.assertIn("中文更新日志、对比链接和验证证据", dev_rules)
            self.assertIn("第一性原理", dev_rules)
            self.assertIn("对抗性检查", dev_rules)
            self.assertIn("GitHub Release URL", dev_rules)
            self.assertIn("发布 / release / version / latest / tag", agents)
            self.assertIn("开发者AI开发与PR提交流程.md", agents)
            self.assertIn("发布工作不是只 push main", agents)

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

    def test_cli_prints_unicode_filenames_with_legacy_stdio_encoding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "legacy-stdio-project"
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "cp1252"

            result = self.run_scaffold(root, "--dry-run", env=env)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("would-create: 项目开发规范（AI协作）.md", result.stdout)
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

    def test_existing_hardlinked_target_is_rejected_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "hardlink-project"
            root.mkdir()
            outside = base / "outside-agents.md"
            original = "outside manual content\n"
            outside.write_text(original, encoding="utf-8", newline="\n")
            try:
                os.link(outside, root / "AGENTS.md")
            except OSError as exc:
                self.skipTest(f"hardlinks unavailable: {exc}")

            result = self.run_scaffold(root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("unsafe managed path", result.stderr)
            self.assertEqual(outside.read_text(encoding="utf-8"), original)
            self.assertFalse((root / "项目开发规范（AI协作）.md").exists())

    def test_non_file_late_target_is_rejected_before_force_mutates_earlier_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "directory-target-project"
            root.mkdir()
            agents = root / "AGENTS.md"
            original = "manual agents\n"
            agents.write_text(original, encoding="utf-8", newline="\n")
            (root / "开发者AI开发与PR提交流程.md").mkdir()

            result = self.run_scaffold(root, "--force")

            self.assertEqual(result.returncode, 2)
            self.assertIn("unsafe managed path", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(agents.read_text(encoding="utf-8"), original)
            self.assertFalse((root / "项目开发规范（AI协作）.md").exists())

    def test_inventory_does_not_follow_directory_links_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "linked-inventory"
            outside = base / "external-tree"
            root.mkdir()
            outside.mkdir()
            (outside / "must-not-appear.txt").write_text("private name\n", encoding="utf-8")
            link = root / "external-link"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")

            result = self.run_scaffold(root, "--inventory-depth", "3")

            self.assertEqual(result.returncode, 0, result.stderr)
            structure = (root / "项目文件结构说明.md").read_text(encoding="utf-8")
            self.assertIn("external-link", structure)
            self.assertIn("不展开", structure)
            self.assertNotIn("must-not-appear.txt", structure)

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
            safe = [
                "config.json",
                "tokenizer.py",
                "passwordless.md",
                "secretary-notes.md",
                "secret-management.md",
                "token_utils.py",
                "password-reset.tsx",
                "credentials_helper.py",
                "normal.txt",
            ]
            for name in [*sensitive, *safe]:
                (root / name).write_text("placeholder\n", encoding="utf-8")

            result = self.run_scaffold(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            structure = (root / "项目文件结构说明.md").read_text(encoding="utf-8")
            for name in sensitive:
                self.assertRegex(structure, rf"`{re.escape(name)}`：运行态或敏感数据")
            for name in safe:
                self.assertRegex(structure, rf"`{re.escape(name)}`：项目文件")

    def test_inventory_skips_common_tooling_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "tooling-dirs-project"
            for name in [".venv", "venv", ".idea", ".vscode", ".pytest_cache", ".tox"]:
                nested = root / name / "nested"
                nested.mkdir(parents=True)
                (nested / "noise.txt").write_text("placeholder\n", encoding="utf-8")

            result = self.run_scaffold(root, "--inventory-depth", "2")

            self.assertEqual(result.returncode, 0, result.stderr)
            structure = (root / "项目文件结构说明.md").read_text(encoding="utf-8")
            for name in [".venv", "venv", ".idea", ".vscode", ".pytest_cache", ".tox"]:
                self.assertRegex(structure, rf"`{re.escape(name)}/`：依赖、构建或工具目录")
                self.assertNotRegex(structure, rf"`{re.escape(name)}/nested/`")

    def test_existing_start_marker_without_end_marker_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "marker-project"
            root.mkdir()
            agents = root / "AGENTS.md"
            agents.write_text("manual\n<!-- DXM-RULES:START -->\npartial\n", encoding="utf-8", newline="\n")

            result = self.run_scaffold(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("incomplete managed block", result.stderr)
            content = agents.read_text(encoding="utf-8")
            self.assertEqual(content.count("<!-- DXM-RULES:START -->"), 1)

    def test_existing_orphan_end_marker_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "orphan-end"
            root.mkdir()
            agents = root / "AGENTS.md"
            agents.write_text("manual\n<!-- DXM-RULES:END -->\n", encoding="utf-8", newline="\n")

            result = self.run_scaffold(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid managed block", result.stderr)
            self.assertEqual(agents.read_text(encoding="utf-8").count("DXM-RULES:END"), 1)

    def test_duplicate_managed_marker_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "duplicate-marker"
            root.mkdir()
            agents = root / "AGENTS.md"
            agents.write_text(
                "<!-- DXM-RULES:START -->\none\n<!-- DXM-RULES:END -->\n"
                "<!-- DXM-RULES:START -->\ntwo\n<!-- DXM-RULES:END -->\n",
                encoding="utf-8",
                newline="\n",
            )

            result = self.run_scaffold(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid managed block", result.stderr)

    def test_crossed_managed_blocks_fail_before_any_scaffold_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "crossed-markers"
            root.mkdir()
            rules = root / "项目开发规范（AI协作）.md"
            original = (
                "manual\n"
                "<!-- DXM-DOC-RULES:START -->\n"
                "doc\n"
                "<!-- DXM-TRELLIS:START -->\n"
                "trellis\n"
                "<!-- DXM-DOC-RULES:END -->\n"
                "<!-- DXM-TRELLIS:END -->\n"
            )
            rules.write_text(original, encoding="utf-8", newline="\n")

            result = self.run_scaffold(root, "--refresh-blocks")

            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid managed block", result.stderr)
            self.assertEqual(rules.read_text(encoding="utf-8"), original)
            self.assertFalse((root / "AGENTS.md").exists())

    def test_marker_like_noncanonical_case_is_rejected_before_append(self) -> None:
        cases = {
            "lowercase": "<!-- dxm-rules:start -->\nmanual\n<!-- dxm-rules:end -->\n",
            "unclosed_start": "<!-- DXM-RULES:START\nmanual\n",
            "unclosed_end": "<!-- DXM-RULES:END\nmanual\n",
            "tab_indented_pseudo_fence": "\t```md\n<!-- DXM-RULES:START -->\n\t```\n",
            "mismatched_inline_ticks": "x```<!-- DXM-RULES:START -->``\n",
            "mismatched_inline_lowercase": "x```<!-- dxm-rules:start -->``\n",
        }
        for label, original in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "malformed-marker"
                root.mkdir()
                agents = root / "AGENTS.md"
                agents.write_text(original, encoding="utf-8", newline="\n")

                result = self.run_scaffold(root)

                self.assertEqual(result.returncode, 2)
                self.assertIn("managed block", result.stderr)
                self.assertEqual(agents.read_text(encoding="utf-8"), original)
            self.assertFalse((root / "项目开发规范（AI协作）.md").exists())

    def test_existing_doc_start_marker_without_end_marker_fails_before_mutating_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "doc-marker-project"
            root.mkdir()
            agents = root / "AGENTS.md"
            doc = root / "项目完整链路说明.md"
            agents.write_text("manual agents\n", encoding="utf-8", newline="\n")
            doc.write_text("manual\n<!-- DXM-DOC-RULES:START -->\npartial\n", encoding="utf-8", newline="\n")
            agents_before = agents.read_bytes()
            doc_before = doc.read_bytes()

            result = self.run_scaffold(root, "--refresh-blocks")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("incomplete managed block", result.stderr)
            self.assertEqual(agents.read_bytes(), agents_before)
            self.assertEqual(doc.read_bytes(), doc_before)

    def test_refresh_ignores_inline_and_fenced_marker_examples_and_updates_real_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "marker-examples"
            root.mkdir()
            agents = root / "AGENTS.md"
            examples = (
                "Inline example: `<!-- DXM-RULES:START --> ... <!-- DXM-RULES:END -->`\n\n"
                "```md\n<!-- DXM-RULES:START -->\nexample only\n<!-- DXM-RULES:END -->\n```\n"
            )
            agents.write_text(
                "# Manual\n\n"
                + examples
                + "\n<!-- DXM-RULES:START -->\nold real block\n<!-- DXM-RULES:END -->\n\nTail\n",
                encoding="utf-8",
            )

            result = self.run_scaffold(root, "--refresh-blocks")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            updated = agents.read_text(encoding="utf-8")
            self.assertIn(examples, updated)
            self.assertIn("## 四模式状态机", updated)
            self.assertNotIn("old real block", updated)
            self.assertIn("Tail", updated)

    def test_fenced_marker_examples_do_not_count_as_a_real_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "marker-example-only"
            root.mkdir()
            agents = root / "AGENTS.md"
            example = (
                "# Manual\n\n```md\n<!-- DXM-RULES:START -->\n"
                "example only\n<!-- DXM-RULES:END -->\n```\n"
            )
            agents.write_text(example, encoding="utf-8")

            result = self.run_scaffold(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            updated = agents.read_text(encoding="utf-8")
            self.assertTrue(updated.startswith(example))
            self.assertIn("## 四模式状态机", updated)
            self.assertIn("appended-dxm-block: AGENTS.md", result.stdout)

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

    def test_baseline_is_persisted_and_hydrates_chain_doc_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "baseline-project"
            baseline = Path(tmp) / "baseline.json"
            self.write_baseline(baseline, root)

            first = self.run_scaffold(root, "--baseline", str(baseline))
            second = self.run_scaffold(root, "--baseline", str(baseline))

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            stored = root / ".dxm" / "project.json"
            self.assertTrue(stored.exists())
            self.assertEqual(json.loads(stored.read_text(encoding="utf-8"))["goal"], "Provide a deterministic DXM workflow.")
            chain = (root / "项目完整链路说明.md").read_text(encoding="utf-8")
            self.assertEqual(chain.count("<!-- DXM-PROJECT-BASELINE:START -->"), 1)
            self.assertEqual(chain.count("<!-- DXM-PROJECT-BASELINE:END -->"), 1)
            self.assertIn("AC-01", chain)
            self.assertIn("DXM scaffold status: READY", second.stdout)

    def test_shared_docs_keep_machine_root_only_in_local_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "portable-project"
            baseline = Path(tmp) / "baseline.json"
            self.write_baseline(baseline, root)

            result = self.run_scaffold(root, "--mode", "init", "--baseline", str(baseline))

            self.assertEqual(result.returncode, 0, result.stderr)
            canonical_root = str(root.resolve())
            stored = json.loads((root / ".dxm" / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["project_root"], canonical_root)
            for name in DXM_FILES:
                self.assertNotIn(canonical_root, (root / name).read_text(encoding="utf-8"), name)

    def test_baseline_hydration_preserves_existing_manual_chain_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "manual-baseline-project"
            root.mkdir()
            chain = root / "项目完整链路说明.md"
            chain.write_text("# Manual chain\n\nkeep this\n", encoding="utf-8", newline="\n")
            baseline = Path(tmp) / "baseline.json"
            self.write_baseline(baseline, root)

            result = self.run_scaffold(root, "--baseline", str(baseline))

            self.assertEqual(result.returncode, 0, result.stderr)
            content = chain.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("# Manual chain\n\nkeep this"))
            self.assertEqual(content.count("DXM-PROJECT-BASELINE:START"), 1)

    def test_invalid_baseline_root_fails_before_creating_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "actual-project"
            baseline = Path(tmp) / "baseline.json"
            self.write_baseline(baseline, Path(tmp) / "different-project")

            result = self.run_scaffold(root, "--baseline", str(baseline))

            self.assertEqual(result.returncode, 2)
            self.assertIn("project_root does not match", result.stderr)
            self.assertFalse(root.exists())

    def test_broken_baseline_marker_fails_before_mutating_existing_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "broken-baseline-marker"
            first = self.run_scaffold(root)
            self.assertEqual(first.returncode, 0, first.stderr)
            agents_before = (root / "AGENTS.md").read_bytes()
            chain = root / "项目完整链路说明.md"
            chain.write_text(
                chain.read_text(encoding="utf-8")
                + "\n<!-- DXM-PROJECT-BASELINE:START -->\npartial\n",
                encoding="utf-8",
                newline="\n",
            )
            baseline = Path(tmp) / "baseline.json"
            self.write_baseline(baseline, root)

            result = self.run_scaffold(root, "--baseline", str(baseline))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("incomplete managed block", result.stderr)
            self.assertEqual((root / "AGENTS.md").read_bytes(), agents_before)

    def test_non_utf8_existing_baseline_fails_before_creating_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bad-existing-baseline"
            (root / ".dxm").mkdir(parents=True)
            (root / ".dxm" / "project.json").write_bytes("中文".encode("gbk"))
            baseline = Path(tmp) / "baseline.json"
            self.write_baseline(baseline, root)

            result = self.run_scaffold(root, "--baseline", str(baseline))

            self.assertEqual(result.returncode, 2)
            self.assertIn("not valid UTF-8", result.stderr)
            self.assertFalse((root / "AGENTS.md").exists())

    def test_scaffold_without_baseline_reports_partial_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "partial-project"

            result = self.run_scaffold(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DXM scaffold status: PARTIAL", result.stdout)
            self.assertNotIn("DXM scaffold status: READY", result.stdout)

    def test_init_mode_requires_valid_baseline_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "guarded-init"

            result = self.run_scaffold(root, "--mode", "init")

            self.assertEqual(result.returncode, 2)
            self.assertIn("--mode init requires --baseline", result.stderr)
            self.assertFalse(root.exists())

    def test_scaffold_only_mode_rejects_baseline_and_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "guarded-scaffold-only"
            baseline = Path(tmp) / "baseline.json"
            self.write_baseline(baseline, root)

            result = self.run_scaffold(root, "--mode", "scaffold-only", "--baseline", str(baseline))

            self.assertEqual(result.returncode, 2)
            self.assertIn("--mode scaffold-only cannot accept --baseline", result.stderr)
            self.assertFalse(root.exists())

    def test_init_mode_with_baseline_reaches_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "guarded-ready-init"
            baseline = Path(tmp) / "baseline.json"
            self.write_baseline(baseline, root)

            result = self.run_scaffold(root, "--mode", "init", "--baseline", str(baseline))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DXM scaffold status: READY", result.stdout)

            scaffold_only = self.run_scaffold(root, "--mode", "scaffold-only")
            self.assertEqual(scaffold_only.returncode, 0, scaffold_only.stderr)
            self.assertIn("DXM scaffold result: SCAFFOLD_ONLY", scaffold_only.stdout)
            self.assertIn("DXM readiness: NOT_EVALUATED", scaffold_only.stdout)
            self.assertNotIn("DXM scaffold status:", scaffold_only.stdout)
            self.assertIn("no project readiness claim", scaffold_only.stdout)

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
            agents_text = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("grill-with-docs` 可在已安装且任务描述匹配时", agents_text)
            self.assertIn("full `grilling`", agents_text)
            self.assertIn("explicit opt-in", agents_text)

            config = (root / ".trellis" / "config.yaml").read_text(encoding="utf-8")
            self.assertIn("session_auto_commit: false", config)
            self.assertNotIn("session_auto_commit: true", config)

            trellis_start = (root / ".agents" / "skills" / "trellis-start" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("DXM Step 0", trellis_start)
            self.assertIn("AGENTS.md", trellis_start)
            self.assertIn("selective docs", trellis_start)
            self.assertIn("0–3", trellis_start)
            self.assertIn("第一性原理", trellis_start)
            self.assertIn("对抗性检查", trellis_start)

            workflow = (root / ".trellis" / "workflow.md").read_text(encoding="utf-8")
            self.assertIn("DXM no-task routing", workflow)
            self.assertIn("小修", workflow)
            self.assertIn("0–3", workflow)
            self.assertIn("optional", workflow)
            self.assertIn("对抗性检查", workflow)

    def test_trellis_commented_session_auto_commit_is_uncommented_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "trellis-commented-config"
            first = self.run_scaffold(root)
            self.assertEqual(first.returncode, 0, first.stderr)

            (root / ".trellis").mkdir()
            (root / ".trellis" / "config.yaml").write_text("# session_auto_commit: true\nother: 1\n", encoding="utf-8")
            (root / ".trellis" / "workflow.md").write_text("# Workflow\n", encoding="utf-8")
            (root / ".agents" / "skills" / "trellis-start").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-start" / "SKILL.md").write_text("# trellis-start\n", encoding="utf-8")

            env = os.environ.copy()
            env["PATH"] = ""
            result = self.run_scaffold(root, "--trellis", env=env)

            self.assertEqual(result.returncode, 0, result.stderr)
            config = (root / ".trellis" / "config.yaml").read_text(encoding="utf-8")
            self.assertIn("session_auto_commit: false", config)
            self.assertNotIn("# session_auto_commit: true", config)
            self.assertEqual(config.count("session_auto_commit"), 1)
            self.assertIn("other: 1", config)

    def test_trellis_duplicate_active_session_auto_commit_keys_are_collapsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "trellis-duplicate-config"
            first = self.run_scaffold(root)
            self.assertEqual(first.returncode, 0, first.stderr)

            (root / ".trellis").mkdir()
            (root / ".trellis" / "config.yaml").write_text(
                "session_auto_commit: false\nother: 1\nsession_auto_commit: true\n",
                encoding="utf-8",
            )
            (root / ".trellis" / "workflow.md").write_text("# Workflow\n", encoding="utf-8")
            (root / ".agents" / "skills" / "trellis-start").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-start" / "SKILL.md").write_text(
                "# trellis-start\n",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["PATH"] = ""
            result = self.run_scaffold(root, "--trellis", env=env)

            self.assertEqual(result.returncode, 0, result.stderr)
            config = (root / ".trellis" / "config.yaml").read_text(encoding="utf-8")
            self.assertEqual(len(re.findall(r"(?m)^\s*session_auto_commit\s*:", config)), 1)
            self.assertIn("session_auto_commit: false", config)
            self.assertIn("other: 1", config)

    def test_trellis_nested_session_auto_commit_is_preserved_and_top_level_is_added(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "trellis-nested-config"
            first = self.run_scaffold(root)
            self.assertEqual(first.returncode, 0, first.stderr)

            (root / ".trellis").mkdir()
            (root / ".trellis" / "config.yaml").write_text(
                "nested:\n  session_auto_commit: true\nother: 1\n",
                encoding="utf-8",
            )
            (root / ".trellis" / "workflow.md").write_text("# Workflow\n", encoding="utf-8")
            (root / ".agents" / "skills" / "trellis-start").mkdir(parents=True)
            (root / ".agents" / "skills" / "trellis-start" / "SKILL.md").write_text(
                "# trellis-start\n",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["PATH"] = ""
            result = self.run_scaffold(root, "--trellis", env=env)

            self.assertEqual(result.returncode, 0, result.stderr)
            config = (root / ".trellis" / "config.yaml").read_text(encoding="utf-8")
            self.assertIn("nested:\n  session_auto_commit: true", config)
            self.assertEqual(len(re.findall(r"(?m)^session_auto_commit\s*:", config)), 1)
            self.assertIn("session_auto_commit: false", config)

    def test_trellis_missing_command_still_scaffolds_normal_dxm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "no-trellis"
            bin_dir = Path(tmp) / "empty-bin"
            bin_dir.mkdir()
            env = os.environ.copy()
            env["PATH"] = str(bin_dir)

            result = self.run_scaffold(root, "--trellis", env=env)

            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertIn("missing-command: trellis init --codex", result.stdout)
            self.assertIn("DXM_SCAFFOLDED_TRELLIS_UNAVAILABLE", result.stdout)
            self.assertNotIn("Next: read AGENTS.md", result.stdout)
            self.assertTrue((root / "AGENTS.md").exists())
            self.assertFalse((root / ".trellis").exists())

    def test_trellis_failed_exit_returns_nonzero_partial_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "failed-trellis"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir, exit_code=7)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            result = self.run_scaffold(root, "--trellis", env=env)

            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertIn("failed-exit-7: trellis init --codex", result.stdout)
            self.assertIn("DXM_SCAFFOLDED_TRELLIS_FAILED", result.stdout)
            self.assertNotIn("Next: read AGENTS.md", result.stdout)

    def test_trellis_failed_exit_never_prints_ready_even_if_artifacts_audit_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "failed-ready-looking-trellis"
            baseline = Path(tmp) / "baseline.json"
            self.write_baseline(baseline, root)
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir, exit_code=7)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            result = self.run_scaffold(root, "--baseline", str(baseline), "--trellis", env=env)

            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertIn("DXM scaffold status: PARTIAL", result.stdout)
            self.assertNotIn("DXM scaffold status: READY", result.stdout)

    def test_trellis_exit_zero_without_integration_is_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "false-zero-trellis"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir, create_trellis=False)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            result = self.run_scaffold(root, "--trellis", env=env)

            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertIn("incomplete-no-trellis-dir: trellis init --codex", result.stdout)
            self.assertIn("DXM_SCAFFOLDED_TRELLIS_FAILED", result.stdout)

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

    def test_dry_run_trellis_reports_post_init_safety_plan_for_fresh_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "dry-run-trellis-fresh"

            result = self.run_scaffold(root, "--trellis", "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(root.exists())
            self.assertIn("would-run: trellis init --codex", result.stdout)
            self.assertIn("would-apply-after-trellis-init: AGENTS.md", result.stdout)
            self.assertIn("would-apply-after-trellis-init: 项目开发规范（AI协作）.md", result.stdout)
            self.assertIn("would-apply-after-trellis-init: .trellis/config.yaml session_auto_commit", result.stdout)
            self.assertIn("would-apply-after-trellis-init: .agents/skills/trellis-start/SKILL.md DXM Step 0", result.stdout)
            self.assertIn("would-apply-after-trellis-init: .trellis/workflow.md DXM no-task routing", result.stdout)

    def test_refresh_blocks_updates_existing_trellis_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "refresh-trellis"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            first = self.run_scaffold(root, "--trellis", env=env)
            self.assertEqual(first.returncode, 0, first.stderr)

            agents = root / "AGENTS.md"
            agents_text = agents.read_text(encoding="utf-8")
            agents.write_text(
                re.sub(
                    r"<!-- DXM-TRELLIS:START -->.*?<!-- DXM-TRELLIS:END -->",
                    "<!-- DXM-TRELLIS:START -->\nOLD TRELLIS ROUTING\n<!-- DXM-TRELLIS:END -->",
                    agents_text,
                    flags=re.S,
                ),
                encoding="utf-8",
                newline="\n",
            )

            trellis_start = root / ".agents" / "skills" / "trellis-start" / "SKILL.md"
            trellis_start_text = trellis_start.read_text(encoding="utf-8")
            trellis_start.write_text(
                re.sub(
                    r"<!-- DXM-TRELLIS-START-STEP0:START -->.*?<!-- DXM-TRELLIS-START-STEP0:END -->",
                    "<!-- DXM-TRELLIS-START-STEP0:START -->\nOLD STEP0\n<!-- DXM-TRELLIS-START-STEP0:END -->",
                    trellis_start_text,
                    flags=re.S,
                ),
                encoding="utf-8",
                newline="\n",
            )

            workflow = root / ".trellis" / "workflow.md"
            workflow_text = workflow.read_text(encoding="utf-8")
            workflow.write_text(
                re.sub(
                    r"<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:START -->.*?<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:END -->",
                    "<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:START -->\nOLD WORKFLOW OVERRIDE\n<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:END -->",
                    workflow_text,
                    flags=re.S,
                ),
                encoding="utf-8",
                newline="\n",
            )

            result = self.run_scaffold(root, "--trellis", "--refresh-blocks", env=env)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("refreshed-managed-block: AGENTS.md", result.stdout)
            self.assertIn("refreshed-managed-block: .agents/skills/trellis-start/SKILL.md DXM Step 0", result.stdout)
            self.assertIn("refreshed-managed-block: .trellis/workflow.md DXM no-task routing", result.stdout)
            self.assertNotIn("OLD TRELLIS ROUTING", agents.read_text(encoding="utf-8"))
            self.assertNotIn("OLD STEP0", trellis_start.read_text(encoding="utf-8"))
            self.assertNotIn("OLD WORKFLOW OVERRIDE", workflow.read_text(encoding="utf-8"))

    def test_trellis_start_marker_without_end_marker_fails_before_mutating_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "trellis-broken-marker"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            first = self.run_scaffold(root, "--trellis", env=env)
            self.assertEqual(first.returncode, 0, first.stderr)
            agents = root / "AGENTS.md"
            trellis_start = root / ".agents" / "skills" / "trellis-start" / "SKILL.md"
            trellis_start.write_text(
                "manual\n<!-- DXM-TRELLIS-START-STEP0:START -->\npartial\n",
                encoding="utf-8",
                newline="\n",
            )
            agents_before = agents.read_bytes()

            result = self.run_scaffold(root, "--trellis", "--refresh-blocks", env=env)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("incomplete managed block", result.stderr)
            self.assertEqual(agents.read_bytes(), agents_before)

    def test_inventory_depth_can_include_nested_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "inventory-depth"
            (root / "src" / "app").mkdir(parents=True)
            (root / "src" / "app" / "main.py").write_text("print('ok')\n", encoding="utf-8")

            result = self.run_scaffold(root, "--inventory-depth", "2")

            self.assertEqual(result.returncode, 0, result.stderr)
            structure = (root / "项目文件结构说明.md").read_text(encoding="utf-8")
            self.assertRegex(structure, r"`src/`：项目目录")
            self.assertRegex(structure, r"`src/app/`：项目目录")
            self.assertNotRegex(structure, r"`src/app/main\\.py`")

    def test_self_test_runs_packaged_smoke_checks(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--self-test"],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DXM self-test OK", result.stdout)

    def test_self_test_is_installation_smoke_not_template_content_lock(self) -> None:
        module = self.load_scaffold_module()

        def minimal_template(name: str) -> str:
            if name == "AGENTS.md":
                return "<!-- DXM-RULES:START -->\nminimal agents\n<!-- DXM-RULES:END -->\n"
            return "<!-- DXM-DOC-RULES:START -->\nminimal doc\n<!-- DXM-DOC-RULES:END -->\n"

        marker_only_blocks = {
            "TRELLIS_AGENTS_BLOCK": "<!-- DXM-TRELLIS:START -->\nminimal\n<!-- DXM-TRELLIS:END -->\n",
            "TRELLIS_DEV_RULES_BLOCK": "<!-- DXM-TRELLIS:START -->\nminimal\n<!-- DXM-TRELLIS:END -->\n",
            "TRELLIS_CHAIN_BLOCK": "<!-- DXM-TRELLIS:START -->\nminimal\n<!-- DXM-TRELLIS:END -->\n",
            "TRELLIS_START_STEP0_BLOCK": "<!-- DXM-TRELLIS-START-STEP0:START -->\nminimal\n<!-- DXM-TRELLIS-START-STEP0:END -->\n",
            "TRELLIS_WORKFLOW_OVERRIDE_BLOCK": "<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:START -->\nminimal\n<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:END -->\n",
        }
        module.read_template = minimal_template
        for name, value in marker_only_blocks.items():
            setattr(module, name, value)

        module.run_self_test()

    def test_broad_root_guard_requires_explicit_override(self) -> None:
        module = self.load_scaffold_module()

        broad_root = Path(Path.cwd().anchor)
        self.assertTrue(module.is_broad_root(broad_root))
        self.assertFalse(module.is_broad_root(Path.cwd()))

    def test_existing_file_root_is_rejected_cleanly_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "not-a-directory"
            root.write_text("preserve me\n", encoding="utf-8")

            result = self.run_scaffold(root, "--mode", "scaffold-only")

            self.assertEqual(result.returncode, 2)
            self.assertIn("project root must be a directory", result.stderr.lower())
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(root.read_text(encoding="utf-8"), "preserve me\n")

    def test_scaffold_only_rejects_file_ancestor_before_creating_any_docs(self) -> None:
        for extra_args in ((), ("--dry-run",)):
            with self.subTest(extra_args=extra_args), tempfile.TemporaryDirectory() as tmp:
                blocker = Path(tmp) / "not-a-directory"
                blocker.write_text("preserve me\n", encoding="utf-8")
                root = blocker / "child"

                result = self.run_scaffold(root, "--mode", "scaffold-only", *extra_args)

                self.assertEqual(result.returncode, 2)
                self.assertIn("project root must be a directory", result.stderr.lower())
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(blocker.read_text(encoding="utf-8"), "preserve me\n")
                self.assertFalse(root.exists())

    def test_init_rejects_file_ancestor_before_creating_any_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            blocker = root / ".dxm"
            blocker.write_text("preserve me\n", encoding="utf-8")
            baseline = Path(tmp) / "baseline.json"
            self.write_baseline(baseline, root)

            result = self.run_scaffold(root, "--mode", "init", "--baseline", str(baseline))

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("unsafe managed path", result.stderr.lower())
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(blocker.read_text(encoding="utf-8"), "preserve me\n")
            self.assertFalse(any((root / name).exists() for name in DXM_FILES))

    def test_trellis_rejects_file_ancestors_before_creating_any_docs(self) -> None:
        for blocker_name in (".trellis", ".agents"):
            with self.subTest(blocker=blocker_name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "project"
                root.mkdir()
                blocker = root / blocker_name
                blocker.write_text("preserve me\n", encoding="utf-8")

                result = self.run_scaffold(root, "--trellis")

                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("unsafe managed path", result.stderr.lower())
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(blocker.read_text(encoding="utf-8"), "preserve me\n")
                self.assertFalse(any((root / name).exists() for name in DXM_FILES))

    def test_trellis_dry_run_rejects_impossible_ancestor_instead_of_promising_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            blocker = root / ".trellis"
            blocker.write_text("preserve me\n", encoding="utf-8")

            result = self.run_scaffold(root, "--trellis", "--dry-run")

            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("unsafe managed path", result.stderr.lower())
            self.assertNotIn("would-run", result.stdout)
            self.assertEqual(blocker.read_text(encoding="utf-8"), "preserve me\n")
            self.assertFalse(any((root / name).exists() for name in DXM_FILES))

    def test_trellis_missing_start_skill_is_reported_not_fabricated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "missing-start"
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            write_fake_trellis(bin_dir, create_start_skill=False)
            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")

            result = self.run_scaffold(root, "--trellis", env=env)

            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertIn("missing-trellis-start-skill", result.stdout)
            self.assertIn("DXM_SCAFFOLDED_TRELLIS_FAILED", result.stdout)
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

            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertIn("timeout: trellis init --codex", result.stdout)
            self.assertIn("DXM_SCAFFOLDED_TRELLIS_FAILED", result.stdout)
            self.assertLess(elapsed, 4.0)

    def test_trellis_launch_oserror_is_structured_without_traceback(self) -> None:
        module = self.load_scaffold_module()

        def fail_launch(*_args, **_kwargs):
            raise OSError("synthetic launch failure")

        original_which = module.shutil.which
        original_popen = module.subprocess.Popen
        try:
            module.shutil.which = lambda _name: "trellis"
            module.subprocess.Popen = fail_launch
            status, output = module.run_trellis_init(Path.cwd(), "developer", 1)
        finally:
            module.shutil.which = original_which
            module.subprocess.Popen = original_popen

        self.assertEqual(status, "failed-launch-OSError")
        self.assertIn("launch failed", output.lower())
        self.assertNotIn("synthetic launch failure", output)

    def test_trellis_launch_failure_maps_to_trellis_failed_exit(self) -> None:
        module = self.load_scaffold_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            module.run_trellis_init = lambda *_args, **_kwargs: (
                "failed-launch-OSError",
                "trellis init launch failed: OSError",
            )
            class ReadyAudit:
                state = module.READY
                issues: tuple[str, ...] = ()
                exit_code = 0

            module.audit_project = lambda *_args, **_kwargs: ReadyAudit()
            stdout = io.StringIO()
            stderr = io.StringIO()
            old_argv = sys.argv
            try:
                sys.argv = [str(SCRIPT), "--root", str(root), "--trellis"]
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = module.main()
            finally:
                sys.argv = old_argv

            combined = stdout.getvalue() + stderr.getvalue()
            self.assertEqual(exit_code, 4, combined)
            self.assertIn("failed-launch-OSError", stdout.getvalue())
            self.assertIn("DXM_SCAFFOLDED_TRELLIS_FAILED", stdout.getvalue())
            self.assertNotIn("Traceback", combined)
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

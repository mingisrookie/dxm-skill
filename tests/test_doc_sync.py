"""Anti-drift tripwire: SKILL.md, installed templates, and the scaffold script
describe the same DXM contract from three places. These tests fail loudly when
one side changes without the others, instead of relying on reviewers to
remember the sync rule."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "dxm"
SKILL_MD = SKILL_DIR / "SKILL.md"
TEMPLATE_DIR = SKILL_DIR / "assets" / "templates"
AGENTS_TEMPLATE = TEMPLATE_DIR / "AGENTS.md.template"
SCRIPT_PATH = SKILL_DIR / "scripts" / "scaffold_dxm.py"
CHAIN_DOC = REPO_ROOT / "项目完整链路说明.md"
OPENAI_METADATA = SKILL_DIR / "agents" / "openai.yaml"
README = REPO_ROOT / "README.md"
GITIGNORE = REPO_ROOT / ".gitignore"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

sys.path.insert(0, str(SCRIPT_PATH.parent))
import scaffold_dxm  # noqa: E402

# Routing labels that SKILL.md and the installed AGENTS.md must both keep,
# because scaffolded projects may be driven by agents without the dxm skill.
GRILL_MODE_LABELS = ("grill-with-docs", "new-project-grill", "lightweight-grill")
OPTIONAL_SIBLING_SKILLS = ("grilling", "grill-with-docs", "grill-me", "domain-modeling")
CORE_SELF_CONTAINED_CONTRACT = "Core DXM must remain usable without sibling interview skills."
TRELLIS_INIT_DOC = "trellis init --codex -u <developer> -y --skip-existing"
TRELLIS_INIT_IMPL = '"init", "--codex", "-u", developer, "-y", "--skip-existing"'


def parse_two_level_yaml_mapping(text: str) -> dict[str, object]:
    """Parse the small mapping subset used by agents/openai.yaml."""
    document: dict[str, object] = {}
    current_mapping: dict[str, str] | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(
            r"(?P<indent> *)(?P<key>[a-z][a-z0-9_]*):(?:\s*(?P<value>.*))?",
            raw_line,
        )
        if match is None:
            raise ValueError(f"unsupported YAML syntax on line {line_number}")

        indent = len(match.group("indent"))
        key = match.group("key")
        value = (match.group("value") or "").strip()
        if indent == 0:
            if key in document:
                raise ValueError(f"duplicate top-level key: {key}")
            if value:
                document[key] = value
                current_mapping = None
            else:
                current_mapping = {}
                document[key] = current_mapping
            continue
        if indent != 2 or current_mapping is None or not value:
            raise ValueError(f"invalid two-level mapping on line {line_number}")
        if key in current_mapping:
            raise ValueError(f"duplicate nested key: {key}")
        if len(value) < 2 or value[0] not in "\"'" or value[-1] != value[0]:
            raise ValueError(f"nested scalar must be quoted on line {line_number}")
        current_mapping[key] = value[1:-1]

    return document


class DocSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = SKILL_MD.read_text(encoding="utf-8")
        cls.agents_template_text = AGENTS_TEMPLATE.read_text(encoding="utf-8")
        cls.script_text = SCRIPT_PATH.read_text(encoding="utf-8")
        cls.chain_doc_text = CHAIN_DOC.read_text(encoding="utf-8")
        cls.openai_metadata_text = OPENAI_METADATA.read_text(encoding="utf-8")
        cls.readme_text = README.read_text(encoding="utf-8")

    def test_generated_filenames_listed_in_skill_and_agents_template(self) -> None:
        for name in scaffold_dxm.FILES:
            self.assertIn(name, self.skill_text, f"SKILL.md no longer lists generated file {name}")
            self.assertIn(name, self.agents_template_text, f"AGENTS.md.template no longer lists generated file {name}")

    def test_templates_on_disk_match_canonical_file_list(self) -> None:
        on_disk = {p.name[: -len(".template")] for p in TEMPLATE_DIR.glob("*.template")}
        self.assertEqual(on_disk, set(scaffold_dxm.FILES), "assets/templates/ drifted from scaffold_dxm.FILES")

    def test_grill_mode_labels_present_in_skill_and_agents_template(self) -> None:
        for label in GRILL_MODE_LABELS:
            self.assertIn(label, self.skill_text, f"SKILL.md dropped grill mode label {label}")
            self.assertIn(label, self.agents_template_text, f"AGENTS.md.template dropped grill mode label {label}")

    def test_optional_sibling_skills_stay_outside_core_install(self) -> None:
        self.assertIn(CORE_SELF_CONTAINED_CONTRACT, self.skill_text)
        for skill in OPTIONAL_SIBLING_SKILLS:
            entry = REPO_ROOT / "skills" / skill / "SKILL.md"
            self.assertTrue(entry.is_file(), f"optional sibling skill {skill!r} is missing")
            self.assertFalse(
                (SKILL_DIR / skill).exists(),
                f"optional sibling skill {skill!r} must not become part of the core skills/dxm package",
            )

    def test_trellis_init_command_documented_and_implemented(self) -> None:
        self.assertIn(TRELLIS_INIT_DOC, self.skill_text, "SKILL.md no longer documents the exact trellis init command")
        self.assertIn(TRELLIS_INIT_IMPL, self.script_text, "scaffold_dxm.py changed the trellis init argv; update SKILL.md too")

    def test_local_dogfood_state_is_not_a_release_artifact(self) -> None:
        ignored = set(GITIGNORE.read_text(encoding="utf-8").splitlines())
        for path in (".codex/", ".dxm/", ".trellis/"):
            self.assertIn(path, ignored, f"local dogfood state {path} could be published by git add -A")

    def test_chain_doc_does_not_claim_unconfigured_ci_steps(self) -> None:
        ci_text = CI_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python -m unittest discover -s tests -v", ci_text)
        self.assertIn("python skills/dxm/scripts/scaffold_dxm.py --self-test", ci_text)
        ci_section = self.chain_doc_text.split("### 2.5 测试 / CI 模式", 1)[1].split("## 3.", 1)[0]
        ci_commands = ci_section.split("```bash", 1)[1].split("```", 1)[0]
        self.assertNotIn("validate_dxm.py audit", ci_commands)
        self.assertIn("本地发布前", ci_section)

    def test_force_flag_warning_matches_actual_overwrite_scope(self) -> None:
        self.assertIn("Overwrite existing DXM target files", self.skill_text)
        self.assertNotIn("Overwrite generated files", self.skill_text)

    def test_dogfood_chain_doc_describes_real_repo_pipeline(self) -> None:
        for expected in [
            "skills/dxm/SKILL.md",
            "skills/dxm/scripts/scaffold_dxm.py",
            "skills/dxm/assets/templates/",
            "tests/test_scaffold_dxm.py",
            "tests/test_doc_sync.py",
            "python -m unittest discover -s tests -v",
        ]:
            self.assertIn(expected, self.chain_doc_text)
        self.assertNotIn("首次 `/dxm` 生成后，应在这里写清楚", self.chain_doc_text)

    def test_openai_metadata_uses_current_interface_schema(self) -> None:
        metadata = parse_two_level_yaml_mapping(self.openai_metadata_text)
        interface = metadata.get("interface")
        self.assertIsInstance(interface, dict)
        assert isinstance(interface, dict)
        self.assertTrue(
            {"display_name", "short_description", "default_prompt"}.issubset(interface)
        )
        self.assertTrue(
            set(interface).issubset(
                {
                    "display_name",
                    "short_description",
                    "default_prompt",
                    "icon_small",
                    "icon_large",
                    "brand_color",
                }
            ),
            "interface contains unsupported metadata keys",
        )
        self.assertTrue(
            {"display_name", "short_description", "default_prompt"}.isdisjoint(metadata),
            "UI metadata must be nested under interface",
        )
        self.assertNotIn("skill_description", metadata)
        self.assertGreaterEqual(len(interface["short_description"]), 25)
        self.assertLessEqual(len(interface["short_description"]), 64)

    def test_openai_metadata_parser_rejects_duplicate_keys(self) -> None:
        duplicate_cases = {
            "nested": (
                '\n'.join(
                    [
                        "interface:",
                        '  display_name: "DXM"',
                        '  display_name: "duplicate"',
                    ]
                ),
                "duplicate nested key: display_name",
            ),
            "top-level": (
                '\n'.join(
                    [
                        "interface:",
                        '  display_name: "DXM"',
                        "interface:",
                    ]
                ),
                "duplicate top-level key: interface",
            ),
        }
        for name, (metadata, message) in duplicate_cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, message):
                parse_two_level_yaml_mapping(metadata)

    def test_openai_default_prompt_explicitly_invokes_dxm(self) -> None:
        metadata = parse_two_level_yaml_mapping(self.openai_metadata_text)
        interface = metadata["interface"]
        assert isinstance(interface, dict)
        self.assertIn("$dxm", interface["default_prompt"])

    def test_all_generated_core_docs_embed_current_contract_marker(self) -> None:
        marker = "<!-- DXM-CONTRACT:1 -->"
        template_dir = REPO_ROOT / "skills" / "dxm" / "assets" / "templates"
        for template in sorted(template_dir.glob("*.template")):
            content = template.read_text(encoding="utf-8")
            self.assertEqual(content.count(marker), 1, str(template))

    def test_readme_distinguishes_core_from_optional_sibling_skills(self) -> None:
        self.assertIn("### 核心 DXM", self.readme_text)
        self.assertIn("### 可选的相邻技能", self.readme_text)
        self.assertIn("核心 DXM 不依赖相邻技能", self.readme_text)
        self.assertIn("以内联 0–3 个阻塞问题", self.readme_text)
        self.assertIn("bounded router 可在其描述明确匹配时", self.readme_text)
        self.assertIn("full/exhaustive grilling 需要用户明确要求", self.readme_text)
        self.assertNotIn("先 `grilling` / `grill-with-docs`", self.readme_text)
        for path in (
            "skills/grilling",
            "skills/grill-with-docs",
            "skills/domain-modeling",
            "skills/grill-me",
        ):
            self.assertIn(path, self.readme_text)

    def test_readme_documents_persisted_contract_and_validator_cli(self) -> None:
        for expected in (
            ".dxm/project.json",
            "<!-- DXM-CHECK:PASS -->",
            "--baseline <baseline.json>",
            "validate_dxm.py audit --root /path/to/project --json",
            "validate_dxm.py baseline --file /path/to/baseline.json --json",
            "task.py archive <task> --no-commit",
            "validate_dxm.py receipt --root /path/to/project --file .trellis/tasks/archive/<YYYY-MM>/<task>/completion.json --json",
            "| `READY` | `0` |",
            "| `BROKEN` | `2` |",
            "| `PARTIAL` | `3` |",
            "| `ABSENT` | `4` |",
            'Copy-Item -Recurse -LiteralPath "skills/dxm" -Destination $core',
            'python "$core/scripts/scaffold_dxm.py" --self-test',
            'python "$core/scripts/validate_dxm.py" --version',
        ):
            self.assertIn(expected, self.readme_text)

    def test_shared_project_docs_use_portable_root_projection(self) -> None:
        template_dir = REPO_ROOT / "skills" / "dxm" / "assets" / "templates"
        for name in (
            "项目开发规范（AI协作）.md",
            "项目完整链路说明.md",
            "项目文件结构说明.md",
            "开发者AI开发与PR提交流程.md",
        ):
            template = (template_dir / f"{name}.template").read_text(encoding="utf-8")
            dogfood = (REPO_ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("{{project_root}}", template, name)
            self.assertIn(".dxm/project.json", template, name)
            self.assertIn(".dxm/project.json", dogfood, name)

    def test_core_only_copy_passes_self_test_and_validator_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            installed_core = temp_root / "installed" / "dxm"
            shutil.copytree(SKILL_DIR, installed_core)
            self.assertFalse((installed_core / "grilling").exists())

            self_test = subprocess.run(
                [sys.executable, str(installed_core / "scripts" / "scaffold_dxm.py"), "--self-test"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(self_test.returncode, 0, self_test.stdout + self_test.stderr)

            empty_project = temp_root / "project"
            empty_project.mkdir()
            audit = subprocess.run(
                [
                    sys.executable,
                    str(installed_core / "scripts" / "validate_dxm.py"),
                    "audit",
                    "--root",
                    str(empty_project),
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(audit.returncode, 4, audit.stdout + audit.stderr)
            self.assertEqual(json.loads(audit.stdout)["state"], "ABSENT")


if __name__ == "__main__":
    unittest.main()

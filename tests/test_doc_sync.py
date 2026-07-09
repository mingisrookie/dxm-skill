"""Anti-drift tripwire: SKILL.md, installed templates, and the scaffold script
describe the same DXM contract from three places. These tests fail loudly when
one side changes without the others, instead of relying on reviewers to
remember the sync rule."""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "dxm"
SKILL_MD = SKILL_DIR / "SKILL.md"
TEMPLATE_DIR = SKILL_DIR / "assets" / "templates"
AGENTS_TEMPLATE = TEMPLATE_DIR / "AGENTS.md.template"
SCRIPT_PATH = SKILL_DIR / "scripts" / "scaffold_dxm.py"
CHAIN_DOC = REPO_ROOT / "项目完整链路说明.md"

sys.path.insert(0, str(SCRIPT_PATH.parent))
import scaffold_dxm  # noqa: E402

# Routing labels that SKILL.md and the installed AGENTS.md must both keep,
# because scaffolded projects may be driven by agents without the dxm skill.
GRILL_MODE_LABELS = ("grill-with-docs", "new-project-grill", "lightweight-grill")
ROUTED_SKILLS = ("grilling", "grill-with-docs", "grill-me", "domain-modeling")
TRELLIS_INIT_DOC = "trellis init --codex -u <developer> -y --skip-existing"
TRELLIS_INIT_IMPL = '"init", "--codex", "-u", developer, "-y", "--skip-existing"'


class DocSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = SKILL_MD.read_text(encoding="utf-8")
        cls.agents_template_text = AGENTS_TEMPLATE.read_text(encoding="utf-8")
        cls.script_text = SCRIPT_PATH.read_text(encoding="utf-8")
        cls.chain_doc_text = CHAIN_DOC.read_text(encoding="utf-8")

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

    def test_routed_skills_exist_in_repo(self) -> None:
        for skill in ROUTED_SKILLS:
            entry = REPO_ROOT / "skills" / skill / "SKILL.md"
            self.assertTrue(entry.is_file(), f"SKILL.md routes to skill {skill!r} but {entry} is missing")

    def test_trellis_init_command_documented_and_implemented(self) -> None:
        self.assertIn(TRELLIS_INIT_DOC, self.skill_text, "SKILL.md no longer documents the exact trellis init command")
        self.assertIn(TRELLIS_INIT_IMPL, self.script_text, "scaffold_dxm.py changed the trellis init argv; update SKILL.md too")

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


if __name__ == "__main__":
    unittest.main()

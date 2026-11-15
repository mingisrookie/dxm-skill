"""Static guards for the skill entry points; NOT live model evaluations."""
from pathlib import Path
import re
import unittest

from test_skill_package import metadata

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
CORE = SKILLS / "dxm"


class AmbientRuleTests(unittest.TestCase):
    def setUp(self):
        self.entry = (CORE / "SKILL.md").read_text(encoding="utf-8")

    def test_descriptions_name_user_situations_and_stay_short(self):
        for path in SKILLS.glob("*/SKILL.md"):
            description = metadata(path)["description"]
            with self.subTest(skill=path.parent.name):
                self.assertLessEqual(len(description), 120)
                self.assertRegex(description, "时使用")
        core = metadata(CORE / "SKILL.md")["description"]
        self.assertIn("/dxm", core)
        self.assertIn("grill", core)

    def test_only_one_interview_skill_claims_grill(self):
        owners = [p.parent.name for p in SKILLS.glob("*/SKILL.md")
                  if p.parent.name != "dxm" and "grill" in metadata(p)["description"].lower()]
        self.assertEqual(owners, ["grilling"])

    def test_core_covers_the_three_gaps_and_boundaries(self):
        headings = re.findall(r"^## (.+)$", self.entry, re.M)
        self.assertEqual(headings, ["项目背景", "关键决策", "交付证据", "边界"])

    def test_section_links_have_real_targets(self):
        links = re.findall(r"\[[^\]]+\]\(([^)#]+)#([^)]+)\)", self.entry)
        self.assertTrue(links)
        for filename, anchor in links:
            target = (CORE / filename).read_text(encoding="utf-8")
            self.assertIn(anchor, re.findall(r"^## (.+)$", target, re.M))

    def test_bold_markers_render_next_to_cjk_punctuation(self):
        # "**标题：**正文" is not emphasis in CommonMark; keep punctuation outside.
        for path in SKILLS.rglob("*.md"):
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"[：，。；]\*\*\S", path.name)

    def test_model_names_are_not_runtime_switches(self):
        for path in SKILLS.rglob("SKILL.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?i)\b(?:gpt|claude|gemini|opus|sonnet|haiku|fable)\b")

    def test_core_remains_small(self):
        # Maintenance budgets in UTF-8 bytes, not claims about model token cost.
        self.assertLessEqual((CORE / "SKILL.md").stat().st_size, 3000)
        self.assertLessEqual((CORE / "references/dxm-method.md").stat().st_size, 3000)
        self.assertLessEqual((CORE / "assets/templates/AGENTS.md.template").stat().st_size, 1400)

    def test_implicit_invocation_is_allowed_without_extra_runtime(self):
        text = (CORE / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: true", text)
        self.assertNotIn("dependencies:", text)
        self.assertFalse((CORE / "scripts").exists())
        self.assertFalse((CORE / "hooks").exists())


if __name__ == "__main__":
    unittest.main()

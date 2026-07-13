"""Behavior-level contract tests for DXM policy and routed interview skills."""

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DXM_SKILL = REPO_ROOT / "skills" / "dxm" / "SKILL.md"
AGENTS_TEMPLATE = REPO_ROOT / "skills" / "dxm" / "assets" / "templates" / "AGENTS.md.template"
DEV_TEMPLATE = (
    REPO_ROOT
    / "skills"
    / "dxm"
    / "assets"
    / "templates"
    / "项目开发规范（AI协作）.md.template"
)
DXM_METHOD = REPO_ROOT / "skills" / "dxm" / "references" / "dxm-method.md"
GRILLING_SKILL = REPO_ROOT / "skills" / "grilling" / "SKILL.md"
GRILL_WITH_DOCS_SKILL = REPO_ROOT / "skills" / "grill-with-docs" / "SKILL.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter_keys(text: str) -> set[str]:
    match = re.match(r"\A---\n(.*?)\n---(?:\n|\Z)", text, flags=re.DOTALL)
    if match is None:
        return set()
    return {
        line.split(":", 1)[0].strip()
        for line in match.group(1).splitlines()
        if line.strip() and not line.lstrip().startswith("#") and ":" in line
    }


class PolicyContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dxm = read(DXM_SKILL)
        cls.agents = read(AGENTS_TEMPLATE)
        cls.dev = read(DEV_TEMPLATE)
        cls.method = read(DXM_METHOD)
        cls.grilling = read(GRILLING_SKILL)
        cls.grill_with_docs = read(GRILL_WITH_DOCS_SKILL)

    def assert_contains_all(self, text: str, snippets: tuple[str, ...], source: str) -> None:
        for snippet in snippets:
            with self.subTest(source=source, snippet=snippet):
                self.assertIn(snippet, text, f"{source} is missing policy token {snippet!r}")

    def test_four_modes_and_root_scope_lock_are_shared(self) -> None:
        mode_tokens = ("`audit`", "`init`", "`task`", "`scaffold-only`")
        for source, text in {
            "DXM skill": self.dxm,
            "AGENTS template": self.agents,
            "development template": self.dev,
            "DXM method": self.method,
        }.items():
            self.assert_contains_all(text, mode_tokens, source)
            self.assertIn("root/mode/scope lock", text, f"{source} does not define the shared lock")

        self.assertIn("before the first write", self.dxm)
        self.assertIn("首次写入前", self.agents)
        self.assertIn("首次写入前", self.dev)

    def test_audit_mode_is_strictly_read_only(self) -> None:
        self.assert_contains_all(
            self.dxm,
            ("no scaffold", "no Trellis task", "no runtime mutation", "no file write"),
            "DXM skill audit mode",
        )
        audit_prohibitions = ("不 scaffold", "不创建 Trellis task", "不改变运行态", "不写文件")
        self.assert_contains_all(self.agents, audit_prohibitions, "AGENTS template audit mode")
        self.assert_contains_all(self.dev, audit_prohibitions, "development template audit mode")

    def test_scaffold_write_modes_are_explicitly_locked(self) -> None:
        for source, text in {
            "DXM skill": self.dxm,
            "AGENTS template": self.agents,
            "development template": self.dev,
            "DXM method": self.method,
        }.items():
            self.assertIn("--mode init", text, source)
            self.assertIn("--mode scaffold-only", text, source)
        self.assertIn("--mode init` rejects a missing baseline before any project write", self.dxm)

    def test_default_bootstrap_is_bounded_and_local_evidence_first(self) -> None:
        for source, text in {
            "DXM skill": self.dxm,
            "DXM method": self.method,
            "grill-with-docs": self.grill_with_docs,
        }.items():
            self.assert_contains_all(text, ("0–3", "one batch", "local evidence first"), source)

        for source, text in {
            "AGENTS template": self.agents,
            "development template": self.dev,
        }.items():
            self.assert_contains_all(text, ("0–3", "单批", "本地证据优先"), source)
            self.assert_contains_all(text, ("第一性原理", "质疑隐藏假设"), source)
            self.assertIn("按推荐走", text)
            self.assertIn("直接做", text)

        for source, text in {
            "DXM skill": self.dxm,
            "DXM method": self.method,
            "grill-with-docs": self.grill_with_docs,
        }.items():
            lowered = text.lower()
            self.assertIn("first principles", lowered, source)
            self.assertIn("challenge hidden assumptions", lowered, source)

    def test_full_grilling_is_explicit_opt_in_only(self) -> None:
        for source, text in {
            "DXM skill": self.dxm,
            "AGENTS template": self.agents,
            "development template": self.dev,
            "DXM method": self.method,
            "grilling": self.grilling,
            "grill-with-docs": self.grill_with_docs,
        }.items():
            self.assertIn("explicit opt-in", text, f"{source} does not protect exhaustive grilling")

        self.assertNotIn("relentlessly", self.grilling.lower())
        self.assertNotIn("project-grill/new-project-grill/lightweight-grill", self.grilling)
        self.assertIn("explicitly", self.grilling.split("---", 2)[1].lower())

    def test_routed_skill_frontmatter_uses_supported_keys_only(self) -> None:
        for path, text in {
            GRILLING_SKILL: self.grilling,
            GRILL_WITH_DOCS_SKILL: self.grill_with_docs,
        }.items():
            self.assertEqual(frontmatter_keys(text), {"name", "description"}, str(path))

    def test_domain_modeling_writes_only_when_project_facts_change(self) -> None:
        self.assert_contains_all(
            self.grill_with_docs,
            ("domain-modeling", "only when", "terminology", "ADR", "do not write"),
            "grill-with-docs",
        )

    def test_generated_rules_define_the_evidence_matrix(self) -> None:
        self.assertIn("evidence matrix", self.agents)
        self.assert_contains_all(
            self.dev,
            (
                "evidence matrix",
                "acceptance_criteria[].id",
                "acceptance_criteria[].evidence_kinds",
                "service",
                "listener",
                "health",
                "original-symptom E2E",
                "UI",
                "approved reference",
                "rendered screenshot",
                "navigation/hit-test",
                "regression",
                "online/deployed",
                "entry-point readback",
                "restart durability",
                "restart/recovery",
            ),
            "development template evidence matrix",
        )

    def test_completion_receipt_contract_covers_claims_and_side_effects(self) -> None:
        for source, text in {
            "DXM skill": self.dxm,
            "AGENTS template": self.agents,
            "development template": self.dev,
            "DXM method": self.method,
        }.items():
            self.assertIn("completion receipt", text, f"{source} dropped the completion gate")

        self.assert_contains_all(
            self.dev,
            (
                "schema_version",
                "workflow_mode",
                "project_root",
                "requirements",
                "evidence_kinds",
                "evidence",
                "adversarial_check",
                "quality_checks",
                "docs",
                "encoding",
                "secrets",
                "rollback",
                "trellis",
                "check_passed",
                "finished",
                "commit_performed",
                "push_performed",
                "archive <task> --no-commit",
                ".trellis/tasks/archive/<YYYY-MM>/<task>/completion.json",
                "receipt --root \"<project-root>\" --file .trellis/tasks/archive/<YYYY-MM>/<task>/completion.json",
            ),
            "development template completion receipt",
        )

        for source, text in {
            "DXM skill": self.dxm,
            "AGENTS template": self.agents,
            "development template": self.dev,
            "DXM method": self.method,
        }.items():
            self.assertIn("archive", text, f"{source} must require archived Trellis truth")
            self.assertIn("--no-commit", text, f"{source} must preserve the Git authorization boundary")
            self.assertIn(
                "<!-- DXM-CHECK:PASS -->",
                text,
                f"{source} must require the machine-verifiable Trellis check verdict",
            )
            self.assertNotIn(
                ".trellis/tasks/<task>/completion.json",
                text,
                f"{source} still points the final receipt at an active task",
            )

    def test_long_term_docs_are_loaded_selectively(self) -> None:
        for source, text in {
            "DXM skill": self.dxm,
            "AGENTS template": self.agents,
            "development template": self.dev,
            "DXM method": self.method,
        }.items():
            self.assertIn("selective docs", text, f"{source} dropped selective loading")
            self.assertIn("`AGENTS.md`", text)
            self.assertIn("always", text.lower())

        self.assertNotIn("Read or re-check the three project maintenance docs", self.dxm)
        self.assertNotIn("三份根目录长期文档", self.dev)


if __name__ == "__main__":
    unittest.main()

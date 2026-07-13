"""Behavior-level contracts bound to real DXM policy and validator assets."""

import json
import ntpath
import re
import sys
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "dxm"
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "dxm_workflow_cases.json"
SKILL_PATH = SKILL_DIR / "SKILL.md"
AGENTS_TEMPLATE = SKILL_DIR / "assets" / "templates" / "AGENTS.md.template"
DEV_TEMPLATE = SKILL_DIR / "assets" / "templates" / "项目开发规范（AI协作）.md.template"
SCRIPTS_DIR = SKILL_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
import dxm_contract  # noqa: E402


POLICY_ASSETS = {
    "skill": SKILL_PATH.read_text(encoding="utf-8"),
    "agents_template": AGENTS_TEMPLATE.read_text(encoding="utf-8"),
    "development_template": DEV_TEMPLATE.read_text(encoding="utf-8"),
}
REQUIRED_COVERAGE = {
    "audit",
    "init",
    "root_mismatch_windows",
    "root_mismatch_unc",
    "review_scope",
    "live_service_gate",
    "ui_gate",
}
VALID_MODES = {"audit", "init", "task", "scaffold-only"}
VALID_READINESS = {
    dxm_contract.ABSENT,
    dxm_contract.PARTIAL,
    dxm_contract.READY,
    dxm_contract.BROKEN,
}
VALID_PHASES = {
    "read_only",
    "clarification",
    "root_lock_failed",
    "scope_locked",
    "evidence_required",
}
EVIDENCE_POLICY_TERMS = {
    "listener": "listener",
    "health": "health",
    "original_symptom_e2e": "original-symptom e2e",
    "approved_reference": "approved reference",
    "rendered_screenshot": "rendered screenshot",
    "navigation_hit_test": "navigation/hit-test",
    "regression_check": "regression",
}


def normalize_root(root: str, flavor: str) -> str:
    if flavor == "posix":
        path = PurePosixPath(root)
        if not path.is_absolute():
            raise ValueError(f"POSIX root is not absolute: {root}")
        return path.as_posix()
    if flavor not in {"windows", "unc"}:
        raise ValueError(f"unsupported root flavor: {flavor}")
    path = PureWindowsPath(root)
    if not path.is_absolute():
        raise ValueError(f"Windows root is not absolute: {root}")
    return ntpath.normcase(ntpath.normpath(str(path)))


def extract_policy_modes(text: str) -> set[str]:
    return set(
        re.findall(
            r"(?m)^\| `(?P<mode>audit|init|task|scaffold-only)` \|",
            text,
        )
    )


def extract_mode_row(text: str, mode: str) -> str:
    match = re.search(rf"(?m)^\| `{re.escape(mode)}` \|.*$", text)
    if match is None:
        raise ValueError(f"policy asset has no {mode} row")
    return match.group(0)


def extract_question_limit(text: str) -> int:
    match = re.search(r"0\s*[–-]\s*(?P<limit>\d+).{0,40}(?:blocking|阻塞)", text, re.IGNORECASE)
    if match is None:
        raise ValueError("policy asset has no bounded-question contract")
    return int(match.group("limit"))


def iter_document_items(value: object, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield f"{path}.{key}", key, True
            yield from iter_document_items(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_document_items(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value, False


def privacy_violations(document: object) -> list[str]:
    violations: list[str] = []
    sensitive_key = re.compile(
        r"(?:^|_)(?:token|api_?key|secret|password|authorization)(?:$|_)",
        re.IGNORECASE,
    )
    value_patterns = (
        re.compile(r"/(?:Users|home)/", re.IGNORECASE),
        re.compile(r"https?://", re.IGNORECASE),
        re.compile(r"\bBearer\s+\S+", re.IGNORECASE),
        re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
        re.compile(
            r"\b(?:token|api[_-]?key|secret|password)\s*[:=]\s*\S+",
            re.IGNORECASE,
        ),
        re.compile(r"019[0-9a-f]{5}-[0-9a-f-]{27,}", re.IGNORECASE),
        re.compile(r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    )

    for path, item, is_key in iter_document_items(document):
        if is_key and sensitive_key.search(item):
            violations.append(f"{path}: sensitive key")
            continue
        if is_key:
            continue
        for pattern in value_patterns:
            if pattern.search(item):
                violations.append(f"{path}: matched {pattern.pattern}")
        if item.startswith("\\\\") and not item.lower().startswith(
            "\\\\synthetic-host\\synthetic-share\\"
        ):
            violations.append(f"{path}: non-synthetic UNC path")
        if re.match(r"^[A-Za-z]:\\", item) and not item.lower().startswith(
            "c:\\workspace\\synthetic-"
        ):
            violations.append(f"{path}: non-synthetic Windows path")
    return violations


class WorkflowCasesTest(unittest.TestCase):
    def load_fixture(self) -> dict:
        self.assertTrue(FIXTURE_PATH.is_file(), f"missing workflow fixture: {FIXTURE_PATH}")
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def cases_by_coverage(self) -> dict[str, dict]:
        document = self.load_fixture()
        return {case["coverage"]: case for case in document["cases"]}

    def test_fixture_schema_is_well_formed(self) -> None:
        document = self.load_fixture()
        self.assertEqual(set(document), {"schema_version", "synthetic", "description", "cases"})
        self.assertEqual(document["schema_version"], 1)
        self.assertIs(document["synthetic"], True)
        self.assertIsInstance(document["description"], str)
        self.assertTrue(document["description"].strip())
        self.assertIsInstance(document["cases"], list)
        self.assertTrue(document["cases"])

        ids: set[str] = set()
        for case in document["cases"]:
            self.assertEqual(set(case), {"id", "coverage", "input", "expected"})
            self.assertRegex(case["id"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
            self.assertNotIn(case["id"], ids)
            ids.add(case["id"])

            case_input = case["input"]
            self.assertEqual(
                set(case_input),
                {"request", "root_flavor", "canonical_root", "observed_root", "local_evidence"},
            )
            self.assertTrue(case_input["request"].strip())
            normalize_root(case_input["canonical_root"], case_input["root_flavor"])
            normalize_root(case_input["observed_root"], case_input["root_flavor"])
            self.assertIsInstance(case_input["local_evidence"], list)

            expected = case["expected"]
            self.assertEqual(
                set(expected),
                {
                    "mode",
                    "readiness",
                    "phase",
                    "write_allowed",
                    "scope",
                    "question_budget",
                    "local_evidence_first",
                    "evidence_gate",
                    "forbidden_actions",
                },
            )
            self.assertIn(expected["mode"], VALID_MODES)
            self.assertIn(expected["readiness"], VALID_READINESS)
            self.assertIn(expected["phase"], VALID_PHASES)
            self.assertIsInstance(expected["write_allowed"], bool)
            self.assertIsInstance(expected["scope"], list)
            self.assertIsInstance(expected["question_budget"], int)
            self.assertGreaterEqual(expected["question_budget"], 0)
            self.assertLessEqual(expected["question_budget"], 3)
            self.assertTrue(expected["local_evidence_first"])
            self.assertEqual(set(expected["evidence_gate"]), {"required", "insufficient_alone"})
            for field in ("scope", "forbidden_actions"):
                self.assertTrue(all(isinstance(item, str) and item for item in expected[field]))
            for field in ("required", "insufficient_alone"):
                evidence = expected["evidence_gate"][field]
                self.assertIsInstance(evidence, list)
                self.assertTrue(all(isinstance(item, str) and item for item in evidence))

    def test_fixture_is_declared_synthetic_and_privacy_clean(self) -> None:
        document = self.load_fixture()
        self.assertIs(document["synthetic"], True)
        self.assertEqual(privacy_violations(document), [])

    def test_privacy_scanner_rejects_private_paths_urls_and_credentials(self) -> None:
        unsafe_samples = (
            {"value": "/Users/person/project"},
            {"value": "/home/person/project"},
            {"value": "https://fixture.invalid/path"},
            {"value": "Bearer placeholder-value"},
            {"value": "sk-placeholder1234"},
            {"value": "token=placeholder-value"},
            {"api_key": "placeholder-value"},
            {"value": "\\\\private-host\\share\\project"},
        )
        for sample in unsafe_samples:
            with self.subTest(sample=sample):
                self.assertTrue(privacy_violations(sample))

    def test_required_workflow_coverage_is_present_once(self) -> None:
        document = self.load_fixture()
        coverage = [case["coverage"] for case in document["cases"]]
        self.assertEqual(set(coverage), REQUIRED_COVERAGE)
        self.assertEqual(len(coverage), len(set(coverage)))

    def test_fixture_modes_and_question_budgets_match_real_policy_assets(self) -> None:
        cases = self.load_fixture()["cases"]
        for name, text in POLICY_ASSETS.items():
            with self.subTest(asset=name):
                self.assertEqual(extract_policy_modes(text), VALID_MODES)
                policy_limit = extract_question_limit(text)
                self.assertEqual(policy_limit, 3)
                for case in cases:
                    self.assertLessEqual(case["expected"]["question_budget"], policy_limit)

    def test_fixture_readiness_comes_from_real_validator_contract(self) -> None:
        self.assertEqual(VALID_READINESS, {"ABSENT", "PARTIAL", "READY", "BROKEN"})
        for case in self.load_fixture()["cases"]:
            self.assertIn(case["expected"]["readiness"], VALID_READINESS)

    def test_audit_case_locks_all_mutations(self) -> None:
        expected = self.cases_by_coverage()["audit"]["expected"]
        self.assertEqual(expected["mode"], "audit")
        self.assertEqual(expected["phase"], "read_only")
        self.assertFalse(expected["write_allowed"])
        self.assertEqual(expected["question_budget"], 0)
        self.assertTrue(
            {"file_write", "scaffold", "task_create", "runtime_mutation"}.issubset(
                expected["forbidden_actions"]
            )
        )
        for name, text in POLICY_ASSETS.items():
            with self.subTest(asset=name):
                audit_row = extract_mode_row(text, "audit").lower()
                self.assertTrue("read-only" in audit_row or "只读" in audit_row)
                for term in ("scaffold", "trellis task"):
                    self.assertIn(term, audit_row)

    def test_init_case_is_bounded_and_local_evidence_first(self) -> None:
        expected = self.cases_by_coverage()["init"]["expected"]
        self.assertEqual(expected["mode"], "init")
        self.assertEqual(expected["readiness"], dxm_contract.ABSENT)
        self.assertEqual(expected["phase"], "clarification")
        self.assertTrue(expected["write_allowed"])
        self.assertLessEqual(expected["question_budget"], 3)
        self.assertGreater(expected["question_budget"], 0)
        self.assertTrue(expected["local_evidence_first"])
        self.assertIn("scaffold_before_blocking_clarification_resolved", expected["forbidden_actions"])

    def test_windows_and_unc_root_mismatches_use_path_semantics(self) -> None:
        cases = self.cases_by_coverage()
        for coverage, flavor in (
            ("root_mismatch_windows", "windows"),
            ("root_mismatch_unc", "unc"),
        ):
            case = cases[coverage]
            case_input = case["input"]
            self.assertEqual(case_input["root_flavor"], flavor)
            canonical = normalize_root(case_input["canonical_root"], flavor)
            observed = normalize_root(case_input["observed_root"], flavor)
            self.assertNotEqual(canonical, observed)
            self.assertEqual(ntpath.commonpath([canonical, observed]), canonical)
            self.assertEqual(case["expected"]["mode"], "audit")
            self.assertEqual(case["expected"]["readiness"], dxm_contract.BROKEN)
            self.assertEqual(case["expected"]["phase"], "root_lock_failed")
            self.assertFalse(case["expected"]["write_allowed"])
            self.assertIn("canonical_root_check", case["expected"]["evidence_gate"]["required"])
        self.assertTrue(PureWindowsPath(cases["root_mismatch_unc"]["input"]["canonical_root"]).is_absolute())
        self.assertRegex(
            POLICY_ASSETS["skill"],
            r"(?is)(?:disagrees|mismatch).{0,160}stop writes",
        )
        for name in ("agents_template", "development_template"):
            self.assertRegex(POLICY_ASSETS[name], r"不一致时.{0,40}停止写入")

    def test_review_scope_stays_locked(self) -> None:
        expected = self.cases_by_coverage()["review_scope"]["expected"]
        self.assertEqual(expected["mode"], "audit")
        self.assertEqual(expected["phase"], "scope_locked")
        self.assertEqual(expected["scope"], ["skills/dxm"])
        self.assertTrue(
            {"scan_unrelated_skills", "scan_unrelated_chat_history", "expand_scope_without_approval"}.issubset(
                expected["forbidden_actions"]
            )
        )
        for text in POLICY_ASSETS.values():
            self.assertIn("root/mode/scope lock", text)

    def test_live_service_gate_matches_real_evidence_matrix(self) -> None:
        expected = self.cases_by_coverage()["live_service_gate"]["expected"]
        self.assertEqual(expected["mode"], "task")
        self.assertEqual(expected["phase"], "evidence_required")
        required = {"listener", "health", "original_symptom_e2e"}
        self.assertTrue(required.issubset(expected["evidence_gate"]["required"]))
        self.assertTrue(
            {"unit_test", "config_inspection"}.issubset(
                expected["evidence_gate"]["insufficient_alone"]
            )
        )
        for evidence in required:
            term = EVIDENCE_POLICY_TERMS[evidence]
            for text in POLICY_ASSETS.values():
                self.assertIn(term, text.lower())

    def test_ui_gate_matches_real_evidence_matrix(self) -> None:
        expected = self.cases_by_coverage()["ui_gate"]["expected"]
        self.assertEqual(expected["mode"], "task")
        self.assertEqual(expected["phase"], "evidence_required")
        required = {
            "approved_reference",
            "rendered_screenshot",
            "navigation_hit_test",
            "regression_check",
        }
        self.assertTrue(required.issubset(expected["evidence_gate"]["required"]))
        self.assertTrue(
            {"source_inspection", "unit_test"}.issubset(
                expected["evidence_gate"]["insufficient_alone"]
            )
        )
        for evidence in required:
            term = EVIDENCE_POLICY_TERMS[evidence]
            for text in POLICY_ASSETS.values():
                self.assertIn(term, text.lower())


if __name__ == "__main__":
    unittest.main()

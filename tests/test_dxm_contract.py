import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "skills" / "dxm" / "scripts" / "dxm_contract.py"
CLI = REPO_ROOT / "skills" / "dxm" / "scripts" / "validate_dxm.py"
DXM_FILES = [
    "AGENTS.md",
    "项目开发规范（AI协作）.md",
    "项目完整链路说明.md",
    "项目文件结构说明.md",
    "开发者AI开发与PR提交流程.md",
]
CONTRACT_MARKER = "<!-- DXM-CONTRACT:1 -->"
RECEIPT_TASK = "07-13-dxm-workflow-state-machine"


def load_contract():
    if not CONTRACT.exists():
        raise AssertionError(f"contract module is missing: {CONTRACT}")
    spec = importlib.util.spec_from_file_location("dxm_contract", CONTRACT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load contract module: {CONTRACT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def create_directory_link_or_skip(target: Path, link: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
        return
    except OSError as symlink_error:
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                return
        raise unittest.SkipTest(f"directory links unavailable: {symlink_error}") from symlink_error


def remove_directory_link(link: Path) -> None:
    if link.is_symlink():
        link.unlink()
    elif link.exists():
        os.rmdir(link)


def valid_baseline(root: Path) -> dict:
    return {
        "schema_version": 1,
        "project_root": str(root.resolve()),
        "goal": "Ship a deterministic DXM validator.",
        "primary_users": ["maintainers", "project agents"],
        "deliverables": ["read-only audit", "completion receipt validator"],
        "non_goals": ["automatic Git operations"],
        "runtime": {
            "entry_points": ["python skills/dxm/scripts/validate_dxm.py"],
            "facts": ["Python 3.10 standard library only"],
        },
        "acceptance_criteria": [
            {
                "id": "AC-01",
                "description": "A complete project reports READY.",
                "evidence_kinds": ["unit-test", "cli"],
            },
            {
                "id": "AC-02",
                "description": "Broken markers report BROKEN.",
                "evidence_kinds": ["unit-test"],
            },
        ],
        "validation_commands": ["python -m unittest tests.test_dxm_contract -v"],
        "assumptions": ["The canonical root remains stable during validation."],
    }


def valid_receipt(root: Path) -> dict:
    return {
        "schema_version": 1,
        "workflow_mode": "task",
        "project_root": str(root.resolve()),
        "requirements": [
            {
                "id": "AC-01",
                "status": "passed",
                "evidence_kinds": ["unit-test", "cli"],
            },
            {
                "id": "AC-02",
                "status": "passed",
                "evidence_kinds": ["unit-test"],
            },
        ],
        "evidence": {
            "AC-01": {
                "unit-test": ["tests.test_dxm_contract: pass"],
                "cli": ["validate_dxm.py audit: exit 0"],
            },
            "AC-02": {"unit-test": ["orphan marker regression: pass"]},
        },
        "adversarial_check": {"passed": True, "summary": "No blocking gaps."},
        "quality_checks": {
            "docs": True,
            "encoding": True,
            "secrets": True,
            "rollback": True,
        },
        "trellis": {
            "required": True,
            "task": RECEIPT_TASK,
            "check_passed": True,
            "finished": True,
        },
        "git": {
            "commit_performed": False,
            "commit": None,
            "push_performed": False,
            "branch": None,
        },
    }


def write_receipt_project(root: Path, contract) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name in DXM_FILES:
        if name == "AGENTS.md":
            content = (
                "# Rules\n\n<!-- DXM-RULES:START -->\n"
                f"{CONTRACT_MARKER}\nmanaged\n<!-- DXM-RULES:END -->\n"
            )
        else:
            content = (
                "# Doc\n\n<!-- DXM-DOC-RULES:START -->\n"
                f"{CONTRACT_MARKER}\nmanaged\n<!-- DXM-DOC-RULES:END -->\n"
            )
        (root / name).write_text(content, encoding="utf-8", newline="\n")
    baseline = valid_baseline(root)
    baseline_path = root / ".dxm" / "project.json"
    baseline_path.parent.mkdir()
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False), encoding="utf-8", newline="\n")
    chain = root / "项目完整链路说明.md"
    chain.write_text(
        chain.read_text(encoding="utf-8") + "\n" + contract.baseline_markdown(baseline),
        encoding="utf-8",
        newline="\n",
    )
    trellis_block = "\n<!-- DXM-TRELLIS:START -->\ntrellis\n<!-- DXM-TRELLIS:END -->\n"
    for name in ("AGENTS.md", "项目开发规范（AI协作）.md", "项目完整链路说明.md", "项目文件结构说明.md"):
        path = root / name
        path.write_text(path.read_text(encoding="utf-8") + trellis_block, encoding="utf-8", newline="\n")
    config = root / ".trellis" / "config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("session_auto_commit: false\n", encoding="utf-8", newline="\n")
    workflow = root / ".trellis" / "workflow.md"
    workflow.write_text(
        "<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:START -->\nmanaged\n"
        "<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:END -->\n",
        encoding="utf-8",
        newline="\n",
    )
    start_skill = root / ".agents" / "skills" / "trellis-start" / "SKILL.md"
    start_skill.parent.mkdir(parents=True)
    start_skill.write_text(
        "<!-- DXM-TRELLIS-START-STEP0:START -->\nmanaged\n"
        "<!-- DXM-TRELLIS-START-STEP0:END -->\n",
        encoding="utf-8",
        newline="\n",
    )
    task_dir = root / ".trellis" / "tasks" / "archive" / "2026-07" / RECEIPT_TASK
    task_dir.mkdir(parents=True)
    (task_dir / "task.json").write_text(
        json.dumps({"id": "dxm-workflow-state-machine", "status": "completed"}),
        encoding="utf-8",
        newline="\n",
    )
    (task_dir / "check.md").write_text(
        "<!-- DXM-CHECK:PASS -->\n\n# Check\n\nNo blocking findings.\n",
        encoding="utf-8",
        newline="\n",
    )


class BaselineContractTests(unittest.TestCase):
    def test_load_baseline_accepts_complete_schema_and_expected_root(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            path = root / "baseline.json"
            data = valid_baseline(root)
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

            loaded = contract.load_baseline(path, expected_root=root)

            self.assertEqual(loaded, data)

    def test_load_baseline_rejects_missing_fields_and_duplicate_acceptance_ids(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "baseline.json"
            data = valid_baseline(root)
            del data["goal"]
            data["acceptance_criteria"].append(dict(data["acceptance_criteria"][0]))
            path.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaises(contract.ContractError) as raised:
                contract.load_baseline(path)

            message = str(raised.exception)
            self.assertIn("goal", message)
            self.assertIn("duplicate acceptance id", message)

    def test_validation_errors_do_not_echo_untrusted_schema_values(self) -> None:
        contract = load_contract()
        secret = "credential-value-that-must-not-leak"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_path = root / "baseline.json"
            baseline = valid_baseline(root)
            baseline["acceptance_criteria"][0]["id"] = secret
            baseline["acceptance_criteria"][1]["id"] = secret
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")

            with self.assertRaises(contract.ContractError) as raised:
                contract.load_baseline(baseline_path)

            receipt = valid_receipt(root)
            receipt["requirements"][0]["id"] = secret
            receipt["requirements"][0]["status"] = "failed"
            receipt["requirements"][0]["evidence_kinds"] = [secret]
            receipt_errors = contract.validate_receipt(receipt, expected_root=root)
            marker_errors = contract.validate_marker_layout(
                f"<!-- DXM-TEST {secret} -->",
                "<!-- DXM-TEST:START -->",
                "<!-- DXM-TEST:END -->",
            )

            self.assertNotIn(secret, str(raised.exception))
            self.assertNotIn(secret, " ".join(receipt_errors))
            self.assertNotIn(secret, " ".join(marker_errors))

    def test_baseline_rejects_high_confidence_credentials_without_echoing_values(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = valid_baseline(root)
            data["goal"] = "Bearer abcdefghijklmnopqrstuvwxyz123456"
            data["runtime"]["facts"] = [
                "api_key=abcdefghijklmnopqrstuvwxyz123456",
                "OPENAI_API_KEY=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
                "GITHUB_TOKEN=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
                "DATABASE_PASSWORD=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
                "JWT_SECRET=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
                "openaiApiKey=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
                "githubAccessToken=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
            ]

            errors = contract.validate_baseline(data, expected_root=root)

            combined = " ".join(errors)
            self.assertIn("baseline.goal", combined)
            for index in range(len(data["runtime"]["facts"])):
                self.assertIn(f"baseline.runtime.facts[{index}]", combined)
            self.assertNotIn("abcdefghijklmnopqrstuvwxyz", combined)

    def test_baseline_rejects_high_confidence_credentials_hidden_in_keys(self) -> None:
        contract = load_contract()
        secret_keys = (
            "api_key=abcdefghijklmnopqrstuvwxyz123456",
            "api_key_abcdefghijklmnopqrstuvwxyz123456",
            "password correct horse battery staple",
            "token-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
            "api_key：abcdefghijklmnopqrstuvwxyz123456",
            "password＝correct horse battery staple",
            "prodApiKey=abcdefghijklmnopqrstuvwxyz123456",
            "prod：api_key：abcdefghijklmnopqrstuvwxyz123456",
            "prefix\\password=abcdefghijklmnopqrstuvwxyz123456",
            "openaiApiKey=abcdefghijklmnopqrstuvwxyz123456",
            "githubAccessToken=abcdefghijklmnopqrstuvwxyz123456",
            "databasePassword=abcdefghijklmnopqrstuvwxyz123456",
            "jwtSecret=abcdefghijklmnopqrstuvwxyz123456",
            "myToken=abcdefghijklmnopqrstuvwxyz123456",
            "api_keys=abcdefghijklmnopqrstuvwxyz123456",
            "access_tokens=abcdefghijklmnopqrstuvwxyz123456",
            "private_keys=abcdefghijklmnopqrstuvwxyz123456",
        )
        for secret_key in secret_keys:
            with self.subTest(secret_key=secret_key[:8]), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                data = valid_baseline(root)
                data[secret_key] = "ignored"

                errors = contract.validate_baseline(data, expected_root=root)

                combined = " ".join(errors)
                self.assertIn("key contains a high-confidence credential", combined)
                self.assertNotIn(secret_key, combined)

    def test_baseline_rejects_credential_key_value_pairs_and_nested_values(self) -> None:
        contract = load_contract()
        cases = {
            "direct_and_nested": {
                "api_key": "abcdefghijklmnopqrstuvwxyz123456",
                "nested": {"password": ["correct horse battery staple"]},
            },
            "uppercase_literal": {"api_key": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "symbol_literal": {"password": "P@ssw0rd!P@ssw0rd!"},
            "angle_literal": {"api_key": "<ABCDEFGHIJKLMNOPQRSTUVWXYZ123456>"},
            "spaced_key": {"api key": "abcdefghijklmnopqrstuvwxyz123456"},
            "dotted_key": {"api.key": "abcdefghijklmnopqrstuvwxyz123456"},
            "camel_key": {"secretKey": "abcdefghijklmnopqrstuvwxyz123456"},
            "authorization_key": {"authorization": "abcdefghijklmnopqrstuvwxyz123456"},
            "value_suffix_alias": {"apiKeyValue": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "header_suffix_alias": {"authorizationHeader": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "client_secret_value": {"clientSecretValue": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "data_suffix_alias": {"apiKeyData": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "map_suffix_alias": {"authorizationMap": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "ref_suffix_alias": {"clientSecretRef": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "numbered_wrapper_alias": {"api_key_value_1": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "private_key_alias": {"sshPrivateKey": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "passphrase_alias": {"passphrase": "correct horse battery staple"},
            "credential_container": {"credentials": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "auth_container": {"auth": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "wrapped_container": {"credentialsData": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "secret_map_container": {"secretsMap": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "auth_config_container": {"authConfig": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "option_container": {"apiKeyOption": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "metadata_container": {"credentialMetadata": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "payload_container": {"credentialsPayload": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "settings_container": {"apiKeySettings": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "material_container": {"privateKeyMaterial": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "plural_api_keys": {"apiKeys": ["abcdefghijklmnopqrstuvwxyz123456"]},
            "plural_access_tokens": {"accessTokens": ["abcdefghijklmnopqrstuvwxyz123456"]},
            "plural_passwords": {"passwords": ["correct horse battery staple"]},
            "env_reference_key_context": {
                "api_key=${DXM_API_KEY}": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
            },
            "secret_in_context_key": {"credentials": {"ABCDEFGHIJKLMNOPQRSTUVWXYZ123456": "<redacted>"}},
            "numeric_scalar": {"api_key": 12345678901234567890},
        }
        for label, deployment in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                data = valid_baseline(root)
                data["deployment"] = deployment

                errors = contract.validate_baseline(data, expected_root=root)

                combined = " ".join(errors)
                self.assertIn("high-confidence credential", combined)
                for secret in ("abcdefghijklmnopqrstuvwxyz123456", "correct horse battery staple", "P@ssw0rd"):
                    self.assertNotIn(secret, combined)

    def test_baseline_allows_redacted_or_environment_credential_examples(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = valid_baseline(root)
            data["goal"] = "Document Authorization: Bearer <token>."
            data["runtime"]["facts"] = ["Read api_key=${DXM_API_KEY}; never persist it."]
            data["validation_commands"] = ["echo sk-example-placeholder"]
            data["deployment"] = {
                "api_key": "${DXM_API_KEY}",
                "access_token": "env:DXM_ACCESS_TOKEN",
                "password": "<redacted>",
                "client_secret": "<env:DXM_CLIENT_SECRET>",
                "api_key=env:DXM_SECONDARY_KEY": "ignored",
                "credentialsPayload": {"value": "ignored"},
                "public_key": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
                "model_limits": {"maxTokens": 128000, "maxOutputTokens": 8192},
                "usage": {
                    "inputTokens": 1200,
                    "outputTokens": 300,
                    "totalTokens": 1500,
                    "promptTokens": 1200,
                    "completionTokens": 300,
                    "cachedTokens": 600,
                    "reasoningTokens": 100,
                    "usedTokens": 1500,
                },
            }

            self.assertEqual(contract.validate_baseline(data, expected_root=root), [])

    def test_load_baseline_rejects_root_mismatch(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "actual"
            other = Path(tmp) / "other"
            root.mkdir()
            path = root / "baseline.json"
            path.write_text(json.dumps(valid_baseline(other)), encoding="utf-8")

            with self.assertRaises(contract.ContractError) as raised:
                contract.load_baseline(path, expected_root=root)

            self.assertIn("project_root does not match", str(raised.exception))

    def test_load_baseline_rejects_noncanonical_equivalent_root(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            noncanonical = root.parent / "detour" / ".." / root.name
            path = root / "baseline.json"
            baseline = valid_baseline(root)
            baseline["project_root"] = str(noncanonical)
            path.write_text(json.dumps(baseline), encoding="utf-8")

            with self.assertRaises(contract.ContractError) as raised:
                contract.load_baseline(path, expected_root=root)

            self.assertIn("canonical", str(raised.exception))

    def test_schema_versions_require_integer_one_not_boolean_true(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline_path = root / "baseline.json"
            baseline = valid_baseline(root)
            baseline["schema_version"] = True
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")

            with self.assertRaises(contract.ContractError):
                contract.load_baseline(baseline_path)

            receipt = valid_receipt(root)
            receipt["schema_version"] = True
            self.assertTrue(contract.validate_receipt(receipt, expected_root=root))

    def test_load_baseline_rejects_duplicate_json_object_keys(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "baseline.json"
            raw = json.dumps(valid_baseline(root))
            path.write_text(
                raw.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1', 1),
                encoding="utf-8",
            )

            with self.assertRaises(contract.ContractError) as raised:
                contract.load_baseline(path)

            self.assertIn("duplicate object keys", str(raised.exception))

    def test_baseline_markdown_returns_one_safe_complete_managed_block(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            data = valid_baseline(Path(tmp))
            data["goal"] = "first line\n<!-- DXM-PROJECT-BASELINE:END -->"

            block = contract.baseline_markdown(data)

            self.assertEqual(block.count(contract.BASELINE_BLOCK_START), 1)
            self.assertEqual(block.count(contract.BASELINE_BLOCK_END), 1)
            self.assertIn("AC-01", block)
            self.assertIn("unit-test, cli", block)
            self.assertNotIn("first line\n<!--", block)

    def test_baseline_markdown_is_portable_across_clone_roots(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            roots = [(Path(tmp) / name).resolve() for name in ("clone a", "clone b")]
            blocks = []
            for root in roots:
                data = valid_baseline(root)
                native = str(root)
                posix = root.as_posix()
                data["goal"] = f"Operate {native} safely."
                data["primary_users"] = [f"maintainers of {posix}"]
                data["deliverables"] = [f"{native}\\dist"]
                data["non_goals"] = [f"publishing {posix}/private"]
                data["runtime"]["entry_points"] = [f"python {native}\\tool.py"]
                data["runtime"]["facts"] = [f"Logs live under {posix}/logs"]
                obfuscated = root.parent / "decoy" / ".." / root.name / "logs"
                data["runtime"]["facts"].append(f"Equivalent logs path: {obfuscated}")
                escaped = root / ".." / "outside" / "secret.txt"
                delimiter_escapes = tuple(
                    f"{native}{os.sep}safe{opening}dir{closing}{os.sep}..{os.sep}..{os.sep}outside{os.sep}secret.txt"
                    for opening, closing in (("[", "]"), ("{", "}"), ("`", "`"))
                )
                prefix_collision = f"{root}-sibling{os.sep}secret.txt"
                file_uri = f"file:///{root.parent.as_posix().lstrip('/')}\u002fdecoy/../{root.name}/logs"
                short_file_uri = f"file:/{root.parent.as_posix().lstrip('/')}\u002foutside/secret.txt"
                forward_unc = f"//private-host/share/{root.name}/logs"
                data["runtime"]["facts"].extend(
                    (
                        f"Escaped path: {escaped}",
                        *(f"Delimiter escape: {path}" for path in delimiter_escapes),
                        f"Prefix collision: {prefix_collision}",
                        f"File URI: {file_uri}",
                        f"Short file URI: {short_file_uri}",
                        f"Forward UNC: {forward_unc}",
                        "Health URL: http://127.0.0.1:17777/healthz",
                        "API URL: https://example.invalid/api/v1",
                        "Socket URL: wss://example.invalid/events",
                        "Output file: README.md",
                        "URN: urn:/example/resource",
                    )
                )
                data["acceptance_criteria"][0]["description"] = f"Audit {native}."
                data["validation_commands"] = [f"python {posix}/tests.py"]
                data["validation_commands"].append(f"clang -I{native}{os.sep}include main.c")
                data["validation_commands"].extend(
                    ("clang -I/usr/include main.c", "clang -L/opt/lib main.c")
                )
                data["assumptions"] = [f"{native.upper()} remains available"]
                blocks.append(contract.baseline_markdown(data))

            self.assertEqual(blocks[0], blocks[1])
            for root, block in zip(roots, blocks):
                self.assertNotIn(str(root).lower(), block.lower())
                self.assertNotIn(root.as_posix().lower(), block.lower())
                self.assertNotIn("decoy", block.lower())
                self.assertNotIn("..", block)
                self.assertNotIn("outside", block.lower())
                self.assertNotIn("sibling", block.lower())
                self.assertNotIn("private-host", block.lower())
                self.assertNotIn("file://", block.lower())
                self.assertIn("$PROJECT_ROOT", block)
                self.assertIn("$ABSOLUTE_PATH", block)
                self.assertIn("http://127.0.0.1:17777/healthz", block)
                self.assertIn("https://example.invalid/api/v1", block)
                self.assertIn("wss://example.invalid/events", block)
                self.assertIn("Output file: README.md", block)
                self.assertIn("urn:/example/resource", block)
                self.assertIn(".dxm/project.json", block)
            if os.name != "nt":
                self.assertEqual(
                    contract._portable_baseline_text("/tmp/clone/logs", "/tmp/Clone"),
                    "$ABSOLUTE_PATH",
                )
                self.assertEqual(
                    contract._portable_baseline_text("/tmp/Clone/logs", "/tmp/Clone"),
                    "$PROJECT_ROOT/logs",
                )


class MarkerContractTests(unittest.TestCase):
    def test_marker_layout_accepts_absent_or_one_ordered_pair(self) -> None:
        contract = load_contract()
        start = "<!-- DXM-TEST:START -->"
        end = "<!-- DXM-TEST:END -->"

        self.assertEqual(contract.validate_marker_layout("manual\n", start, end), [])
        self.assertEqual(contract.validate_marker_layout(f"before\n{start}\nbody\n{end}\nafter\n", start, end), [])
        self.assertEqual(contract.validate_marker_layout(f"x```{start}```\n", start, end), [])
        self.assertEqual(
            contract.validate_marker_layout(
                "<!-- DXM-TEST-EXTRA:START -->\nbody\n<!-- DXM-TEST-EXTRA:END -->\n",
                start,
                end,
            ),
            [],
        )

    def test_marker_layout_rejects_orphans_duplicates_and_out_of_order_pairs(self) -> None:
        contract = load_contract()
        start = "<!-- DXM-TEST:START -->"
        end = "<!-- DXM-TEST:END -->"
        cases = {
            "orphan start": start,
            "orphan end": end,
            "duplicate start": f"{start}\n{start}\n{end}",
            "duplicate end": f"{start}\n{end}\n{end}",
            "out of order": f"{end}\n{start}",
        }

        for label, content in cases.items():
            with self.subTest(label=label):
                errors = contract.validate_marker_layout(content, start, end)
                self.assertTrue(errors, label)
                self.assertIn(label, " ".join(errors).lower())

        tab_fence_errors = contract.validate_marker_layout(
            "\t```md\n<!-- DXM-TEST:START -->\n\t```\n",
            start,
            end,
        )
        self.assertIn("orphan start", " ".join(tab_fence_errors).lower())
        mismatched_inline_runs = (
            f"x```{start}``\n",
            f"x``{start}```\n",
            f"x````{start}```\n",
        )
        for content in mismatched_inline_runs:
            with self.subTest(content=content[:5]):
                errors = contract.validate_marker_layout(content, start, end)
                self.assertIn("orphan start", " ".join(errors).lower())

    def test_marker_layout_rejects_marker_like_malformed_syntax(self) -> None:
        contract = load_contract()
        start = "<!-- DXM-TEST:START -->"
        end = "<!-- DXM-TEST:END -->"
        cases = (
            "<!-- DXM-TEST START -->\n",
            "<!-- DXM-TEST:START\nmanual\n",
            "<!-- dxm-test:start\nmanual\n",
            "<!-- DXM-TEST:END\nmanual\n",
            "x```<!-- dxm-test:start -->``\n",
        )
        for content in cases:
            with self.subTest(content=content.splitlines()[0]):
                errors = contract.validate_marker_layout(content, start, end)
                self.assertIn("malformed", " ".join(errors).lower())

    def test_managed_marker_stack_rejects_nesting_and_cross_closed_blocks(self) -> None:
        contract = load_contract()
        sequential = (
            "<!-- DXM-A:START -->\na\n<!-- DXM-A:END -->\n"
            "<!-- DXM-B:START -->\nb\n<!-- DXM-B:END -->\n"
        )
        crossed = (
            "<!-- DXM-A:START -->\n"
            "<!-- DXM-B:START -->\n"
            "<!-- DXM-A:END -->\n"
            "<!-- DXM-B:END -->\n"
        )

        self.assertEqual(contract.validate_managed_markers(sequential), [])
        errors = contract.validate_managed_markers(crossed)
        combined = " ".join(errors).lower()
        self.assertIn("nested", combined)
        self.assertIn("out of order", combined)

    def test_managed_marker_validation_rejects_lowercase_and_underscore_marker_like_comments(self) -> None:
        contract = load_contract()
        malformed = (
            "<!-- dxm-rules:start -->\n<!-- dxm-rules:end -->\n"
            "<!-- DXM_RULES:START -->\n<!-- DXM_RULES:END -->\n"
            "<!-- DXM-RULES:START\nmanual\n"
        )

        errors = contract.validate_managed_markers(malformed)

        self.assertIn("malformed", " ".join(errors).lower())


class AuditContractTests(unittest.TestCase):
    def write_docs(self, root: Path, contract, *, include_baseline: bool = True) -> None:
        root.mkdir(parents=True, exist_ok=True)
        for name in DXM_FILES:
            if name == "AGENTS.md":
                content = (
                    "# Rules\n\n<!-- DXM-RULES:START -->\n"
                    f"{CONTRACT_MARKER}\nmanaged\n<!-- DXM-RULES:END -->\n"
                )
            else:
                content = (
                    "# Doc\n\n<!-- DXM-DOC-RULES:START -->\n"
                    f"{CONTRACT_MARKER}\nmanaged\n<!-- DXM-DOC-RULES:END -->\n"
                )
            (root / name).write_text(content, encoding="utf-8", newline="\n")
        if include_baseline:
            data = valid_baseline(root)
            baseline_path = root / ".dxm" / "project.json"
            baseline_path.parent.mkdir()
            baseline_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8", newline="\n")
            chain = root / "项目完整链路说明.md"
            chain.write_text(chain.read_text(encoding="utf-8") + "\n" + contract.baseline_markdown(data), encoding="utf-8", newline="\n")

    def write_trellis_integration(self, root: Path, contract, config: str = "session_auto_commit: false\n") -> None:
        trellis_block = "\n<!-- DXM-TRELLIS:START -->\ntrellis\n<!-- DXM-TRELLIS:END -->\n"
        for name in ("AGENTS.md", "项目开发规范（AI协作）.md", "项目完整链路说明.md", "项目文件结构说明.md"):
            path = root / name
            path.write_text(path.read_text(encoding="utf-8") + trellis_block, encoding="utf-8")
        config_path = root / ".trellis" / "config.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(config, encoding="utf-8")
        workflow = root / ".trellis" / "workflow.md"
        workflow.write_text(
            "<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:START -->\nmanaged\n"
            "<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:END -->\n",
            encoding="utf-8",
        )
        start_skill = root / ".agents" / "skills" / "trellis-start" / "SKILL.md"
        start_skill.parent.mkdir(parents=True)
        start_skill.write_text(
            "<!-- DXM-TRELLIS-START-STEP0:START -->\nmanaged\n"
            "<!-- DXM-TRELLIS-START-STEP0:END -->\n",
            encoding="utf-8",
        )

    def test_audit_reports_absent_without_creating_root(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "missing"

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.ABSENT)
            self.assertEqual(result.exit_code, contract.EXIT_ABSENT)
            self.assertFalse(root.exists())

    def test_audit_treats_non_directory_root_and_dxm_ancestor_as_broken(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root_file = base / "root-file"
            root_file.write_text("not a project directory", encoding="utf-8")
            invalid_dxm = base / "invalid-dxm"
            invalid_dxm.mkdir()
            (invalid_dxm / ".dxm").write_text("not a directory", encoding="utf-8")

            for root in (root_file, invalid_dxm):
                with self.subTest(root=root.name):
                    result = contract.audit_project(root)

                    self.assertEqual(result.state, contract.BROKEN, result.issues)
                    self.assertIn("directory", " ".join(result.issues).lower())

    def test_audit_reports_partial_when_docs_exist_without_baseline(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "legacy"
            self.write_docs(root, contract, include_baseline=False)

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.PARTIAL)
            self.assertIn(".dxm/project.json", " ".join(result.issues))

    def test_audit_reports_ready_for_complete_valid_project(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ready"
            self.write_docs(root, contract)

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.READY, result.issues)
            self.assertEqual(result.exit_code, contract.EXIT_OK)
            self.assertEqual(result.to_dict()["state"], contract.READY)

    def test_contract_marker_matches_exported_contract_version(self) -> None:
        contract = load_contract()

        self.assertEqual(contract.CONTRACT_MARKER, CONTRACT_MARKER)

    def test_audit_reports_partial_when_current_contract_marker_is_missing(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "legacy"
            self.write_docs(root, contract)
            doc = root / "项目文件结构说明.md"
            doc.write_text(
                doc.read_text(encoding="utf-8").replace(f"{CONTRACT_MARKER}\n", ""),
                encoding="utf-8",
            )

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.PARTIAL, result.issues)
            self.assertIn("contract marker", " ".join(result.issues).lower())

    def test_audit_reports_broken_for_duplicate_contract_marker(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "duplicate-contract-marker"
            self.write_docs(root, contract)
            agents = root / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8").replace(
                    f"{CONTRACT_MARKER}\nmanaged",
                    f"{CONTRACT_MARKER}\n{CONTRACT_MARKER}\nmanaged",
                ),
                encoding="utf-8",
            )

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.BROKEN, result.issues)
            self.assertIn("duplicate", " ".join(result.issues).lower())

    def test_audit_reports_broken_when_json_and_managed_baseline_block_drift(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "drifted-baseline"
            self.write_docs(root, contract)
            baseline_path = root / ".dxm" / "project.json"
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
            baseline["goal"] = "Changed without hydrating the managed block."
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.BROKEN, result.issues)
            self.assertIn("does not match", " ".join(result.issues).lower())

    def test_audit_rejects_baseline_directory_link_that_escapes_project(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            self.write_docs(root, contract)
            baseline_link = root / ".dxm"
            external_baseline = base / "external-baseline"
            shutil.move(str(baseline_link), str(external_baseline))
            create_directory_link_or_skip(external_baseline, baseline_link)
            try:
                result = contract.audit_project(root)
            finally:
                remove_directory_link(baseline_link)

            self.assertEqual(result.state, contract.BROKEN, result.issues)
            combined = " ".join(result.issues).lower()
            self.assertIn("baseline", combined)
            self.assertTrue("trusted project" in combined or "reparse" in combined, combined)

    def test_audit_rejects_hardlinked_baseline_artifact(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            self.write_docs(root, contract)
            baseline = root / ".dxm" / "project.json"
            external_baseline = base / "external-project.json"
            baseline.replace(external_baseline)
            os.link(external_baseline, baseline)

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.BROKEN, result.issues)
            self.assertIn("hardlink", " ".join(result.issues).lower())

    def test_audit_treats_existing_non_file_artifacts_as_broken(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for artifact in ("required-doc", "baseline"):
                with self.subTest(artifact=artifact):
                    root = base / artifact
                    self.write_docs(root, contract)
                    if artifact == "required-doc":
                        path = root / "项目文件结构说明.md"
                    else:
                        path = root / ".dxm" / "project.json"
                    path.unlink()
                    path.mkdir()

                    result = contract.audit_project(root)

                    self.assertEqual(result.state, contract.BROKEN, result.issues)
                    self.assertIn("regular file", " ".join(result.issues).lower())

    def test_audit_never_reads_unsafe_linked_trellis_skill_after_rejecting_it(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            write_receipt_project(root, contract)
            agents_link = root / ".agents"
            external_agents = base / "external-agents"
            shutil.move(str(agents_link), str(external_agents))
            create_directory_link_or_skip(external_agents, agents_link)
            unsafe_skill = agents_link / "skills" / "trellis-start" / "SKILL.md"
            unsafe_reads: list[Path] = []
            original_read = contract._read_audit_text

            def record_read(path: Path):
                if path == unsafe_skill:
                    unsafe_reads.append(path)
                return original_read(path)

            contract._read_audit_text = record_read
            try:
                result = contract.audit_project(root, require_trellis=True)
            finally:
                contract._read_audit_text = original_read
                remove_directory_link(agents_link)

            self.assertEqual(result.state, contract.BROKEN, result.issues)
            self.assertEqual(unsafe_reads, [])

    def test_audit_reports_broken_for_invalid_json_root_mismatch_or_bad_markers(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roots = [base / "json", base / "mismatch", base / "markers"]
            for root in roots:
                self.write_docs(root, contract)

            (roots[0] / ".dxm" / "project.json").write_text("{bad json", encoding="utf-8")
            mismatch = valid_baseline(base / "somewhere-else")
            (roots[1] / ".dxm" / "project.json").write_text(json.dumps(mismatch), encoding="utf-8")
            agents = roots[2] / "AGENTS.md"
            agents.write_text(agents.read_text(encoding="utf-8") + "<!-- DXM-RULES:END -->\n", encoding="utf-8")

            for root in roots:
                with self.subTest(root=root.name):
                    result = contract.audit_project(root)
                    self.assertEqual(result.state, contract.BROKEN, result.issues)
                    self.assertEqual(result.exit_code, contract.EXIT_INVALID)

    def test_audit_reports_broken_for_malformed_required_marker(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "malformed-marker"
            self.write_docs(root, contract)
            agents = root / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8").replace(
                    "<!-- DXM-RULES:START -->",
                    "<!-- DXM-RULES START -->",
                ),
                encoding="utf-8",
            )

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.BROKEN, result.issues)
            self.assertIn("malformed", " ".join(result.issues).lower())

    def test_audit_reports_broken_for_lowercase_marker_like_comments(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "lowercase-marker"
            self.write_docs(root, contract)
            agents = root / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8")
                .replace("<!-- DXM-RULES:START -->", "<!-- dxm-rules:start -->")
                .replace("<!-- DXM-RULES:END -->", "<!-- dxm-rules:end -->"),
                encoding="utf-8",
            )

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.BROKEN, result.issues)
            self.assertIn("malformed", " ".join(result.issues).lower())

    def test_audit_reports_broken_for_cross_closed_managed_blocks(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "cross-closed"
            self.write_docs(root, contract)
            chain = root / "项目完整链路说明.md"
            chain.write_text(
                "<!-- DXM-DOC-RULES:START -->\n"
                "<!-- DXM-TRELLIS:START -->\n"
                "<!-- DXM-DOC-RULES:END -->\n"
                "<!-- DXM-TRELLIS:END -->\n"
                + contract.baseline_markdown(valid_baseline(root)),
                encoding="utf-8",
            )

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.BROKEN, result.issues)
            self.assertIn("out of order", " ".join(result.issues).lower())

    def test_audit_reports_broken_for_malformed_baseline_marker_even_without_baseline_file(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "malformed-baseline-marker"
            self.write_docs(root, contract, include_baseline=False)
            chain = root / "项目完整链路说明.md"
            chain.write_text(
                chain.read_text(encoding="utf-8") + "\n<!-- DXM-PROJECT-BASELINE START -->\n",
                encoding="utf-8",
            )

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.BROKEN, result.issues)
            self.assertIn("malformed", " ".join(result.issues).lower())

    def test_audit_reports_partial_for_placeholder_or_missing_requested_trellis(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "partial"
            self.write_docs(root, contract)
            doc = root / "项目文件结构说明.md"
            doc.write_text(doc.read_text(encoding="utf-8") + "{{unresolved}}\n", encoding="utf-8")

            placeholder = contract.audit_project(root)
            trellis = contract.audit_project(root, require_trellis=True)

            self.assertEqual(placeholder.state, contract.PARTIAL)
            self.assertIn("placeholder", " ".join(placeholder.issues).lower())
            self.assertEqual(trellis.state, contract.PARTIAL)
            self.assertIn(".trellis", " ".join(trellis.issues))

    def test_audit_rejects_duplicate_active_session_auto_commit_keys(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "duplicate-trellis-config"
            self.write_docs(root, contract)
            self.write_trellis_integration(
                root,
                contract,
                config="session_auto_commit: false\nsession_auto_commit: true\n",
            )

            result = contract.audit_project(root, require_trellis=True)

            self.assertEqual(result.state, contract.BROKEN, result.issues)
            self.assertIn("exactly one", " ".join(result.issues).lower())

    def test_audit_does_not_treat_nested_session_auto_commit_as_top_level_config(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "nested-trellis-config"
            self.write_docs(root, contract)
            self.write_trellis_integration(
                root,
                contract,
                config="outer:\n  session_auto_commit: false\n",
            )

            result = contract.audit_project(root, require_trellis=True)

            self.assertEqual(result.state, contract.PARTIAL, result.issues)
            self.assertIn("session_auto_commit", " ".join(result.issues))

    def test_audit_ignores_placeholders_documented_in_inline_and_fenced_code(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "documented-placeholders"
            self.write_docs(root, contract)
            chain = root / "项目完整链路说明.md"
            chain.write_text(
                chain.read_text(encoding="utf-8")
                + "\nTemplate token: `{{file_inventory}}`.\n"
                + "\n```text\n{{project_root}}\n```\n"
                + "\n~~~markdown\n{{generated_date}}\n~~~\n",
                encoding="utf-8",
            )

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.READY, result.issues)

    def test_audit_ignores_marker_examples_in_inline_and_fenced_code(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "marker-examples"
            self.write_docs(root, contract)
            agents = root / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8")
                + "\nExample: `<!-- DXM-RULES:START -->`.\n"
                + "\n```markdown\n<!-- DXM-RULES:START -->\n"
                + f"{CONTRACT_MARKER}\n<!-- DXM-RULES:END -->\n```\n",
                encoding="utf-8",
            )

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.READY, result.issues)

    def test_audit_does_not_accept_required_markers_only_inside_code_fence(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "coded-markers-only"
            self.write_docs(root, contract)
            agents = root / "AGENTS.md"
            agents.write_text(
                "# Rules\n\n```markdown\n<!-- DXM-RULES:START -->\n"
                f"{CONTRACT_MARKER}\nmanaged\n<!-- DXM-RULES:END -->\n```\n",
                encoding="utf-8",
            )

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.PARTIAL, result.issues)
            self.assertIn("managed block", " ".join(result.issues).lower())

    def test_audit_does_not_accept_contract_marker_hidden_in_code_within_real_block(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "coded-contract-marker"
            self.write_docs(root, contract)
            agents = root / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8").replace(
                    CONTRACT_MARKER,
                    f"```markdown\n{CONTRACT_MARKER}\n```",
                    1,
                ),
                encoding="utf-8",
            )

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.PARTIAL, result.issues)
            self.assertIn("contract marker", " ".join(result.issues).lower())

    def test_audit_does_not_hide_placeholder_behind_unclosed_code_fence(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "unclosed-fence"
            self.write_docs(root, contract)
            chain = root / "项目完整链路说明.md"
            chain.write_text(
                chain.read_text(encoding="utf-8") + "\n```text\n{{unresolved_after_open_fence}}\n",
                encoding="utf-8",
            )

            result = contract.audit_project(root)

            self.assertEqual(result.state, contract.PARTIAL, result.issues)
            self.assertIn("placeholder", " ".join(result.issues).lower())


class ReceiptContractTests(unittest.TestCase):
    def test_complete_receipt_is_valid(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            self.assertEqual(contract.validate_receipt(valid_receipt(root), expected_root=root), [])

    def test_receipt_rejects_non_completion_workflow_modes(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            for mode in ("audit", "scaffold-only"):
                with self.subTest(mode=mode):
                    receipt = valid_receipt(root)
                    receipt["workflow_mode"] = mode

                    errors = contract.validate_receipt(receipt, expected_root=root)

                    combined = " ".join(errors).lower()
                    self.assertIn("workflow_mode", combined)
                    self.assertIn("init", combined)
                    self.assertIn("task", combined)

    def test_receipt_rejects_high_confidence_credentials_without_echoing_values(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            receipt = valid_receipt(root)
            receipt["evidence"]["AC-01"]["unit-test"][0] = (
                "Bearer abcdefghijklmnopqrstuvwxyz123456"
            )
            receipt["adversarial_check"]["summary"] = (
                "-----BEGIN PRIVATE KEY----- private material"
            )

            errors = contract.validate_receipt(receipt, expected_root=root)

            combined = " ".join(errors)
            self.assertIn("receipt.evidence", combined)
            self.assertIn("receipt.adversarial_check.summary", combined)
            self.assertNotIn("abcdefghijklmnopqrstuvwxyz", combined)
            self.assertNotIn("private material", combined)

    def test_receipt_rejects_high_confidence_credentials_hidden_in_keys(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            receipt = valid_receipt(root)
            secret_key = "api_key_abcdefghijklmnopqrstuvwxyz123456"
            receipt[secret_key] = "ignored"

            errors = contract.validate_receipt(receipt, expected_root=root)

            combined = " ".join(errors)
            self.assertIn("key contains a high-confidence credential", combined)
            self.assertNotIn(secret_key, combined)

    def test_receipt_rejects_credential_key_value_pairs_and_nested_values(self) -> None:
        contract = load_contract()
        cases = {
            "direct_and_nested": {
                "password": "abcdefghijklmnopqrstuvwxyz123456",
                "nested": {"api_key": ["correct horse battery staple"]},
            },
            "uppercase_literal": {"api_key": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "symbol_literal": {"password": "P@ssw0rd!P@ssw0rd!"},
            "angle_literal": {"api_key": "<correcthorsebatterystaple>"},
            "value_suffix_alias": {"apiKeyValue": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "private_key_alias": {"private_key": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
            "numeric_scalar": {"api_key": 12345678901234567890},
            "alias_container": {"credentials": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "option_container": {"apiKeyOption": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "metadata_container": {"credentialMetadata": {"value": "abcdefghijklmnopqrstuvwxyz123456"}},
            "plural_tokens": {"authTokens": ["abcdefghijklmnopqrstuvwxyz123456"]},
            "env_reference_key_context": {
                "api_key=${DXM_API_KEY}": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
            },
            "secret_in_context_key": {"credentials": {"ABCDEFGHIJKLMNOPQRSTUVWXYZ123456": "<redacted>"}},
        }
        for label, metadata in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write_receipt_project(root, contract)
                receipt = valid_receipt(root)
                receipt["metadata"] = metadata

                errors = contract.validate_receipt(receipt, expected_root=root)

                combined = " ".join(errors)
                self.assertIn("high-confidence credential", combined)
                for secret in ("abcdefghijklmnopqrstuvwxyz123456", "correct horse battery staple", "P@ssw0rd"):
                    self.assertNotIn(secret, combined)

    def test_receipt_allows_redacted_or_environment_credential_examples(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            receipt = valid_receipt(root)
            receipt["evidence"]["AC-01"]["unit-test"][0] = "Bearer <redacted>"
            receipt["adversarial_check"]["summary"] = "Checked api_key=${DXM_API_KEY}."
            receipt["metadata"] = {
                "api_key": "${DXM_API_KEY}",
                "access_token": "env:DXM_ACCESS_TOKEN",
                "password": "<redacted>",
                "client_secret": "<env:DXM_CLIENT_SECRET>",
                "api_key=<env:DXM_SECONDARY_KEY>": "ignored",
                "credentialsPayload": {"value": "ignored"},
                "public_key": "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
                "model_limits": {"maxTokens": 128000, "maxOutputTokens": 8192},
                "usage": {
                    "inputTokens": 1200,
                    "outputTokens": 300,
                    "totalTokens": 1500,
                    "promptTokens": 1200,
                    "completionTokens": 300,
                    "cachedTokens": 600,
                    "reasoningTokens": 100,
                    "usedTokens": 1500,
                },
            }

            self.assertEqual(contract.validate_receipt(receipt, expected_root=root), [])

    def test_receipt_rejects_failed_requirement_and_missing_evidence_kind(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            receipt = valid_receipt(root)
            receipt["requirements"][0]["status"] = "failed"
            del receipt["evidence"]["AC-01"]["cli"]

            errors = contract.validate_receipt(receipt, expected_root=root)

            combined = " ".join(errors)
            self.assertIn("status", combined)
            self.assertIn("evidence", combined)

    def test_receipt_rejects_failed_checks_and_false_trellis_completion(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            receipt = valid_receipt(root)
            receipt["adversarial_check"]["passed"] = False
            receipt["quality_checks"]["encoding"] = False
            receipt["trellis"]["check_passed"] = False
            receipt["trellis"]["finished"] = False

            errors = contract.validate_receipt(receipt, expected_root=root)

            combined = " ".join(errors)
            self.assertIn("adversarial_check", combined)
            self.assertIn("encoding", combined)
            self.assertIn("check_passed", combined)
            self.assertIn("finished", combined)

    def test_receipt_loader_rejects_invalid_json_and_inconsistent_git_state(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid = root / "invalid.json"
            invalid.write_text("{private-but-invalid", encoding="utf-8")
            self.assertTrue(contract.validate_receipt(invalid, expected_root=root))

            write_receipt_project(root, contract)
            receipt = valid_receipt(root)
            receipt["git"]["commit_performed"] = True
            receipt["git"]["commit"] = None
            errors = contract.validate_receipt(receipt, expected_root=root)
            self.assertIn("git.commit", " ".join(errors))

    def test_receipt_loader_rejects_duplicate_nested_json_keys(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            receipt_path = root / "receipt.json"
            raw = json.dumps(valid_receipt(root))
            receipt_path.write_text(
                raw.replace('"finished": true', '"finished": false, "finished": true', 1),
                encoding="utf-8",
            )

            errors = contract.validate_receipt(receipt_path, expected_root=root)

            self.assertIn("duplicate object keys", " ".join(errors))

    def test_receipt_rejects_requirements_that_do_not_exactly_cover_project_baseline(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            receipt = valid_receipt(root)
            receipt["requirements"][0]["id"] = "FAKE-ID"
            receipt["requirements"][1]["evidence_kinds"] = ["trust-me"]

            errors = contract.validate_receipt(receipt, expected_root=root)

            combined = " ".join(errors).lower()
            self.assertIn("baseline", combined)
            self.assertIn("requirements", combined)

    def test_receipt_rejects_nonexistent_or_unstarted_trellis_task_and_missing_check_artifact(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            receipt = valid_receipt(root)

            receipt["trellis"]["task"] = "FAKE-ID"
            missing_task_errors = contract.validate_receipt(receipt, expected_root=root)
            self.assertIn("task directory", " ".join(missing_task_errors).lower())

            receipt["trellis"]["task"] = "07-13-dxm-workflow-state-machine"
            task_dir = root / ".trellis" / "tasks" / "archive" / "2026-07" / receipt["trellis"]["task"]
            (task_dir / "task.json").write_text(json.dumps({"status": "planning"}), encoding="utf-8")
            (task_dir / "check.md").unlink()
            state_errors = contract.validate_receipt(receipt, expected_root=root)
            combined = " ".join(state_errors).lower()
            self.assertIn("started", combined)
            self.assertIn("check artifact", combined)

    def test_receipt_rejects_finished_active_in_progress_task_without_runtime_session(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            receipt = valid_receipt(root)
            archived = root / ".trellis" / "tasks" / "archive" / "2026-07" / RECEIPT_TASK
            active = root / ".trellis" / "tasks" / RECEIPT_TASK
            active.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(archived), str(active))
            (active / "task.json").write_text(
                json.dumps({"id": "dxm-workflow-state-machine", "status": "in_progress"}),
                encoding="utf-8",
            )

            errors = contract.validate_receipt(receipt, expected_root=root)

            combined = " ".join(errors).lower()
            self.assertIn("finished", combined)
            self.assertIn("archived", combined)

    def test_receipt_rejects_tasks_root_link_that_escapes_trusted_project(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            write_receipt_project(root, contract)
            tasks_link = root / ".trellis" / "tasks"
            external_tasks = base / "external-tasks"
            shutil.move(str(tasks_link), str(external_tasks))
            create_directory_link_or_skip(external_tasks, tasks_link)
            try:
                errors = contract.validate_receipt(valid_receipt(root), expected_root=root)
            finally:
                remove_directory_link(tasks_link)

            combined = " ".join(errors).lower()
            self.assertIn("task", combined)
            self.assertTrue("trusted project" in combined or "reparse" in combined, combined)

    def test_receipt_rejects_runtime_sessions_link_that_escapes_trusted_project(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            write_receipt_project(root, contract)
            sessions_link = root / ".trellis" / ".runtime" / "sessions"
            sessions_link.parent.mkdir(parents=True)
            external_sessions = base / "external-sessions"
            external_sessions.mkdir()
            create_directory_link_or_skip(external_sessions, sessions_link)
            try:
                errors = contract.validate_receipt(valid_receipt(root), expected_root=root)
            finally:
                remove_directory_link(sessions_link)

            combined = " ".join(errors).lower()
            self.assertIn("session", combined)
            self.assertTrue("trusted project" in combined or "reparse" in combined, combined)

    def test_receipt_rejects_hardlinked_check_artifact(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "project"
            write_receipt_project(root, contract)
            check = root / ".trellis" / "tasks" / "archive" / "2026-07" / RECEIPT_TASK / "check.md"
            external_check = base / "external-check.md"
            check.replace(external_check)
            os.link(external_check, check)

            errors = contract.validate_receipt(valid_receipt(root), expected_root=root)

            self.assertIn("hardlink", " ".join(errors).lower())

    def test_receipt_rejects_noncanonical_check_artifact_substitution(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            receipt = valid_receipt(root)
            receipt["trellis"]["check_artifact"] = "task.json"

            errors = contract.validate_receipt(receipt, expected_root=root)

            combined = " ".join(errors).lower()
            self.assertIn("check_artifact", combined)
            self.assertIn("check.md", combined)

    def test_receipt_accepts_archive_metadata_files_beside_month_directories(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            archive = root / ".trellis" / "tasks" / "archive"
            (archive / ".gitkeep").write_text("", encoding="utf-8")

            self.assertEqual(contract.validate_receipt(valid_receipt(root), expected_root=root), [])

    def test_receipt_rejects_task_archived_outside_canonical_month_directory(self) -> None:
        contract = load_contract()
        for directory in ("not-a-month", "0000-01", "2026-00", "2026-13", "2026-7"):
            with self.subTest(directory=directory), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write_receipt_project(root, contract)
                archive = root / ".trellis" / "tasks" / "archive"
                canonical = archive / "2026-07" / RECEIPT_TASK
                noncanonical = archive / directory / RECEIPT_TASK
                noncanonical.parent.mkdir()
                shutil.move(str(canonical), str(noncanonical))
                receipt_path = noncanonical / "completion.json"
                receipt_path.write_text(json.dumps(valid_receipt(root)), encoding="utf-8", newline="\n")

                errors = contract.validate_receipt(receipt_path, expected_root=root)

                self.assertIn("YYYY-MM", " ".join(errors))

    def test_receipt_requires_machine_verifiable_passing_check_verdict(self) -> None:
        contract = load_contract()
        cases = {
            "missing": "# Check\n\nNo structured verdict.\n",
            "prose_failed": "# Check\n\nVERDICT: FAILED\nBlocking findings remain.\n",
            "failed": "# Check\n\n<!-- DXM-CHECK:FAIL -->\nBlocking findings remain.\n",
            "unknown": "# Check\n\n<!-- DXM-CHECK:UNKNOWN -->\n",
            "duplicate": "<!-- DXM-CHECK:PASS -->\n<!-- DXM-CHECK:PASS -->\n",
            "unclosed_fence": "```text\n<!-- DXM-CHECK:PASS -->\n",
            "indented_code": "    <!-- DXM-CHECK:PASS -->\n",
            "tab_indented_code": "\t<!-- DXM-CHECK:PASS -->\n",
            "inline_code": "`<!-- DXM-CHECK:PASS -->`\n",
            "html_pre": "<pre>\n<!-- DXM-CHECK:PASS -->\n</pre>\n",
            "html_code": "<code><!-- DXM-CHECK:PASS --></code>\n",
            "html_script": "<script>\n<!-- DXM-CHECK:PASS -->\n</script>\n",
            "html_style": "<style>\n<!-- DXM-CHECK:PASS -->\n</style>\n",
            "html_textarea": "<textarea>\n<!-- DXM-CHECK:PASS -->\n</textarea>\n",
            "html_xmp": "<xmp>\n<!-- DXM-CHECK:PASS -->\n</xmp>\n",
            "html_fake_attribute_close": "<pre title=\"</pre>\">\n<!-- DXM-CHECK:PASS -->\n</pre>\n",
            "html_fake_comment_close": "<pre>\n<!-- fake </pre> -->\n<!-- DXM-CHECK:PASS -->\n</pre>\n",
            "outer_unclosed_comment": "<!-- wrapper\n<!-- DXM-CHECK:PASS -->\n",
            "cdata": "<![CDATA[\n<!-- DXM-CHECK:PASS -->\n]]>\n",
            "processing_instruction": "<?xml version=\"1.0\"\n<!-- DXM-CHECK:PASS -->\n?>\n",
            "surrounded": "prefix <!-- DXM-CHECK:PASS --> suffix\n",
            "mixed": "<!-- DXM-CHECK:PASS -->\n<!-- DXM-CHECK:FAIL -->\n",
            "unclosed_fail_after_pass": "<!-- DXM-CHECK:PASS -->\n<!-- DXM-CHECK:FAIL\n",
            "unclosed_pass_after_pass": "<!-- DXM-CHECK:PASS -->\n<!-- DXM-CHECK:PASS\n",
        }
        for label, content in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write_receipt_project(root, contract)
                check = (
                    root
                    / ".trellis"
                    / "tasks"
                    / "archive"
                    / "2026-07"
                    / RECEIPT_TASK
                    / "check.md"
                )
                check.write_text(content, encoding="utf-8", newline="\n")

                errors = contract.validate_receipt(valid_receipt(root), expected_root=root)

                self.assertIn("DXM-CHECK:PASS", " ".join(errors))

    def test_trellis_receipt_path_must_be_archived_completion_json(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            wrong = root / "receipt.json"
            correct = (
                root
                / ".trellis"
                / "tasks"
                / "archive"
                / "2026-07"
                / RECEIPT_TASK
                / "completion.json"
            )
            payload = json.dumps(valid_receipt(root))
            wrong.write_text(payload, encoding="utf-8")
            correct.write_text(payload, encoding="utf-8")

            wrong_errors = contract.validate_receipt(wrong, expected_root=root)
            correct_errors = contract.validate_receipt(correct, expected_root=root)

            combined = " ".join(wrong_errors).lower()
            self.assertIn("completion.json", combined)
            self.assertIn("archive", combined)
            self.assertEqual(correct_errors, [])

            real_parent = root / "real-parent"
            real_parent.mkdir()
            root_alias = root / "root-alias"
            create_directory_link_or_skip(real_parent, root_alias)
            try:
                aliased_root = root_alias / "project"
                write_receipt_project(aliased_root, contract)
                aliased_receipt = (
                    aliased_root
                    / ".trellis"
                    / "tasks"
                    / "archive"
                    / "2026-07"
                    / RECEIPT_TASK
                    / "completion.json"
                )
                aliased_receipt.write_text(
                    json.dumps(valid_receipt(aliased_root)),
                    encoding="utf-8",
                    newline="\n",
                )

                alias_errors = contract.validate_receipt(aliased_receipt, expected_root=aliased_root)

                self.assertEqual(alias_errors, [])
            finally:
                remove_directory_link(root_alias)

    def test_receipt_rejects_finished_claim_while_trellis_task_is_still_active(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            receipt = valid_receipt(root)
            sessions = root / ".trellis" / ".runtime" / "sessions"
            sessions.mkdir(parents=True)
            (sessions / "session.json").write_text(
                json.dumps({"current_task": ".trellis/tasks/07-13-dxm-workflow-state-machine"}),
                encoding="utf-8",
            )

            errors = contract.validate_receipt(receipt, expected_root=root)

            combined = " ".join(errors).lower()
            self.assertIn("finished", combined)
            self.assertIn("active", combined)

    def test_receipt_rejects_required_trellis_when_integration_is_not_ready(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            (root / ".trellis" / "config.yaml").unlink()

            errors = contract.validate_receipt(valid_receipt(root), expected_root=root)

            combined = " ".join(errors).lower()
            self.assertIn("trellis", combined)
            self.assertIn("ready", combined)

    def test_receipt_without_trusted_root_does_not_read_declared_project(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            declared_root = Path(tmp) / "declared"
            receipt = valid_receipt(declared_root)
            receipt["trellis"] = {
                "required": False,
                "task": None,
                "check_passed": False,
                "finished": False,
            }
            project_checks: list[bool] = []
            original = contract._validate_receipt_project
            contract._validate_receipt_project = lambda *args, **kwargs: project_checks.append(True) or []
            try:
                errors = contract.validate_receipt(receipt)
            finally:
                contract._validate_receipt_project = original

            self.assertFalse(project_checks)
            self.assertIn("expected_root", " ".join(errors))

    def test_receipt_root_mismatch_is_rejected_before_project_read(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            trusted_root = Path(tmp) / "trusted"
            declared_root = Path(tmp) / "declared"
            receipt = valid_receipt(declared_root)
            receipt["trellis"] = {
                "required": False,
                "task": None,
                "check_passed": False,
                "finished": False,
            }
            project_checks: list[bool] = []
            original = contract._validate_receipt_project
            contract._validate_receipt_project = lambda *args, **kwargs: project_checks.append(True) or []
            try:
                errors = contract.validate_receipt(receipt, expected_root=trusted_root)
            finally:
                contract._validate_receipt_project = original

            self.assertFalse(project_checks)
            self.assertIn("does not match expected_root", " ".join(errors))


class ValidatorCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )

    def test_audit_cli_supports_json_and_state_exit_codes(self) -> None:
        contract = load_contract()
        helper = AuditContractTests()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            ready = base / "ready"
            helper.write_docs(ready, contract)

            ready_result = self.run_cli("audit", "--root", str(ready), "--json")
            absent_result = self.run_cli("audit", "--root", str(base / "absent"), "--json")

            self.assertEqual(ready_result.returncode, contract.EXIT_OK, ready_result.stderr)
            self.assertEqual(json.loads(ready_result.stdout)["state"], contract.READY)
            self.assertEqual(absent_result.returncode, contract.EXIT_ABSENT, absent_result.stderr)
            self.assertEqual(json.loads(absent_result.stdout)["state"], contract.ABSENT)

    def test_text_cli_never_prints_success_guidance_for_partial(self) -> None:
        contract = load_contract()
        helper = AuditContractTests()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "partial"
            helper.write_docs(root, contract, include_baseline=False)

            result = self.run_cli("audit", "--root", str(root))

            self.assertEqual(result.returncode, contract.EXIT_PARTIAL, result.stderr)
            self.assertIn("state: PARTIAL", result.stdout)
            self.assertNotIn("Next", result.stdout)

    def test_baseline_and_receipt_cli_return_structured_json(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            baseline = root / "baseline.json"
            receipt = (
                root
                / ".trellis"
                / "tasks"
                / "archive"
                / "2026-07"
                / RECEIPT_TASK
                / "completion.json"
            )
            baseline.write_text(json.dumps(valid_baseline(root)), encoding="utf-8")
            receipt.write_text(json.dumps(valid_receipt(root)), encoding="utf-8")

            baseline_result = self.run_cli("baseline", "--file", str(baseline), "--json")
            receipt_result = self.run_cli(
                "receipt",
                "--root",
                str(root),
                "--file",
                str(receipt),
                "--json",
            )

            self.assertEqual(baseline_result.returncode, contract.EXIT_OK, baseline_result.stderr)
            self.assertEqual(json.loads(baseline_result.stdout)["valid"], True)
            self.assertEqual(receipt_result.returncode, contract.EXIT_OK, receipt_result.stderr)
            self.assertEqual(json.loads(receipt_result.stdout)["valid"], True)

    def test_receipt_cli_requires_explicit_trusted_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "receipt.json"
            receipt.write_text(json.dumps(valid_receipt(Path(tmp))), encoding="utf-8")

            result = self.run_cli("receipt", "--file", str(receipt), "--json")

            self.assertEqual(result.returncode, 2)
            self.assertIn("--root", result.stderr)

    def test_json_validation_cli_rejects_duplicate_object_keys(self) -> None:
        contract = load_contract()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_receipt_project(root, contract)
            baseline = root / "duplicate-baseline.json"
            receipt = root / "duplicate-receipt.json"
            baseline.write_text(
                json.dumps(valid_baseline(root)).replace(
                    '"schema_version": 1',
                    '"schema_version": 1, "schema_version": 1',
                    1,
                ),
                encoding="utf-8",
            )
            receipt.write_text(
                json.dumps(valid_receipt(root)).replace(
                    '"finished": true',
                    '"finished": false, "finished": true',
                    1,
                ),
                encoding="utf-8",
            )

            baseline_result = self.run_cli("baseline", "--file", str(baseline), "--json")
            receipt_result = self.run_cli(
                "receipt",
                "--root",
                str(root),
                "--file",
                str(receipt),
                "--json",
            )

            self.assertEqual(baseline_result.returncode, contract.EXIT_INVALID)
            self.assertEqual(receipt_result.returncode, contract.EXIT_INVALID)
            self.assertIn("duplicate object keys", baseline_result.stdout)
            self.assertIn("duplicate object keys", receipt_result.stdout)

    def test_version_is_doctor_visible(self) -> None:
        result = self.run_cli("--version")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dxm-validator", result.stdout)
        self.assertIn("contract=1", result.stdout)
        self.assertIn("baseline-schema=1", result.stdout)
        self.assertIn("receipt-schema=1", result.stdout)

    def test_core_only_install_reports_the_release_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            installed = Path(tmp) / "installed" / "dxm"
            shutil.copytree(REPO_ROOT / "skills" / "dxm", installed)
            expected_version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
            Path(tmp, "VERSION").write_text("unrelated-parent-version\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(installed / "scripts" / "validate_dxm.py"), "--version"],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((installed / "VERSION").read_text(encoding="utf-8").strip(), expected_version)
            self.assertIn(f"dxm-validator {expected_version}", result.stdout)


if __name__ == "__main__":
    unittest.main()

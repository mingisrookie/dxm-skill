import errno
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "skills" / "dxm" / "scripts"
SCAFFOLD = SCRIPTS / "scaffold_dxm.py"
ROUTER = SCRIPTS / "dxm.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import dxm_contract
import dxm_git
import dxm_inventory
import dxm_io
import scaffold_dxm


def baseline(root: Path, *, profile: str = "standard") -> dict:
    return {
        "schema_version": 1,
        "project_root": str(root.resolve()),
        "profile": profile,
        "goal": "Validate DXM v2 safety semantics.",
        "primary_users": ["maintainer"],
        "deliverables": ["governed project documents"],
        "non_goals": ["automatic Git mutation"],
        "runtime": {"entry_points": ["python skills/dxm/scripts/dxm.py"], "facts": ["stdlib only"]},
        "acceptance_criteria": [
            {"id": "AC-01", "description": "Init reports a truthful readiness state.", "evidence_kinds": ["cli"]}
        ],
        "validation_commands": ["python -m unittest discover -s tests -v"],
        "assumptions": [],
    }


def write_baseline(path: Path, root: Path, *, profile: str = "standard") -> None:
    path.write_text(json.dumps(baseline(root, profile=profile), ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def write_recovery_journal(
    root: Path,
    *,
    operation_id: str = "a" * 32,
    state: str = "prepared",
    entries: object | None = None,
    filename: str | None = None,
) -> Path:
    transactions = root / ".dxm" / "transactions"
    transactions.mkdir(parents=True, exist_ok=True)
    journal = transactions / (filename or f"{operation_id}.json")
    journal.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "operation_id": operation_id,
                "root": str(root.resolve()),
                "mode": "init",
                "state": state,
                "entries": [] if entries is None else entries,
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    return journal


class DxmV2CliTests(unittest.TestCase):
    def run_scaffold(self, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCAFFOLD), "--root", str(root), *arguments],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )

    def test_explicit_init_partial_returns_audit_exit_and_structured_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "partial"
            root.mkdir()
            # Existing human-maintained content is preserved, so the required
            # DXM block remains missing after initialization.
            (root / "项目完整链路说明.md").write_text("# manual chain\n", encoding="utf-8")
            baseline_path = Path(tmp) / "baseline.json"
            write_baseline(baseline_path, root)

            result = self.run_scaffold(root, "--mode", "init", "--baseline", str(baseline_path), "--output", "json")

            self.assertEqual(result.returncode, dxm_contract.EXIT_PARTIAL, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["operation_status"], "completed")
            self.assertEqual(payload["readiness"], dxm_contract.PARTIAL)
            self.assertEqual(payload["readiness_exit_code"], dxm_contract.EXIT_PARTIAL)
            self.assertEqual(payload["exit_code"], dxm_contract.EXIT_PARTIAL)
            self.assertGreaterEqual(payload["files_written"], 1)
            self.assertTrue((root / ".dxm" / "project.json").is_file())

    def test_requested_json_argument_error_is_structured_and_performs_no_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for name, output_arguments in (
                ("output-value", ("--output", "json")),
                ("output-equals", ("--output=json",)),
                ("json-alias", ("--json",)),
            ):
                with self.subTest(name=name):
                    root = Path(tmp) / name
                    result = self.run_scaffold(
                        root,
                        "--mode",
                        "scaffold-only",
                        "--inventory-depth",
                        "999",
                        *output_arguments,
                    )

                    self.assertEqual(result.returncode, dxm_contract.EXIT_BROKEN, result.stderr)
                    payload = json.loads(result.stdout)
                    self.assertEqual(payload["operation"], "scaffold-only")
                    self.assertEqual(payload["operation_status"], "failed")
                    self.assertEqual(payload["readiness"], "NOT_EVALUATED")
                    self.assertEqual(payload["exit_code"], dxm_contract.EXIT_BROKEN)
                    self.assertEqual(payload["error_code"], "DXM_E_INVALID_ARGUMENTS")
                    self.assertEqual(payload["issues"], ["invalid DXM CLI arguments"])
                    self.assertFalse(root.exists())
                    self.assertNotIn("usage:", result.stderr.lower())

    @unittest.skipUnless(shutil.which("git"), "Git is required for tracked-state privacy coverage")
    def test_explicit_init_with_tracked_local_state_returns_broken(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "tracked"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            tracked = root / ".dxm" / "local-state.json"
            tracked.parent.mkdir()
            tracked.write_text("{}\n", encoding="utf-8")
            subprocess.run(["git", "add", ".dxm/local-state.json"], cwd=root, check=True, capture_output=True)
            baseline_path = Path(tmp) / "baseline.json"
            write_baseline(baseline_path, root)

            result = self.run_scaffold(root, "--mode", "init", "--baseline", str(baseline_path), "--output", "json")

            self.assertEqual(result.returncode, dxm_contract.EXIT_BROKEN, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["readiness"], dxm_contract.BROKEN)
            self.assertEqual(payload["readiness_exit_code"], dxm_contract.EXIT_BROKEN)
            self.assertEqual(payload["exit_code"], dxm_contract.EXIT_BROKEN)
            self.assertIn("tracked", " ".join(payload["issues"]).lower())

    @unittest.skipUnless(shutil.which("git"), "Git is required for .gitignore coverage")
    def test_init_writes_portable_gitignore_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "portable-ignore"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            baseline_path = Path(tmp) / "baseline.json"
            write_baseline(baseline_path, root)

            result = self.run_scaffold(root, "--mode", "init", "--baseline", str(baseline_path))

            self.assertEqual(result.returncode, 0, result.stderr)
            gitignore = (root / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("# DXM:START\n.dxm/\n# DXM:END", gitignore)
            ignored = subprocess.run(
                ["git", "check-ignore", "-q", "--", ".dxm/project.json"],
                cwd=root,
                check=False,
            )
            self.assertEqual(ignored.returncode, 0)

    @unittest.skipUnless(shutil.which("git"), "Git is required for .gitignore coverage")
    def test_init_rejects_ambiguous_gitignore_markers_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "invalid-ignore"
            root.mkdir()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            original = "# DXM:END\n.dxm/\n# DXM:START trailing rule\n"
            gitignore = root / ".gitignore"
            gitignore.write_text(original, encoding="utf-8")
            baseline_path = Path(tmp) / "baseline.json"
            write_baseline(baseline_path, root)

            result = self.run_scaffold(root, "--mode", "init", "--baseline", str(baseline_path), "--output", "json")

            self.assertEqual(result.returncode, dxm_contract.EXIT_BROKEN, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["error_code"], "DXM_E_GITIGNORE_INVALID")
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(gitignore.read_text(encoding="utf-8"), original)

    def test_refresh_blocks_hydrates_existing_baseline_without_rewriting_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "baseline-refresh"
            root.mkdir()
            baseline_path = Path(tmp) / "baseline.json"
            write_baseline(baseline_path, root)
            initialized = self.run_scaffold(root, "--mode", "init", "--baseline", str(baseline_path))
            self.assertEqual(initialized.returncode, 0, initialized.stderr)

            persisted = root / ".dxm" / "project.json"
            before = persisted.read_text(encoding="utf-8")
            chain = root / "项目完整链路说明.md"
            chain.write_text(
                chain.read_text(encoding="utf-8").replace(
                    "- Governance profile: `standard`\n",
                    "",
                ),
                encoding="utf-8",
                newline="\n",
            )

            refreshed = self.run_scaffold(root, "--mode", "scaffold-only", "--refresh-blocks", "--output", "json")

            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            payload = json.loads(refreshed.stdout)
            self.assertEqual(payload["readiness"], "NOT_EVALUATED")
            self.assertEqual(payload["exit_code"], 0)
            self.assertEqual(persisted.read_text(encoding="utf-8"), before)
            self.assertIn("- Governance profile: `standard`", chain.read_text(encoding="utf-8"))
            audit = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_dxm.py"), "audit", "--root", str(root), "--json"],
                cwd=REPO_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            self.assertEqual(audit.returncode, 0, audit.stderr)

    def test_bounded_cli_rejects_legacy_and_out_of_range_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bounds"
            legacy = self.run_scaffold(root, "--output", "json")
            bounded = self.run_scaffold(root, "--mode", "scaffold-only", "--inventory-depth", "999")
            self.assertEqual(legacy.returncode, 2)
            payload = json.loads(legacy.stdout)
            self.assertEqual(payload["error_code"], "DXM_E_MODE_REQUIRED")
            self.assertEqual(payload["exit_code"], 2)
            self.assertEqual(payload["issues"], ["DXM v2 requires an explicit --mode"])
            self.assertEqual(bounded.returncode, 2)
            self.assertNotIn("Traceback", bounded.stderr)

    def test_recover_returns_the_final_readiness_exit_in_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "empty-project"
            root.mkdir()

            result = self.run_scaffold(root, "--recover", "--output", "json")

            self.assertEqual(result.returncode, dxm_contract.EXIT_ABSENT, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["operation"], "recover")
            self.assertEqual(payload["readiness"], dxm_contract.ABSENT)
            self.assertEqual(payload["exit_code"], dxm_contract.EXIT_ABSENT)
            self.assertIsInstance(payload["issues"], list)

    def test_router_status_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "absent"
            result = subprocess.run(
                [sys.executable, str(ROUTER), "status", "--root", str(root)],
                cwd=REPO_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, dxm_contract.EXIT_ABSENT, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["state"], dxm_contract.ABSENT)

    def test_doctor_preserves_nonready_exit_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "absent"
            result = subprocess.run(
                [sys.executable, str(ROUTER), "doctor", "--root", str(root), "--json"],
                cwd=REPO_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, dxm_contract.EXIT_ABSENT, result.stderr)
            self.assertEqual(json.loads(result.stdout)["readiness"], dxm_contract.ABSENT)

    def test_audit_and_doctor_block_a_pending_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "pending-transaction"
            root.mkdir()
            baseline_path = Path(tmp) / "baseline.json"
            write_baseline(baseline_path, root)
            initialized = self.run_scaffold(root, "--mode", "init", "--baseline", str(baseline_path))
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            write_recovery_journal(root)

            audit = subprocess.run(
                [sys.executable, str(SCRIPTS / "validate_dxm.py"), "audit", "--root", str(root), "--json"],
                cwd=REPO_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            doctor = subprocess.run(
                [sys.executable, str(ROUTER), "doctor", "--root", str(root), "--json"],
                cwd=REPO_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )

            self.assertEqual(audit.returncode, dxm_contract.EXIT_PARTIAL, audit.stderr)
            self.assertEqual(json.loads(audit.stdout)["state"], dxm_contract.PARTIAL)
            self.assertEqual(doctor.returncode, dxm_contract.EXIT_PARTIAL, doctor.stderr)
            doctor_payload = json.loads(doctor.stdout)
            self.assertTrue(doctor_payload["recovery_required"])
            self.assertEqual(doctor_payload["pending_transactions"], ["prepared"])

    def test_doctor_reports_a_stale_lock_as_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "stale-lock"
            root.mkdir()
            baseline_path = Path(tmp) / "baseline.json"
            write_baseline(baseline_path, root)
            initialized = self.run_scaffold(root, "--mode", "init", "--baseline", str(baseline_path))
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            lock = root / ".dxm" / "locks" / "project.lock"
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text(
                json.dumps(
                    {
                        "operation_id": "b" * 32,
                        "mode": "init",
                        "pid": 1,
                        "hostname": socket.gethostname(),
                        "started_epoch": 0,
                    }
                ),
                encoding="utf-8",
                newline="\n",
            )

            result = subprocess.run(
                [sys.executable, str(ROUTER), "doctor", "--root", str(root), "--json"],
                cwd=REPO_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, dxm_contract.EXIT_PARTIAL, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["recovery"]["lock_state"], "stale")
            self.assertTrue(payload["recovery_required"])


class DxmV2SafetyTests(unittest.TestCase):
    def test_write_io_error_is_structured_and_leaves_no_scaffold_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "write-error"
            root.mkdir()
            baseline_path = Path(tmp) / "baseline.json"
            write_baseline(baseline_path, root)
            stdout = io.StringIO()
            stderr = io.StringIO()
            old_argv = sys.argv
            try:
                sys.argv = [
                    str(SCAFFOLD),
                    "--root",
                    str(root),
                    "--mode",
                    "init",
                    "--baseline",
                    str(baseline_path),
                    "--output",
                    "json",
                ]
                with (
                    mock.patch.object(dxm_io.os, "replace", side_effect=OSError(errno.ENOSPC, "full")),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    exit_code = scaffold_dxm.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(exit_code, dxm_contract.EXIT_BROKEN)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["error_code"], dxm_io.ERROR_DISK_FULL)
            self.assertEqual(payload["exit_code"], dxm_contract.EXIT_BROKEN)
            self.assertEqual(payload["issues"], ["could not atomically replace a managed file"])
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertFalse((root / "AGENTS.md").exists())

    def test_gitignore_rejects_noncanonical_or_crossed_managed_markers(self) -> None:
        cases = (
            "# DXM:START trailing manual rule\n.dxm/\n# DXM:END\n",
            "# DXM:START\n.dxm/\n# DXM:END trailing manual rule\n",
            "# DXM:END\n.dxm/\n# DXM:START\n",
        )
        for existing in cases:
            with self.subTest(existing=existing):
                with self.assertRaises(dxm_git.GitPrivacyError):
                    dxm_git.managed_gitignore_content(existing)

    def test_result_counts_include_all_applied_managed_block_statuses(self) -> None:
        written, skipped = scaffold_dxm._result_counts(
            [
                ("chain baseline", "appended-baseline-block"),
                ("AGENTS", "appended-trellis-block"),
                ("README", "skipped-existing"),
            ]
        )
        self.assertEqual(written, 2)
        self.assertEqual(skipped, 1)

    def test_inventory_is_data_only_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "safe").mkdir()
            (root / "safe" / "evil`DXM-END\u202e.md").write_text("x", encoding="utf-8")
            (root / ".dxm").mkdir()
            (root / ".dxm" / "private.json").write_text("{}", encoding="utf-8")
            rendered = dxm_inventory.project_inventory(
                root,
                depth=4,
                max_entries=2,
                max_bytes=4096,
                timeout_seconds=5,
                skip_dirs=set(),
                is_sensitive_name=lambda _name, _is_file: False,
            )
            self.assertTrue(rendered.startswith("#### 文件结构快照（安全编码）\n\n````json\n"))
            self.assertNotIn("<!-- DXM:END -->", rendered)
            self.assertNotIn("evil`", rendered)
            self.assertNotIn("<!-- DXM:END -->", dxm_inventory.safe_markdown_label("`<!-- DXM:END -->"))
            payload = json.loads(rendered.split("\n", 3)[3].rsplit("\n````", 1)[0])
            self.assertEqual(payload["format"], "dxm-inventory-v2")
            self.assertTrue(payload["truncated"])
            self.assertTrue(any(item["note"] == "tool-or-build-state-not-expanded" for item in payload["entries"]))

    def test_inventory_stops_wide_enumeration_at_the_entry_bound(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            yielded = 0

            def wide_iterdir(directory: Path):
                nonlocal yielded
                for index in range(10_000):
                    yielded += 1
                    yield directory / f"synthetic-{index}.txt"

            with mock.patch.object(Path, "iterdir", wide_iterdir):
                rendered = dxm_inventory.project_inventory(
                    root,
                    depth=1,
                    max_entries=2,
                    max_bytes=4096,
                    timeout_seconds=5,
                    skip_dirs=set(),
                    is_sensitive_name=lambda _name, _is_file: False,
                )

            payload = json.loads(rendered.split("\n", 3)[3].rsplit("\n````", 1)[0])
            self.assertEqual(payload["truncated_reason"], "max-entries")
            self.assertLessEqual(yielded, 3)

    def test_inventory_checks_timeout_while_streaming_directory_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(4):
                (root / f"slow-{index}.txt").write_text("x", encoding="utf-8")
            original_iterdir = Path.iterdir
            yielded = 0

            def slow_iterdir(directory: Path):
                nonlocal yielded
                for child in original_iterdir(directory):
                    yielded += 1
                    time.sleep(0.2)
                    yield child

            with mock.patch.object(Path, "iterdir", slow_iterdir):
                rendered = dxm_inventory.project_inventory(
                    root,
                    depth=1,
                    max_entries=10,
                    max_bytes=4096,
                    timeout_seconds=0.5,
                    skip_dirs=set(),
                    is_sensitive_name=lambda _name, _is_file: False,
                )

            payload = json.loads(rendered.split("\n", 3)[3].rsplit("\n````", 1)[0])
            self.assertEqual(payload["truncated_reason"], "timeout")
            self.assertLess(yielded, 4)

    def test_inventory_final_json_never_exceeds_its_byte_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "entry.txt").write_text("x", encoding="utf-8")
            rendered = dxm_inventory.project_inventory(
                root,
                depth=1,
                max_entries=10,
                max_bytes=70,
                timeout_seconds=5,
                skip_dirs=set(),
                is_sensitive_name=lambda _name, _is_file: False,
            )

            encoded = rendered.split("\n", 3)[3].rsplit("\n````", 1)[0]
            payload = json.loads(encoded)
            self.assertLessEqual(len(encoded.encode("utf-8")), 70)
            self.assertTrue(payload["truncated"])

    def test_transaction_recovery_handles_replace_before_journal_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "AGENTS.md"
            target.write_text("before\n", encoding="utf-8")
            transaction = dxm_io.ProjectTransaction(root, "init")
            transaction.write_text(target, "after\n")
            # Model a crash after os.replace but before the applied flag was
            # durably acknowledged in the journal.
            transaction.entries[0]["applied"] = False
            transaction.state = "applying"
            transaction._save_journal()

            recovered = dxm_io.recover_transactions(root)

            self.assertEqual(recovered, 1)
            self.assertEqual(target.read_text(encoding="utf-8"), "before\n")
            self.assertEqual(dxm_io.pending_transaction_states(root), [])

    def test_committed_journal_blocks_new_writes_until_explicit_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "managed.txt"
            target.write_text("before\n", encoding="utf-8")
            transaction = dxm_io.ProjectTransaction(root, "init")
            transaction.write_text(target, "after\n")
            transaction.state = "committed"
            transaction._save_journal()

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCAFFOLD),
                    "--root",
                    str(root),
                    "--mode",
                    "scaffold-only",
                    "--output",
                    "json",
                ],
                cwd=REPO_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, dxm_contract.EXIT_BROKEN, result.stderr)
            self.assertEqual(json.loads(result.stdout)["error_code"], dxm_io.ERROR_RECOVERY_REQUIRED)
            self.assertFalse((root / "AGENTS.md").exists())
            self.assertEqual(dxm_io.recover_transactions(root), 1)
            self.assertEqual(dxm_io.pending_transaction_states(root), [])

    def test_recovery_rejects_forged_journal_paths_before_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            outside = Path(tmp) / "outside"
            outside.mkdir()
            sentinel = outside / "keep.txt"
            sentinel.write_text("keep\n", encoding="utf-8")
            write_recovery_journal(root, operation_id="../../../outside", state="committed", filename="forged.json")

            with mock.patch.object(dxm_io, "_safe_remove") as remove:
                with self.assertRaises(dxm_io.DxmIoError) as raised:
                    dxm_io.recover_transactions(root)

            self.assertEqual(raised.exception.code, dxm_io.ERROR_RECOVERY_REQUIRED)
            remove.assert_not_called()
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")

    def test_recovery_rejects_journal_filename_mismatch_and_malformed_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            write_recovery_journal(root, filename="other.json")

            with self.assertRaises(dxm_io.DxmIoError) as mismatched:
                dxm_io.recover_transactions(root)

            self.assertEqual(mismatched.exception.code, dxm_io.ERROR_RECOVERY_REQUIRED)
            shutil.rmtree(root / ".dxm" / "transactions")
            write_recovery_journal(root, state="applying", entries=["not-an-object"])
            result = subprocess.run(
                [sys.executable, str(SCAFFOLD), "--root", str(root), "--recover", "--output", "json"],
                cwd=REPO_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, dxm_contract.EXIT_BROKEN, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["error_code"], dxm_io.ERROR_RECOVERY_REQUIRED)
            self.assertNotIn("Traceback", result.stderr)

    def test_recovery_rejects_linked_transaction_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            outside = Path(tmp) / "outside"
            outside.mkdir()
            state = root / ".dxm"
            state.mkdir()
            linked_transactions = state / "transactions"
            try:
                linked_transactions.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory links unavailable: {exc}")

            with self.assertRaises(dxm_io.DxmIoError) as raised:
                dxm_io.recover_transactions(root)

            self.assertEqual(raised.exception.code, dxm_io.ERROR_RECOVERY_REQUIRED)

    def test_project_lock_reports_concurrent_operation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with dxm_io.ProjectLock(root, "init"):
                with self.assertRaises(dxm_io.DxmIoError) as raised:
                    dxm_io.ProjectLock(root, "init").acquire()
            self.assertEqual(raised.exception.code, dxm_io.ERROR_CONCURRENT_OPERATION)

    def test_project_lock_does_not_delete_a_tampered_lock_on_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = dxm_io.ProjectLock(root, "init")
            lock.acquire()
            lock.path.write_text("not-json\n", encoding="utf-8")

            with self.assertRaises(dxm_io.DxmIoError) as raised:
                lock.release()

            self.assertEqual(raised.exception.code, dxm_io.ERROR_RECOVERY_REQUIRED)
            self.assertTrue(lock.path.exists())
            lock._held = False
            lock.path.unlink()

    @unittest.skipUnless(os.name == "nt", "Windows-specific process liveness probe")
    def test_windows_pid_probe_does_not_call_os_kill(self) -> None:
        with mock.patch.object(dxm_io.os, "kill", side_effect=AssertionError("os.kill must not be used on Windows")):
            self.assertIs(dxm_io.ProjectLock._pid_is_alive(os.getpid()), True)

    def test_strict_schema_and_portable_paths_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            document = baseline(root)
            document["project_rooot"] = str(root)
            errors = dxm_contract.validate_baseline(document, expected_root=root)
            self.assertIn("unsupported", " ".join(errors))
            self.assertIn(
                "Windows reserved",
                dxm_contract._project_relative_path_error("CON/output.txt", "scope.paths[0]") or "",
            )

    def test_high_assurance_profile_requires_external_provenance_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.mkdir(exist_ok=True)
            # Baseline validation owns the profile value; receipt validation
            # additionally requires externally verifiable evidence for it.
            document = baseline(root, profile="high-assurance")
            self.assertEqual(dxm_contract.validate_baseline(document, expected_root=root), [])
            self.assertIn(
                "high-assurance",
                " ".join(dxm_contract._validate_external_provenance(None, required=True)),
            )


if __name__ == "__main__":
    unittest.main()

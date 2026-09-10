"""Release assets are developer outputs, not a skill runtime."""
from pathlib import Path
import hashlib
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from package_release import PACKAGE_FILES, build_release


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dxm-release-test-")
        self.addCleanup(self.tmp.cleanup)
        # macOS may expose its system temp directory through /var -> /private/var.
        self.directory = Path(self.tmp.name).resolve()
        self.root = self.directory / "source"
        self.root.mkdir()
        shutil.copytree(ROOT / "skills", self.root / "skills")
        shutil.copy2(ROOT / "VERSION", self.root / "VERSION")
        self.tag = "v" + (ROOT / "VERSION").read_text().strip()

    def test_core_and_bundle_have_exact_contents_and_valid_hashes(self):
        assets = build_release(self.root, self.directory / "release", self.tag)
        self.assertEqual(len(assets), 3)
        with zipfile.ZipFile(assets[0]) as archive:
            self.assertEqual(set(archive.namelist()), {"dxm/" + name for name in PACKAGE_FILES["dxm"]})
            self.assertIsNone(archive.testzip())
        with zipfile.ZipFile(assets[1]) as archive:
            expected = {"skills/" + skill + "/" + name for skill, names in PACKAGE_FILES.items() for name in names}
            self.assertEqual(set(archive.namelist()), expected)
            self.assertIsNone(archive.testzip())
        for line in assets[-1].read_text().splitlines():
            digest, name = line.split("  ", 1)
            self.assertEqual(hashlib.sha256((assets[-1].parent / name).read_bytes()).hexdigest(), digest)

    def test_repeated_builds_have_identical_bytes(self):
        first = build_release(self.root, self.directory / "first", self.tag)
        second = build_release(self.root, self.directory / "second", self.tag)
        self.assertEqual([p.read_bytes() for p in first], [p.read_bytes() for p in second])

    def test_tag_version_mismatch_fails_before_any_output(self):
        output = self.directory / "release"
        with self.assertRaises(ValueError):
            build_release(self.root, output, "v999.0.0")
        self.assertFalse(output.exists())

    def test_development_or_invalid_tags_are_not_released(self):
        for tag in ("v3.0.0-dev", "v03.0.0", "main", "v3.0.0/other"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                build_release(self.root, self.directory / "release", tag)
        self.assertFalse((self.directory / "release").exists())

    def test_extra_runtime_file_is_not_packaged(self):
        (self.root / "skills/dxm/old.py").write_text("# obsolete\n")
        with self.assertRaises(ValueError):
            build_release(self.root, self.directory / "release", self.tag)
        self.assertFalse((self.directory / "release").exists())

    def test_missing_license_is_rejected(self):
        (self.root / "skills/grilling/LICENSE").unlink()
        with self.assertRaises(ValueError):
            build_release(self.root, self.directory / "release", self.tag)

    def test_existing_output_is_not_overwritten(self):
        output = self.directory / "release"
        output.mkdir()
        marker = output / "keep.txt"
        marker.write_bytes(b"user-owned")
        with self.assertRaises(FileExistsError):
            build_release(self.root, output, self.tag)
        self.assertEqual(marker.read_bytes(), b"user-owned")
        self.assertEqual(list(output.iterdir()), [marker])

    def test_packaging_does_not_change_source(self):
        def snapshot():
            return {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        before = snapshot()
        build_release(self.root, self.directory / "release", self.tag)
        self.assertEqual(snapshot(), before)

    def test_release_is_tag_only_and_depends_on_full_test_matrix(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        release = workflow.split("\n  release:\n", 1)[1]
        self.assertIn("needs: test", release)
        self.assertIn("github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')", release)
        self.assertIn("persist-credentials: false", release)
        self.assertIn("--verify-tag", release)
        self.assertIn("sha256sum --check SHA256SUMS", release)
        self.assertIn("--draft=false --latest", release)
        self.assertNotIn("pull_request_target", workflow)

    def test_published_release_cannot_be_silently_replaced(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("A published release already exists; refusing to replace it.", workflow)
        self.assertIn("releases/latest", workflow)
        self.assertIn('commits/$tag', workflow)
        self.assertIn('commits/main', workflow)


if __name__ == "__main__":
    unittest.main()

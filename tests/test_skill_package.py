"""Static package regression checks; these do not measure model behavior."""
from pathlib import Path
import hashlib
import os
import re
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
CORE = SKILLS / "dxm"
NAMES = {"dxm", "grilling", "grill-me", "grill-with-docs", "domain-modeling"}
CORE_FILES = {"SKILL.md", "VERSION", "LICENSE", "agents/openai.yaml", "assets/templates/AGENTS.md.template", "references/dxm-method.md"}


def metadata(path):
    """Parse this repository's intentionally scalar-only frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing metadata start")
    fields, separator, body = text[4:].partition("\n---\n")
    if not separator or not body.strip():
        raise ValueError("missing metadata end or body")
    result = {}
    for line in fields.splitlines():
        key, sep, value = line.partition(": ")
        if not sep or key in result or not value.strip():
            raise ValueError("invalid or duplicate metadata field")
        result[key] = value.strip()
    if set(result) != {"name", "description"}:
        raise ValueError("unexpected metadata fields")
    if not re.fullmatch(r"[a-z]+(?:-[a-z]+)*", result["name"]):
        raise ValueError("invalid skill name")
    return result


def inspect_package(package):
    """Read files without executing package contents or changing their bytes."""
    issues = []
    for directory, dirs, names in os.walk(package, followlinks=False):
        parent = Path(directory)
        for name in list(dirs):
            item = parent / name
            if item.is_symlink() or getattr(item.lstat(), "st_file_attributes", 0) & 0x400:
                issues.append("linked directory")
                dirs.remove(name)
        for name in names:
            item = parent / name
            if item.is_symlink() or getattr(item.lstat(), "st_file_attributes", 0) & 0x400:
                issues.append("linked file")
                continue
            rel = item.relative_to(package).as_posix()
            if item.suffix.lower() not in {".md", ".yaml", ".template"} and name not in {"VERSION", "LICENSE"}:
                issues.append("unexpected file: " + rel)
            data = item.read_bytes()
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                issues.append("invalid utf8: " + rel)
                continue
            if data.startswith(b"\xef\xbb\xbf") or b"\r" in data or "\ufffd" in text:
                issues.append("invalid text format: " + rel)
            if not data.endswith(b"\n"):
                issues.append("missing newline: " + rel)
            if "trellis" in text.lower():
                issues.append("retired integration: " + rel)
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
                if re.match(r"[a-z]+://", link, re.I) or link.startswith("#"):
                    continue
                target = (item.parent / link.split("#", 1)[0]).resolve()
                if not target.is_relative_to(package.resolve()):
                    issues.append("external package reference: " + rel)
                elif not target.is_file():
                    issues.append("missing reference: " + rel)
    return issues


class PackageTests(unittest.TestCase):
    def test_exact_core_resources(self):
        self.assertEqual({p.relative_to(CORE).as_posix() for p in CORE.rglob("*") if p.is_file()}, CORE_FILES)
        self.assertFalse((CORE / "scripts").exists())
        self.assertFalse((CORE / "contract").exists())

    def test_all_five_packages_are_valid(self):
        self.assertEqual({p.name for p in SKILLS.iterdir() if p.is_dir()}, NAMES)
        for name in sorted(NAMES):
            with self.subTest(skill=name):
                self.assertEqual(metadata(SKILLS / name / "SKILL.md")["name"], name)
                self.assertEqual(inspect_package(SKILLS / name), [])

    def test_isolated_core_copy(self):
        with tempfile.TemporaryDirectory(prefix="dxm-package-") as tmp:
            dest = Path(tmp) / "isolated"
            shutil.copytree(CORE, dest)
            self.assertEqual(inspect_package(dest), [])
            self.assertEqual(metadata(dest / "SKILL.md")["name"], "dxm")
            self.assertFalse((dest.parent / "grilling").exists())

    def test_inspection_does_not_write(self):
        def snapshot():
            return {p.relative_to(CORE): hashlib.sha256(p.read_bytes()).digest() for p in CORE.rglob("*") if p.is_file()}
        before = snapshot()
        self.assertEqual(inspect_package(CORE), [])
        self.assertEqual(snapshot(), before)

    def test_independent_packages_include_original_license(self):
        for name in NAMES:
            self.assertEqual((SKILLS / name / "LICENSE").read_text(encoding="utf-8"), (ROOT / "LICENSE").read_text(encoding="utf-8"))

    def test_no_runtime_or_cache_files(self):
        for item in SKILLS.rglob("*"):
            self.assertNotIn(item.suffix.lower(), {".py", ".pyc", ".exe", ".ps1", ".sh"})
            self.assertNotIn(item.name, {"__pycache__", "contract", "scripts"})

    def test_no_machine_paths(self):
        for item in SKILLS.rglob("*"):
            if item.is_file():
                self.assertNotRegex(item.read_text(encoding="utf-8"), r"(?i)\b[A-Z]:[\\/]|/(?:Users|home)/[^\s/]+/")

    def test_consistent_version_and_release_documentation(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(version, (CORE / "VERSION").read_text(encoding="utf-8").strip())
        self.assertRegex(version, r"^\d+\.\d+\.\d+(?:-dev)?$")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(version, readme)
        if version.endswith("-dev"):
            self.assertIn(version + "（未发布）", changelog)
        else:
            self.assertIn("## v" + version + " - ", changelog)

    def test_interface_is_dependency_free(self):
        text = (CORE / "agents/openai.yaml").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("interface:\n"))
        keys = re.findall(r"^  ([a-z_]+):", text, re.M)
        self.assertEqual(set(keys), {"display_name", "short_description", "default_prompt"})
        self.assertEqual(len(keys), 3)
        self.assertIn("$dxm", text)
        self.assertNotIn("dependencies:", text)

    def test_no_project_integration_entries(self):
        self.assertFalse((ROOT / ".trellis").exists())
        for directory in [".agents/skills", ".codex/agents"]:
            self.assertEqual(list((ROOT / directory).glob("trellis*")), [])
        self.assertNotIn("trellis", (ROOT / ".gitattributes").read_text(encoding="utf-8").lower())

    def test_private_state_stays_ignored(self):
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".trellis/", text)
        self.assertIn(".dxm/", text)
        self.assertNotIn("# DXM:START", text)

    def test_ci_covers_entire_test_directory(self):
        text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("python -B -m unittest discover -s tests -v", text)
        self.assertNotIn("-p test_", text)
        self.assertIn("contents: read", text)
        actions = re.findall(r"uses: (\S+)", text)
        self.assertTrue(actions)
        self.assertTrue(all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", action) for action in actions))

    def test_active_docs_have_no_managed_runtime_contract(self):
        for name in ["AGENTS.md", "项目开发规范（AI协作）.md", "项目完整链路说明.md", "项目文件结构说明.md", "开发者AI开发与PR提交流程.md"]:
            text = (ROOT / name).read_text(encoding="utf-8")
            for term in ["DXM_RULES_ONLY", "<!-- DXM-", "--refresh-blocks", ".dxm/project.json", "test_rules_only.py"]:
                self.assertNotIn(term, text, name)

    def test_readme_links_exist(self):
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", (ROOT / "README.md").read_text(encoding="utf-8")):
            if not re.match(r"[a-z]+://", link, re.I):
                self.assertTrue((ROOT / link.split("#", 1)[0]).is_file(), link)


class NegativePackageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="dxm-negative-")
        self.addCleanup(temp.cleanup)
        self.package = Path(temp.name) / "core"
        shutil.copytree(CORE, self.package)

    def test_old_module_rejected(self):
        (self.package / "old.py").write_text("# historical only\n", encoding="utf-8", newline="\n")
        self.assertTrue(any("unexpected file" in i for i in inspect_package(self.package)))

    def test_old_dependency_rejected(self):
        with (self.package / "SKILL.md").open("a", encoding="utf-8") as f:
            f.write("\nTrellis integration\n")
        self.assertTrue(any("retired integration" in i for i in inspect_package(self.package)))

    def test_invalid_encoding_rejected(self):
        (self.package / "SKILL.md").write_bytes(b"\xff\xfe\n")
        self.assertTrue(any("invalid utf8" in i for i in inspect_package(self.package)))

    def test_missing_reference_rejected(self):
        (self.package / "references/dxm-method.md").unlink()
        self.assertTrue(any("missing reference" in i for i in inspect_package(self.package)))

    def test_nonportable_reference_rejected(self):
        with (self.package / "SKILL.md").open("a", encoding="utf-8") as f:
            f.write("\n[reference](../outside.md)\n")
        self.assertTrue(any("external package reference" in i for i in inspect_package(self.package)))

    def test_duplicate_metadata_rejected(self):
        (self.package / "SKILL.md").write_text("---\nname: dxm\nname: other\ndescription: sample\n---\nBody\n", encoding="utf-8", newline="\n")
        with self.assertRaises(ValueError):
            metadata(self.package / "SKILL.md")


class RulePresenceTests(unittest.TestCase):
    """Literal regression tripwires, not semantic or live-model evaluations."""
    def test_core_retains_meaningful_clarification(self):
        text = (CORE / "SKILL.md").read_text(encoding="utf-8")
        for term in ["没有阻塞就不问", "挑战隐藏假设", "一轮一个关键问题", "只读请求只分析", "不强制固定文件名", "不重复询问", "不自动授权"]:
            self.assertIn(term, text)

    def test_interviews_can_stop_without_authorizing_writes(self):
        for name in ["grilling", "grill-me", "grill-with-docs"]:
            text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
            for term in ["每轮只问一个", "停止访谈", "结束提问", "只读请求保持只读", "不自动写文件", "不自动授权"]:
                self.assertIn(term, text, name)

    def test_domain_materials_respect_readonly_scope(self):
        for path in (SKILLS / "domain-modeling").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertRegex(text, "授权|获准写入")
            self.assertRegex(text, "只读|没有写入授权")
        text = (SKILLS / "domain-modeling/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("优先更新已有合适文档", text)
        self.assertIn("不将猜测写成已接受事实", text)

    def test_verification_and_review_limits_remain(self):
        text = (CORE / "references/dxm-method.md").read_text(encoding="utf-8")
        for term in ["原故障", "自身复核", "不要将本轮未执行的历史测试算作通过", "不覆盖、不 reset"]:
            self.assertIn(term, text)

    def test_upgrade_is_scoped_and_non_overlay(self):
        text = (ROOT / "docs/migration-v3.md").read_text(encoding="utf-8")
        for term in ["不要仅覆盖同名文件", "保留其他工具和人工配置", "不应自动递归销毁", "不默认修改全局安装", "不能声称已完成全机卸载"]:
            self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()

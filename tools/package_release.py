"""Build deterministic release archives; never included in installed skills."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import stat
import zipfile

CORE_FILES = {"SKILL.md", "VERSION", "LICENSE", "agents/openai.yaml", "assets/templates/AGENTS.md.template", "references/dxm-method.md"}
PACKAGE_FILES = {
    "dxm": CORE_FILES,
    "grilling": {"SKILL.md", "LICENSE"},
    "grill-me": {"SKILL.md", "LICENSE"},
    "grill-with-docs": {"SKILL.md", "LICENSE"},
    "domain-modeling": {"SKILL.md", "LICENSE", "ADR-FORMAT.md", "CONTEXT-FORMAT.md"},
}


def regular_path(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("Release input/output must not be a linked path")


def release_inputs(root: Path, tag: str) -> dict[str, bytes]:
    """Validate the tag, exact package allowlist and portable text before writing."""
    if not re.fullmatch(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", tag):
        raise ValueError("Release tag must be a stable vMAJOR.MINOR.PATCH")
    for version_file in (root / "VERSION", root / "skills/dxm/VERSION"):
        if version_file.read_text(encoding="utf-8").strip() != tag[1:]:
            raise ValueError("Tag and version files disagree")
    skill_root = root / "skills"
    regular_path(skill_root)
    if {p.name for p in skill_root.iterdir()} != set(PACKAGE_FILES):
        raise ValueError("Unexpected package in release skill tree")
    result = {}
    for name, allowed in PACKAGE_FILES.items():
        package = skill_root / name
        regular_path(package)
        files = []
        for path in package.rglob("*"):
            regular_path(path)
            if path.is_file():
                files.append(path)
            elif not path.is_dir():
                raise ValueError("Non-regular package entry")
        if {p.relative_to(package).as_posix() for p in files} != allowed:
            raise ValueError("Unexpected or missing package resources: " + name)
        for path in files:
            if not stat.S_ISREG(path.stat().st_mode):
                raise ValueError("Non-regular release input")
            data = path.read_bytes()
            text = data.decode("utf-8")
            if data.startswith(b"\xef\xbb\xbf") or b"\r" in data or "\ufffd" in text or not data.endswith(b"\n"):
                raise ValueError("Release resources must be UTF-8/LF text")
            if "trellis" in text.lower():
                raise ValueError("Retired integration in skill package")
            result[path.relative_to(root).as_posix()] = data
    return result


def write_zip(path: Path, entries: dict[str, bytes]) -> None:
    """Fixed timestamps and no compression produce identical bytes across hosts."""
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, data)


def build_release(root: Path, output: Path, tag: str) -> list[Path]:
    entries = release_inputs(root, tag)
    output = output.absolute()
    # Never follow a symlink/reparse point or mix new archives with stale assets.
    for component in [output, *output.parents]:
        if component.exists() or component.is_symlink():
            regular_path(component)
    if output.exists():
        raise FileExistsError("Release output must be a new directory")
    output.mkdir(parents=True)
    core = output / ("dxm-skill-core-" + tag + ".zip")
    bundle = output / ("dxm-skills-bundle-" + tag + ".zip")
    write_zip(core, {name.removeprefix("skills/"): data for name, data in entries.items() if name.startswith("skills/dxm/")})
    write_zip(bundle, entries)
    assets = [core, bundle]
    manifest = output / "SHA256SUMS"
    checksums = "".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in assets)
    manifest.write_text(checksums, encoding="utf-8", newline="\n")
    return [*assets, manifest]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True, help="new output directory")
    args = parser.parse_args()
    try:
        for asset in build_release(Path(__file__).resolve().parents[1], args.output, args.tag):
            print(asset.name, asset.stat().st_size, hashlib.sha256(asset.read_bytes()).hexdigest())
    except (OSError, ValueError) as exc:
        parser.exit(2, "Release packaging failed: " + str(exc) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

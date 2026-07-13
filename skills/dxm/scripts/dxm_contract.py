#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic DXM baseline, readiness, and completion contracts."""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


CONTRACT_VERSION = 1
CONTRACT_MARKER = f"<!-- DXM-CONTRACT:{CONTRACT_VERSION} -->"
SCHEMA_VERSION = 1
BASELINE_SCHEMA_VERSION = SCHEMA_VERSION
RECEIPT_SCHEMA_VERSION = SCHEMA_VERSION

ABSENT = "ABSENT"
PARTIAL = "PARTIAL"
READY = "READY"
BROKEN = "BROKEN"

EXIT_OK = 0
EXIT_INVALID = 2
EXIT_BROKEN = EXIT_INVALID
EXIT_PARTIAL = 3
EXIT_ABSENT = 4

REQUIRED_FILES = (
    "AGENTS.md",
    "项目开发规范（AI协作）.md",
    "项目完整链路说明.md",
    "项目文件结构说明.md",
    "开发者AI开发与PR提交流程.md",
)

DXM_BLOCK_START = "<!-- DXM-RULES:START -->"
DXM_BLOCK_END = "<!-- DXM-RULES:END -->"
DXM_DOC_BLOCK_START = "<!-- DXM-DOC-RULES:START -->"
DXM_DOC_BLOCK_END = "<!-- DXM-DOC-RULES:END -->"
TRELLIS_BLOCK_START = "<!-- DXM-TRELLIS:START -->"
TRELLIS_BLOCK_END = "<!-- DXM-TRELLIS:END -->"
TRELLIS_START_STEP0_START = "<!-- DXM-TRELLIS-START-STEP0:START -->"
TRELLIS_START_STEP0_END = "<!-- DXM-TRELLIS-START-STEP0:END -->"
TRELLIS_WORKFLOW_OVERRIDE_START = "<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:START -->"
TRELLIS_WORKFLOW_OVERRIDE_END = "<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:END -->"
BASELINE_BLOCK_START = "<!-- DXM-PROJECT-BASELINE:START -->"
BASELINE_BLOCK_END = "<!-- DXM-PROJECT-BASELINE:END -->"
CHECK_PASS_MARKER = "<!-- DXM-CHECK:PASS -->"

WORKFLOW_MODES = ("audit", "init", "task", "scaffold-only")
RECEIPT_WORKFLOW_MODES = ("init", "task")
QUALITY_CHECKS = ("docs", "encoding", "secrets", "rollback")
STARTED_TRELLIS_STATUSES = ("in_progress", "review", "completed", "done")
COMPLETED_TRELLIS_STATUSES = ("completed", "done")
PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")
MANAGED_MARKER_RE = re.compile(r"<!--\s*(DXM-[A-Z0-9-]+):(START|END)\s*-->")
CONTRACT_MARKER_RE = re.compile(r"<!-- DXM-CONTRACT:(?P<version>[0-9]+) -->")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(?<!`)(?P<ticks>`+)(?!`)[^\n]*?(?<!`)(?P=ticks)(?!`)")
ARCHIVE_MONTH_RE = re.compile(r"^(?!0000)[0-9]{4}-(?:0[1-9]|1[0-2])$")
CREDENTIAL_FIELD_SUFFIXES = (
    "apikey",
    "accesstoken",
    "authtoken",
    "bearertoken",
    "token",
    "clientsecret",
    "secretkey",
    "secret",
    "secrets",
    "password",
    "passwd",
    "credential",
    "credentials",
    "creds",
    "authorization",
    "privatekey",
    "passphrase",
    "pwd",
)
CREDENTIAL_FIELD_NAMES = frozenset({"auth", *CREDENTIAL_FIELD_SUFFIXES})
TOKEN_METRIC_SUFFIXES = (
    "maxtoken",
    "maxtokens",
    "inputtoken",
    "inputtokens",
    "outputtoken",
    "outputtokens",
    "totaltoken",
    "totaltokens",
    "prompttoken",
    "prompttokens",
    "completiontoken",
    "completiontokens",
    "cachedtoken",
    "cachedtokens",
    "reasoningtoken",
    "reasoningtokens",
    "usedtoken",
    "usedtokens",
    "tokenused",
    "tokensused",
    "tokencount",
    "tokenscount",
    "tokenlimit",
    "tokenslimit",
    "tokenbudget",
    "tokensbudget",
    "tokenwindow",
    "tokenswindow",
    "tokenusage",
    "tokensusage",
)
CREDENTIAL_FIELD_WRAPPERS = (
    "value",
    "header",
    "literal",
    "data",
    "map",
    "ref",
    "reference",
    "config",
    "store",
    "entry",
    "field",
    "option",
    "options",
    "metadata",
    "payload",
    "object",
    "settings",
    "material",
)
CREDENTIAL_CONTEXT_SAFE_KEYS = frozenset(
    {"value", "name", "type", "source", "env", "reference", "ref", "id", "provider", "username", "user", "nested"}
)
ENV_REFERENCE_RE = re.compile(
    r"(?i)^(?:\$\{[A-Za-z_][A-Za-z0-9_]*\}|env:[A-Za-z_][A-Za-z0-9_]*|"
    r"<env:[A-Za-z_][A-Za-z0-9_]*>)$"
)
SAFE_CREDENTIAL_PLACEHOLDERS = frozenset(
    {
        "redacted",
        "placeholder",
        "example",
        "dummy",
        "test",
        "none",
        "unset",
        "not-set",
        "not set",
        "not-configured",
        "not configured",
        "disabled",
        "ignored",
        "<redacted>",
        "<placeholder>",
        "<example>",
        "<dummy>",
        "<test>",
        "<token>",
        "<unset>",
    }
)
ABSOLUTE_PATH_START_RE = re.compile(
    r"(?i)(?:(?<![A-Za-z0-9_])file:(?=(?:[\\/]|[A-Z]:(?:\\|/(?!/))))|"
    r"(?<!:)//[^/\s]+/[^/\s]+(?:/|$)|\\\\[^\\/\s]+[\\/][^\\/\s]+(?:[\\/]|$)|"
    r"(?<![A-Za-z0-9])[A-Z]:(?:\\|/(?!/))|(?<=-[A-Za-z])[A-Z]:(?:\\|/(?!/))|"
    r"(?<=-[A-Za-z])/(?!/)|(?<![A-Za-z0-9+./:\\-])/(?!/))"
)
CREDENTIAL_KEY_MATERIAL_RE = re.compile(
    r"(?i)(?:^|[\s._-])(?:api[\s._-]*keys?|access[\s._-]*tokens?|auth[\s._-]*tokens?|"
    r"bearer[\s._-]*tokens?|client[\s._-]*secrets?|ssh[\s._-]*private[\s._-]*keys?|"
    r"private[\s._-]*keys?|secret[\s._-]*keys?|passwords?|passwd|passphrases?|pwd|"
    r"credentials?|creds|authorization|tokens?|secrets?)"
    r"[\s._:=/\\\-：＝]+(?P<candidate>.+)$"
)
CREDENTIAL_ASSIGNMENT_SEPARATOR_RE = re.compile(r"[:=：＝]")
HIGH_CONFIDENCE_CREDENTIAL_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bBearer[ \t]+[A-Za-z0-9._~+/=-]{16,}\b"),
    re.compile(
        r"(?i)\bsk-(?!(?:example|test|placeholder|redacted|dummy)(?:[-_]|$))"
        r"[A-Za-z0-9_-]{16,}\b"
    ),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|token|"
        r"client[_-]?secret|secret|password|passwd)\s*[:=]\s*[\"']?"
        r"[A-Za-z0-9][A-Za-z0-9._~+/=-]{11,}"
    ),
)
SAFE_SCHEMA_PATH_KEYS = frozenset(
    {
        "goal",
        "primary_users",
        "deliverables",
        "non_goals",
        "runtime",
        "entry_points",
        "facts",
        "acceptance_criteria",
        "id",
        "description",
        "evidence_kinds",
        "validation_commands",
        "assumptions",
        "workflow_mode",
        "requirements",
        "status",
        "evidence",
        "adversarial_check",
        "passed",
        "summary",
        "quality_checks",
        "docs",
        "encoding",
        "secrets",
        "rollback",
        "trellis",
        "required",
        "task",
        "check_passed",
        "finished",
        "check_artifact",
        "git",
        "commit_performed",
        "commit",
        "push_performed",
        "branch",
    }
)


class ContractError(ValueError):
    """Raised when a baseline cannot satisfy the deterministic contract."""

    def __init__(self, errors: str | list[str] | tuple[str, ...]):
        if isinstance(errors, str):
            errors = [errors]
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


class _DuplicateJsonKeyError(ValueError):
    pass


@dataclass(frozen=True)
class AuditResult:
    root: Path
    state: str
    issues: tuple[str, ...] = ()

    @property
    def exit_code(self) -> int:
        return {
            READY: EXIT_OK,
            BROKEN: EXIT_INVALID,
            PARTIAL: EXIT_PARTIAL,
            ABSENT: EXIT_ABSENT,
        }[self.state]

    @property
    def is_ready(self) -> bool:
        return self.state == READY

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "root": str(self.root),
            "issues": list(self.issues),
            "exit_code": self.exit_code,
            "contract_version": CONTRACT_VERSION,
            "baseline_schema_version": BASELINE_SCHEMA_VERSION,
        }


def _canonical_path(path: Path | str) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _lexical_absolute_path(path: Path | str) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def _same_path(left: Path | str, right: Path | str) -> bool:
    return os.path.normcase(str(_canonical_path(left))) == os.path.normcase(str(_canonical_path(right)))


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _trusted_project_path_error(root: Path, path: Path, label: str) -> str | None:
    """Reject project artifacts that escape root or traverse link/reparse nodes."""

    lexical_root = _lexical_absolute_path(root)
    lexical_path = _lexical_absolute_path(path)
    canonical_root = _canonical_path(root)
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError:
        return f"{label} must stay inside the trusted project"

    current = lexical_root
    for part in relative.parts:
        current /= part
        if _is_link_or_reparse(current):
            return f"{label} must stay inside the trusted project and not use symlink/reparse paths"

    try:
        metadata = lexical_path.lstat()
    except OSError:
        metadata = None
    if metadata is not None and stat.S_ISREG(metadata.st_mode) and metadata.st_nlink > 1:
        return f"{label} must stay inside the trusted project and not use hardlinked files"

    try:
        resolved = lexical_path.resolve(strict=True)
        resolved.relative_to(canonical_root)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return f"{label} must stay inside the trusted project"
    return None


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _credential_field_name(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
    if normalized.endswith("publickey") or normalized.endswith("publickeys"):
        return False
    while True:
        normalized = re.sub(r"[0-9]+$", "", normalized)
        matching_wrappers = [wrapper for wrapper in CREDENTIAL_FIELD_WRAPPERS if normalized.endswith(wrapper)]
        stripped = (
            normalized[: -len(max(matching_wrappers, key=len))]
            if matching_wrappers
            else normalized
        )
        if stripped == normalized:
            break
        normalized = stripped
    if any(normalized.endswith(suffix) for suffix in TOKEN_METRIC_SUFFIXES):
        return False
    return normalized in CREDENTIAL_FIELD_NAMES or any(
        normalized.endswith(suffix) or normalized.endswith(f"{suffix}s")
        for suffix in CREDENTIAL_FIELD_SUFFIXES
    )


def _credential_assignments(value: str):
    """Yield credential-shaped assignment candidates without exposing them."""

    for separator in CREDENTIAL_ASSIGNMENT_SEPARATOR_RE.finditer(value):
        field = value[: separator.start()].strip()
        if not _credential_field_name(field):
            continue
        candidate = value[separator.end() :]
        candidate = re.split(r"[;\r\n]", candidate, maxsplit=1)[0].strip().strip("\"'")
        yield candidate


def _credential_scalar(value: str) -> bool:
    candidate = value.strip()
    lowered = candidate.lower()
    reference_candidate = candidate.rstrip(".!?,")
    if not candidate or ENV_REFERENCE_RE.fullmatch(reference_candidate):
        return False
    if lowered in SAFE_CREDENTIAL_PLACEHOLDERS:
        return False
    if re.fullmatch(
        r"(?i)Bearer[ \t]+(?:<redacted>|<token>|<placeholder>|redacted|placeholder)[.!]?",
        candidate,
    ):
        return False
    return True


def _contains_high_confidence_credential(value: str) -> bool:
    if any(pattern.search(value) is not None for pattern in HIGH_CONFIDENCE_CREDENTIAL_PATTERNS):
        return True
    return any(len(candidate) >= 12 and _credential_scalar(candidate) for candidate in _credential_assignments(value))


def _credential_field(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    if any(True for _candidate in _credential_assignments(key)):
        return True
    return _credential_field_name(key)


def _credential_hidden_in_key(key: str) -> bool:
    if _contains_high_confidence_credential(key):
        return True
    material = CREDENTIAL_KEY_MATERIAL_RE.search(key)
    if material is None:
        return False
    candidate = material.group("candidate").strip().strip("\"'")
    return len(candidate) >= 12 and _credential_scalar(candidate)


def _credential_errors(value: Any, path: str, credential_context: bool = False) -> list[str]:
    errors: list[str] = []
    if isinstance(value, str):
        if _contains_high_confidence_credential(value) or (credential_context and _credential_scalar(value)):
            errors.append(f"{path} contains a high-confidence credential")
        return errors
    if credential_context and isinstance(value, (int, float)) and not isinstance(value, bool):
        return [f"{path} contains a high-confidence credential"]
    if isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_credential_errors(item, f"{path}[{index}]", credential_context))
        return errors
    if isinstance(value, dict):
        for index, (key, item) in enumerate(value.items()):
            safe_key = isinstance(key, str) and key in SAFE_SCHEMA_PATH_KEYS
            child = f"{path}.{key}" if safe_key else f"{path}[{index}]"
            if isinstance(key, str) and _credential_hidden_in_key(key):
                errors.append(f"{path}[{index}] key contains a high-confidence credential")
            elif credential_context and isinstance(key, str):
                normalized_key = re.sub(r"[^a-z0-9]", "", key.casefold())
                if (
                    normalized_key not in CREDENTIAL_CONTEXT_SAFE_KEYS
                    and len(key.strip()) >= 12
                    and _credential_scalar(key)
                ):
                    errors.append(f"{path}[{index}] key contains a high-confidence credential")
            errors.extend(_credential_errors(item, child, credential_context or _credential_field(key)))
    return errors


def _check_verdict_errors(content: str) -> list[str]:
    marker_fragments = re.findall(r"DXM[-_]CHECK", content, re.IGNORECASE)
    if len(marker_fragments) != 1 or content.count(CHECK_PASS_MARKER) != 1:
        return [f"trellis.check artifact must contain exactly one canonical {CHECK_PASS_MARKER} verdict"]

    first_nonempty = next((line.rstrip("\r") for line in content.splitlines() if line.strip()), None)
    if first_nonempty != CHECK_PASS_MARKER:
        return [f"trellis.check artifact must contain exactly one canonical {CHECK_PASS_MARKER} verdict"]

    top_level_markers = 0
    fence_char: str | None = None
    fence_length = 0
    for line in content.splitlines(keepends=True):
        if fence_char is not None:
            closing = re.match(
                rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*(?:\r?\n)?$",
                line,
            )
            if closing is not None:
                fence_char = None
                fence_length = 0
            continue
        opening = FENCE_OPEN_RE.match(line)
        if opening is not None:
            fence = opening.group(1)
            fence_char = fence[0]
            fence_length = len(fence)
            continue
        marker_line = line.rstrip("\r\n")
        if marker_line == CHECK_PASS_MARKER:
            top_level_markers += 1
    if fence_char is not None or top_level_markers != 1:
        return [f"trellis.check artifact must contain exactly one canonical {CHECK_PASS_MARKER} verdict"]
    return []


def _validate_string_list(value: Any, field: str, *, allow_empty: bool) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return [f"{field} must be a list of strings"]
    if not allow_empty and not value:
        errors.append(f"{field} must not be empty")
    for index, item in enumerate(value):
        if not _is_nonempty_string(item):
            errors.append(f"{field}[{index}] must be a non-empty string")
    return errors


def validate_baseline(data: Any, expected_root: Path | None = None) -> list[str]:
    """Return all baseline schema errors without exposing baseline values."""

    if not isinstance(data, dict):
        return ["baseline must be a JSON object"]

    errors: list[str] = []
    required = (
        "schema_version",
        "project_root",
        "goal",
        "primary_users",
        "deliverables",
        "non_goals",
        "runtime",
        "acceptance_criteria",
        "validation_commands",
        "assumptions",
    )
    for field in required:
        if field not in data:
            errors.append(f"missing required field: {field}")

    if type(data.get("schema_version")) is not int or data.get("schema_version") != BASELINE_SCHEMA_VERSION:
        errors.append(f"schema_version must be {BASELINE_SCHEMA_VERSION}")

    project_root = data.get("project_root")
    if not _is_nonempty_string(project_root):
        errors.append("project_root must be a non-empty absolute path")
    elif not Path(project_root).is_absolute():
        errors.append("project_root must be an absolute path")
    elif os.path.normcase(project_root) != os.path.normcase(str(_canonical_path(project_root))):
        errors.append("project_root must be canonical")
    elif expected_root is not None and not _same_path(project_root, expected_root):
        errors.append("project_root does not match the expected root")

    if not _is_nonempty_string(data.get("goal")):
        errors.append("goal must be a non-empty string")

    errors.extend(_validate_string_list(data.get("primary_users"), "primary_users", allow_empty=False))
    errors.extend(_validate_string_list(data.get("deliverables"), "deliverables", allow_empty=False))
    errors.extend(_validate_string_list(data.get("non_goals"), "non_goals", allow_empty=True))
    errors.extend(_validate_string_list(data.get("validation_commands"), "validation_commands", allow_empty=False))
    errors.extend(_validate_string_list(data.get("assumptions"), "assumptions", allow_empty=True))

    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        errors.append("runtime must be an object")
    else:
        errors.extend(_validate_string_list(runtime.get("entry_points"), "runtime.entry_points", allow_empty=False))
        errors.extend(_validate_string_list(runtime.get("facts"), "runtime.facts", allow_empty=True))

    acceptance = data.get("acceptance_criteria")
    if not isinstance(acceptance, list):
        errors.append("acceptance_criteria must be a list")
    elif not acceptance:
        errors.append("acceptance_criteria must not be empty")
    else:
        seen_ids: set[str] = set()
        for index, item in enumerate(acceptance):
            prefix = f"acceptance_criteria[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            acceptance_id = item.get("id")
            if not _is_nonempty_string(acceptance_id):
                errors.append(f"{prefix}.id must be a non-empty string")
            elif acceptance_id in seen_ids:
                errors.append(f"duplicate acceptance id at {prefix}.id")
            else:
                seen_ids.add(acceptance_id)
            if not _is_nonempty_string(item.get("description")):
                errors.append(f"{prefix}.description must be a non-empty string")
            evidence_errors = _validate_string_list(
                item.get("evidence_kinds"),
                f"{prefix}.evidence_kinds",
                allow_empty=False,
            )
            errors.extend(evidence_errors)
            evidence_kinds = item.get("evidence_kinds")
            if isinstance(evidence_kinds, list) and len(evidence_kinds) != len(set(map(str, evidence_kinds))):
                errors.append(f"{prefix}.evidence_kinds contains duplicates")
    errors.extend(_credential_errors(data, "baseline"))
    return errors


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError
        result[key] = value
    return result


def _load_json_object(path: Path, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, [f"{label} file does not exist: {path}"]
    except UnicodeDecodeError:
        return None, [f"{label} file is not valid UTF-8: {path}"]
    except OSError as exc:
        return None, [f"cannot read {label} file {path}: {exc.__class__.__name__}"]
    try:
        data = json.loads(raw, object_pairs_hook=_unique_json_object)
    except _DuplicateJsonKeyError:
        return None, [f"{label} contains duplicate object keys: {path}"]
    except json.JSONDecodeError as exc:
        return None, [f"{label} is invalid JSON at line {exc.lineno}, column {exc.colno}: {path}"]
    if not isinstance(data, dict):
        return None, [f"{label} must be a JSON object"]
    return data, []


def load_baseline(
    path: Path,
    expected_root: Path | None = None,
    *,
    require_trusted_path: bool = False,
) -> dict[str, Any]:
    """Load a UTF-8 baseline and raise ContractError for any schema issue.

    ``expected_root`` validates the persisted project_root value. Callers reading
    the project's managed ``.dxm/project.json`` also set ``require_trusted_path``;
    explicit import files may legitimately live outside the target project.
    """

    baseline_path = Path(path)
    if require_trusted_path:
        if expected_root is None:
            raise ContractError("expected_root is required for trusted baseline path validation")
        path_error = _trusted_project_path_error(
            _canonical_path(expected_root),
            baseline_path,
            "project baseline",
        )
        if path_error is not None:
            raise ContractError(path_error)
    data, errors = _load_json_object(baseline_path, "baseline")
    if data is not None:
        errors.extend(validate_baseline(data, expected_root))
    if errors:
        raise ContractError(errors)
    assert data is not None
    return data


def _safe_markdown_text(value: Any) -> str:
    text = " ".join(str(value).splitlines()).strip()
    return text.replace("<!--", "&lt;!--").replace("-->", "--&gt;").replace("|", "\\|")


def _portable_baseline_text(value: Any, project_root: str) -> str:
    text = " ".join(str(value).splitlines()).strip()
    canonical = str(_canonical_path(project_root))
    root_norm = os.path.normcase(os.path.normpath(canonical))
    variants = {canonical, canonical.replace("\\", "/"), canonical.replace("/", "\\")}
    root_variants = sorted((item for item in variants if item and item not in {"/", "\\"}), key=len, reverse=True)
    cursor = 0
    while True:
        absolute = ABSOLUTE_PATH_START_RE.search(text, cursor)
        if absolute is None:
            break
        start = absolute.start()
        tail = text[start:]
        matching_root = next(
            (
                variant
                for variant in root_variants
                if os.path.normcase(tail[: len(variant)]) == os.path.normcase(variant)
                and (
                    len(tail) == len(variant)
                    or tail[len(variant)] in "/\\ \t`<>{}[]\"'|.,;:)]}"
                )
            ),
            None,
        )
        end = start + len(matching_root) if matching_root is not None else start
        while end < len(text) and text[end] not in " \t`<>{}[]\"'|":
            end += 1
        if matching_root is not None and end < len(text) and text[end] in "`<>{}[]\"'|":
            ambiguous_tail = text[end:]
            if ".." in ambiguous_tail or "\\" in ambiguous_tail or "/" in ambiguous_tail:
                text = f"{text[:start]}$ABSOLUTE_PATH"
                break
        token = text[start:end]
        core = token.rstrip(".,;:)]}")
        punctuation = token[len(core) :]

        if matching_root is not None:
            suffix = core[len(matching_root) :].replace("\\", os.sep).replace("/", os.sep)
            candidate = os.path.normpath(canonical + suffix)
        elif core.casefold().startswith("file://"):
            candidate = ""
        else:
            candidate = os.path.normpath(core)

        candidate_norm = os.path.normcase(candidate)
        try:
            inside_root = bool(candidate) and os.path.commonpath((root_norm, candidate_norm)) == root_norm
        except ValueError:
            inside_root = False
        if not inside_root:
            text = f"{text[:start]}$ABSOLUTE_PATH"
            break

        if end < len(text) and text[end].isspace() and end > start + len(matching_root or ""):
            ambiguous_tail = text[end:]
            if ".." in ambiguous_tail or "\\" in ambiguous_tail or "/" in ambiguous_tail:
                text = f"{text[:start]}$ABSOLUTE_PATH"
                break

        relative = os.path.relpath(candidate_norm, root_norm)
        if relative == os.curdir:
            replacement = f"$PROJECT_ROOT{punctuation}"
        else:
            portable_relative = relative.replace("\\", "/")
            replacement = f"$PROJECT_ROOT/{portable_relative}{punctuation}"
        text = f"{text[:start]}{replacement}{text[end:]}"
        cursor = start + len(replacement)
    if re.search(r"\$PROJECT_ROOT[^\s]*(?:\.\.|\\)", text) or any(
        os.path.normcase(variant) in os.path.normcase(text) for variant in root_variants
    ) or re.search(
        r"(?i)(?:(?<![A-Za-z0-9_])file:(?=(?:[\\/]|[A-Z]:(?:\\|/(?!/))))|"
        r"(?<![A-Za-z0-9])[A-Z]:(?:\\|/(?!/))|(?<=-[A-Za-z])[A-Z]:(?:\\|/(?!/))|"
        r"\\\\|(?<!:)//[^/\s]+/[^/\s]+)",
        text,
    ):
        text = "$ABSOLUTE_PATH"
    return _safe_markdown_text(text)


def _portable_markdown_list(lines: list[str], project_root: str) -> list[str]:
    if not lines:
        return ["- _None._"]
    return [f"- {_portable_baseline_text(item, project_root)}" for item in lines]


def baseline_markdown(data: dict[str, Any]) -> str:
    """Render a complete, safe managed baseline block for the chain document."""

    errors = validate_baseline(data)
    if errors:
        raise ContractError(errors)
    runtime = data["runtime"]
    project_root = data["project_root"]
    lines = [
        BASELINE_BLOCK_START,
        "",
        "## DXM 项目基线",
        "",
        f"- Schema version: `{BASELINE_SCHEMA_VERSION}`",
        "- Project root: local canonical path stored in `.dxm/project.json`; not embedded in shared Markdown.",
        f"- Goal: {_portable_baseline_text(data['goal'], project_root)}",
        "",
        "### Primary users / callers",
        "",
        *_portable_markdown_list(data["primary_users"], project_root),
        "",
        "### Deliverables",
        "",
        *_portable_markdown_list(data["deliverables"], project_root),
        "",
        "### Non-goals",
        "",
        *_portable_markdown_list(data["non_goals"], project_root),
        "",
        "### Runtime entry points",
        "",
        *_portable_markdown_list(runtime["entry_points"], project_root),
        "",
        "### Runtime facts",
        "",
        *_portable_markdown_list(runtime["facts"], project_root),
        "",
        "### Acceptance criteria",
        "",
        "| ID | Criterion | Required evidence |",
        "| --- | --- | --- |",
    ]
    for item in data["acceptance_criteria"]:
        evidence = ", ".join(_portable_baseline_text(kind, project_root) for kind in item["evidence_kinds"])
        lines.append(
            f"| {_portable_baseline_text(item['id'], project_root)} | "
            f"{_portable_baseline_text(item['description'], project_root)} | {evidence} |"
        )
    lines.extend(
        [
            "",
            "### Validation commands",
            "",
            *[
                f"- `{_portable_baseline_text(command, project_root).replace('`', '&#96;')}`"
                for command in data["validation_commands"]
            ],
            "",
            "### Assumptions",
            "",
            *_portable_markdown_list(data["assumptions"], project_root),
            "",
            BASELINE_BLOCK_END,
            "",
        ]
    )
    return "\n".join(lines)


def _mask_markdown_code(text: str) -> str:
    return "".join(character if character in "\r\n" else " " for character in text)


def markdown_noncode_surface(content: str) -> str:
    """Mask complete fenced/inline code while preserving source offsets."""

    surface: list[str] = []
    fence_char: str | None = None
    fence_length = 0
    fence_buffer: list[str] = []
    for line in content.splitlines(keepends=True):
        if fence_char is not None:
            fence_buffer.append(line)
            closing = re.match(
                rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*(?:\r?\n)?$",
                line,
            )
            if closing is not None:
                surface.extend(_mask_markdown_code(buffered) for buffered in fence_buffer)
                fence_char = None
                fence_length = 0
                fence_buffer = []
            continue

        opening = FENCE_OPEN_RE.match(line)
        if opening is not None:
            fence = opening.group(1)
            fence_char = fence[0]
            fence_length = len(fence)
            fence_buffer = [line]
            continue
        surface.append(INLINE_CODE_RE.sub(lambda match: " " * len(match.group(0)), line))
    if fence_buffer:
        # An unclosed fence cannot hide integrity-significant content.
        surface.extend(fence_buffer)
    return "".join(surface)


def _html_comment_fragments(content: str):
    """Yield every HTML-comment-shaped fragment, including unclosed/nested starts."""

    for opening in re.finditer(r"<!--", content):
        closing = content.find("-->", opening.end())
        yield content[opening.start() :] if closing < 0 else content[opening.start() : closing + 3]


def validate_marker_layout(content: str, start: str, end: str) -> list[str]:
    """Accept only zero pairs or one ordered START/END pair."""

    marker_surface = markdown_noncode_surface(content)
    errors: list[str] = []
    start_shape = re.fullmatch(r"<!--\s*([A-Z0-9-]+):START\s*-->", start)
    end_shape = re.fullmatch(r"<!--\s*([A-Z0-9-]+):END\s*-->", end)
    if start_shape is not None and end_shape is not None and start_shape.group(1) == end_shape.group(1):
        label = start_shape.group(1)
        label_pattern = re.compile(rf"(?<![A-Za-z0-9-]){re.escape(label)}(?=\s|:)", re.IGNORECASE)
        for candidate in _html_comment_fragments(marker_surface):
            if label_pattern.search(candidate) is not None and re.search(
                r"(?<![A-Za-z])(start|end)(?![A-Za-z])",
                candidate,
                re.IGNORECASE,
            ) and candidate not in (start, end):
                errors.append("malformed managed marker syntax")
    start_count = marker_surface.count(start)
    end_count = marker_surface.count(end)
    if start_count > 1:
        errors.append(f"duplicate start marker: {start}")
    if end_count > 1:
        errors.append(f"duplicate end marker: {end}")
    if start_count and not end_count:
        errors.append(f"orphan start marker: {start}")
    if end_count and not start_count:
        errors.append(f"orphan end marker: {end}")
    if start_count == 1 and end_count == 1 and marker_surface.find(start) > marker_surface.find(end):
        errors.append(f"markers are out of order: {end} precedes {start}")
    return errors


def validate_managed_markers(content: str) -> list[str]:
    """Validate every canonical DXM marker as disjoint, ordered blocks."""

    marker_surface = markdown_noncode_surface(content)
    labels = {match.group(1) for match in MANAGED_MARKER_RE.finditer(marker_surface)}
    errors: list[str] = []
    for comment in _html_comment_fragments(marker_surface):
        if re.search(r"dxm", comment, re.IGNORECASE) and re.search(
            r"(?<![A-Za-z])(start|end)(?![A-Za-z])",
            comment,
            re.IGNORECASE,
        ):
            if MANAGED_MARKER_RE.fullmatch(comment) is None:
                errors.append("malformed DXM managed marker syntax")
    for label in sorted(labels):
        errors.extend(
            validate_marker_layout(
                marker_surface,
                f"<!-- {label}:START -->",
                f"<!-- {label}:END -->",
            )
        )

    stack: list[str] = []
    for marker in MANAGED_MARKER_RE.finditer(marker_surface):
        label, kind = marker.groups()
        if kind == "START":
            if stack:
                errors.append("nested DXM managed markers are not allowed")
            stack.append(label)
            continue
        if not stack:
            continue
        if stack[-1] == label:
            stack.pop()
            continue
        errors.append("DXM managed markers close out of order")
        if label in stack:
            stack.remove(label)
    return list(dict.fromkeys(errors))


def _marker_errors(content: str) -> list[str]:
    return validate_managed_markers(content)


def managed_block_span(content: str, start: str, end: str) -> tuple[int, int] | None:
    """Return the real non-code managed block span, including both markers."""

    if validate_marker_layout(content, start, end):
        return None
    marker_surface = markdown_noncode_surface(content)
    start_index = marker_surface.find(start)
    if start_index < 0:
        return None
    end_index = marker_surface.find(end, start_index)
    if end_index < 0:
        return None
    return start_index, end_index + len(end)


def _managed_block(content: str, start: str, end: str) -> str | None:
    span = managed_block_span(content, start, end)
    if span is None:
        return None
    return content[slice(*span)]


def _markdown_prose(content: str) -> str:
    """Remove fenced and inline code before checking prose placeholders."""
    return markdown_noncode_surface(content)


def _read_audit_text(path: Path) -> tuple[str | None, list[str]]:
    try:
        return path.read_text(encoding="utf-8"), []
    except UnicodeDecodeError:
        return None, [f"{path.name} is not valid UTF-8"]
    except OSError as exc:
        return None, [f"cannot read {path.name}: {exc.__class__.__name__}"]


def _required_marker_pair(filename: str) -> tuple[str, str]:
    if filename == "AGENTS.md":
        return DXM_BLOCK_START, DXM_BLOCK_END
    return DXM_DOC_BLOCK_START, DXM_DOC_BLOCK_END


def _audit_trellis(root: Path, texts: dict[str, str], partial: list[str], broken: list[str]) -> None:
    required_paths = (
        root / ".trellis" / "config.yaml",
        root / ".trellis" / "workflow.md",
        root / ".agents" / "skills" / "trellis-start" / "SKILL.md",
    )
    safe_contents: dict[Path, str] = {}
    trellis_root = root / ".trellis"
    if not os.path.lexists(trellis_root):
        partial.append("requested Trellis integration is missing: .trellis")
    else:
        trellis_root_error = _trusted_project_path_error(root, trellis_root, ".trellis directory")
        if trellis_root_error is not None:
            broken.append(trellis_root_error)
            return
        if not trellis_root.is_dir():
            broken.append(".trellis must be a directory")
            return
    for path in required_paths:
        relative_name = path.relative_to(root).as_posix()
        path_error = _trusted_project_path_error(root, path, relative_name)
        if path_error is not None:
            broken.append(path_error)
            continue
        if not path.is_file():
            if os.path.lexists(path):
                broken.append(f"{relative_name} must be a regular file")
                continue
            partial.append(f"requested Trellis integration is missing: {relative_name}")
            continue
        content, errors = _read_audit_text(path)
        broken.extend(f"{relative_name}: {error}" for error in errors)
        if content is None:
            continue
        safe_contents[path] = content
        marker_errors = _marker_errors(content)
        broken.extend(f"{path.relative_to(root).as_posix()}: {error}" for error in marker_errors)
        if path.name == "config.yaml":
            session_auto_commit = [
                match.group(1).strip().lower()
                for match in re.finditer(
                    r"(?m)^session_auto_commit[ \t]*:[ \t]*([^#\r\n]*)",
                    content,
                )
            ]
            if len(session_auto_commit) > 1:
                broken.append(".trellis/config.yaml must contain exactly one active session_auto_commit key")
            elif session_auto_commit != ["false"]:
                partial.append(".trellis/config.yaml must set exactly one session_auto_commit: false")

    required_trellis_markers = {
        "AGENTS.md": (TRELLIS_BLOCK_START, TRELLIS_BLOCK_END),
        "项目开发规范（AI协作）.md": (TRELLIS_BLOCK_START, TRELLIS_BLOCK_END),
        "项目完整链路说明.md": (TRELLIS_BLOCK_START, TRELLIS_BLOCK_END),
        "项目文件结构说明.md": (TRELLIS_BLOCK_START, TRELLIS_BLOCK_END),
    }
    for filename, (start, end) in required_trellis_markers.items():
        content = texts.get(filename)
        if content is not None:
            marker_surface = markdown_noncode_surface(content)
        else:
            marker_surface = None
        if marker_surface is not None and start not in marker_surface and end not in marker_surface:
            partial.append(f"{filename} is missing the requested Trellis managed block")

    workflow = root / ".trellis" / "workflow.md"
    workflow_content = safe_contents.get(workflow)
    if workflow_content is not None:
        workflow_surface = markdown_noncode_surface(workflow_content)
        if TRELLIS_WORKFLOW_OVERRIDE_START not in workflow_surface and TRELLIS_WORKFLOW_OVERRIDE_END not in workflow_surface:
            partial.append(".trellis/workflow.md is missing the DXM workflow override block")
    start_skill = root / ".agents" / "skills" / "trellis-start" / "SKILL.md"
    start_content = safe_contents.get(start_skill)
    if start_content is not None:
        start_surface = markdown_noncode_surface(start_content)
        if TRELLIS_START_STEP0_START not in start_surface and TRELLIS_START_STEP0_END not in start_surface:
            partial.append("trellis-start/SKILL.md is missing the DXM Step 0 block")


def audit_project(root: Path, require_trellis: bool = False) -> AuditResult:
    """Audit DXM readiness without creating or modifying project files."""

    canonical_root = _canonical_path(root)
    if os.path.lexists(canonical_root) and not canonical_root.is_dir():
        return AuditResult(canonical_root, BROKEN, ("project root must be a directory",))

    dxm_root = canonical_root / ".dxm"
    baseline_path = dxm_root / "project.json"
    has_artifact = os.path.lexists(dxm_root) or any(
        os.path.lexists(canonical_root / filename) for filename in REQUIRED_FILES
    )
    if not has_artifact:
        return AuditResult(canonical_root, ABSENT, ("DXM document set is absent",))

    partial: list[str] = []
    broken: list[str] = []
    if os.path.lexists(dxm_root):
        dxm_root_error = _trusted_project_path_error(canonical_root, dxm_root, ".dxm directory")
        if dxm_root_error is not None:
            broken.append(dxm_root_error)
        elif not dxm_root.is_dir():
            broken.append(".dxm must be a directory")
    texts: dict[str, str] = {}
    for filename in REQUIRED_FILES:
        path = canonical_root / filename
        path_error = _trusted_project_path_error(canonical_root, path, filename)
        if path_error is not None:
            broken.append(path_error)
            continue
        if not path.is_file():
            if os.path.lexists(path):
                broken.append(f"{filename} must be a regular file")
                continue
            partial.append(f"missing required file: {filename}")
            continue
        content, errors = _read_audit_text(path)
        broken.extend(f"{filename}: {error}" for error in errors)
        if content is None:
            continue
        texts[filename] = content
        marker_surface = markdown_noncode_surface(content)
        broken.extend(f"{filename}: {error}" for error in _marker_errors(content))
        start, end = _required_marker_pair(filename)
        broken.extend(f"{filename}: {error}" for error in validate_marker_layout(content, start, end))
        if start not in marker_surface and end not in marker_surface:
            partial.append(f"{filename} is missing its required DXM managed block")
        managed_block = _managed_block(content, start, end)
        contract_comments = [
            comment
            for comment in HTML_COMMENT_RE.findall(marker_surface)
            if re.search(r"DXM[-_]CONTRACT", comment, re.IGNORECASE)
        ]
        canonical_contract_markers = [
            comment for comment in contract_comments if CONTRACT_MARKER_RE.fullmatch(comment)
        ]
        if len(canonical_contract_markers) > 1:
            broken.append(f"{filename}: duplicate DXM contract markers")
        if len(canonical_contract_markers) != len(contract_comments):
            broken.append(f"{filename}: malformed DXM contract marker")
        if managed_block is not None:
            managed_surface = markdown_noncode_surface(managed_block)
            if CONTRACT_MARKER not in managed_surface:
                partial.append(f"{filename} managed block is missing the current DXM contract marker")
        if PLACEHOLDER_RE.search(_markdown_prose(content)):
            partial.append(f"{filename} contains an unresolved placeholder")

    baseline: dict[str, Any] | None = None
    if not baseline_path.is_file():
        if os.path.lexists(baseline_path):
            broken.append(".dxm/project.json must be a regular file")
        else:
            partial.append("missing project baseline: .dxm/project.json")
    else:
        try:
            baseline = load_baseline(
                baseline_path,
                expected_root=canonical_root,
                require_trusted_path=True,
            )
        except ContractError as exc:
            broken.extend(f".dxm/project.json: {error}" for error in exc.errors)

    chain = texts.get("项目完整链路说明.md")
    if chain is not None:
        chain_surface = markdown_noncode_surface(chain)
        broken.extend(
            f"项目完整链路说明.md: {error}"
            for error in validate_marker_layout(chain, BASELINE_BLOCK_START, BASELINE_BLOCK_END)
        )
        if baseline is not None:
            if BASELINE_BLOCK_START not in chain_surface and BASELINE_BLOCK_END not in chain_surface:
                partial.append("项目完整链路说明.md is missing the managed project baseline block")
            else:
                actual_block = _managed_block(chain, BASELINE_BLOCK_START, BASELINE_BLOCK_END)
                expected_block = baseline_markdown(baseline).strip("\n")
                if actual_block is not None and actual_block != expected_block:
                    broken.append("项目完整链路说明.md managed baseline does not match .dxm/project.json")

    if require_trellis:
        _audit_trellis(canonical_root, texts, partial, broken)

    if broken:
        return AuditResult(canonical_root, BROKEN, tuple(dict.fromkeys(broken + partial)))
    if partial:
        return AuditResult(canonical_root, PARTIAL, tuple(dict.fromkeys(partial)))
    return AuditResult(canonical_root, READY)


def _receipt_data(data_or_path: Mapping[str, Any] | Path | str) -> tuple[dict[str, Any] | None, list[str]]:
    if isinstance(data_or_path, Mapping):
        return dict(data_or_path), []
    return _load_json_object(Path(data_or_path), "receipt")


def _validate_receipt_project(
    root: Path,
    requirement_kinds: dict[str, tuple[int, list[str]]],
    *,
    require_trellis: bool,
) -> list[str]:
    errors: list[str] = []
    audit = audit_project(root, require_trellis=require_trellis)
    if audit.state != READY:
        subject = "project_root and required Trellis integration" if require_trellis else "project_root"
        errors.append(f"{subject} must be READY; audit reported {audit.state}")

    try:
        baseline = load_baseline(
            root / ".dxm" / "project.json",
            expected_root=root,
            require_trusted_path=True,
        )
    except ContractError:
        errors.append("project baseline must be valid and match project_root")
        return errors

    baseline_kinds = {
        item["id"]: set(item["evidence_kinds"])
        for item in baseline["acceptance_criteria"]
    }
    if set(requirement_kinds) != set(baseline_kinds):
        errors.append("receipt requirements must exactly cover project baseline acceptance IDs")
    for requirement_id, (index, kinds) in requirement_kinds.items():
        if requirement_id in baseline_kinds and set(kinds) != baseline_kinds[requirement_id]:
            errors.append(f"requirements[{index}].evidence_kinds must exactly match the project baseline")
    return errors


def _find_trellis_task(root: Path, task_name: str) -> tuple[Path | None, bool, list[str]]:
    tasks_root = root / ".trellis" / "tasks"
    tasks_root_error = _trusted_project_path_error(root, tasks_root, "Trellis tasks root")
    if tasks_root_error is not None:
        return None, False, [tasks_root_error]
    candidates: list[tuple[Path, bool]] = []
    active = tasks_root / task_name
    active_error = _trusted_project_path_error(root, active, "trellis.task directory")
    if active_error is not None:
        return None, False, [active_error]
    if active.is_dir():
        candidates.append((active, False))
    archive_root = tasks_root / "archive"
    archive_error = _trusted_project_path_error(root, archive_root, "Trellis archive root")
    if archive_error is not None:
        return None, False, [archive_error]
    if archive_root.is_dir():
        try:
            months = list(archive_root.iterdir())
        except OSError:
            return None, False, ["Trellis archive state is unreadable"]
        for month in months:
            month_error = _trusted_project_path_error(root, month, "Trellis archive directory")
            if month_error is not None:
                return None, False, [month_error]
            if not month.is_dir():
                continue
            archived = month / task_name
            archived_error = _trusted_project_path_error(root, archived, "trellis.task directory")
            if archived_error is not None:
                return None, False, [archived_error]
            if ARCHIVE_MONTH_RE.fullmatch(month.name) is None:
                if os.path.lexists(archived):
                    return None, False, ["Trellis archive directory for trellis.task must use YYYY-MM"]
                continue
            if archived.is_dir():
                candidates.append((archived, True))
    if not candidates:
        return None, False, ["trellis.task directory does not exist"]
    if len(candidates) != 1:
        return None, False, ["trellis.task directory is ambiguous across active/archive state"]
    task_dir, archived = candidates[0]
    task_error = _trusted_project_path_error(root, task_dir, "trellis.task directory")
    if task_error is not None:
        return None, False, [task_error]
    return task_dir, archived, []


def _task_ref_matches(task_ref: str, task_name: str) -> bool:
    normalized = task_ref.strip().replace("\\", "/").rstrip("/")
    if not normalized:
        return False
    parts = [part for part in normalized.split("/") if part]
    if not parts or parts[-1] != task_name:
        return False
    return "tasks" in parts or len(parts) == 1


def _validate_finished_trellis_state(root: Path, task_name: str) -> list[str]:
    sessions = root / ".trellis" / ".runtime" / "sessions"
    sessions_error = _trusted_project_path_error(root, sessions, "Trellis runtime sessions")
    if sessions_error is not None:
        return [sessions_error]
    if not sessions.is_dir():
        return []
    try:
        session_files = list(sessions.glob("*.json"))
    except OSError:
        return ["trellis.finished cannot be verified because runtime session state is unreadable"]
    for session_file in session_files:
        session_error = _trusted_project_path_error(root, session_file, "Trellis runtime session")
        if session_error is not None:
            return [session_error]
        session, load_errors = _load_json_object(session_file, "Trellis runtime session")
        if load_errors or session is None:
            return ["trellis.finished cannot be verified because runtime session state is invalid"]
        current_task = session.get("current_task")
        if isinstance(current_task, str) and _task_ref_matches(current_task, task_name):
            return ["trellis.finished is false because the task is still active in runtime session state"]
    return []


def _validate_trellis_receipt(root: Path, trellis: dict[str, Any]) -> list[str]:
    task_name = trellis.get("task")
    if not _is_nonempty_string(task_name):
        return []
    if task_name in (".", "..") or "/" in task_name or "\\" in task_name:
        return ["trellis.task must be one task directory name"]

    task_dir, archived, errors = _find_trellis_task(root, task_name)
    if task_dir is None:
        return errors

    task_status: Any = None
    task_metadata = task_dir / "task.json"
    task_metadata_error = _trusted_project_path_error(root, task_metadata, "Trellis task metadata")
    task_data: dict[str, Any] | None = None
    task_errors: list[str] = []
    if task_metadata_error is not None:
        errors.append(task_metadata_error)
    else:
        task_data, task_errors = _load_json_object(task_metadata, "Trellis task metadata")
    if task_metadata_error is None and (task_errors or task_data is None):
        errors.append("trellis.task task.json must be valid UTF-8 JSON")
    elif task_data is not None:
        task_id = task_data.get("id")
        if not _is_nonempty_string(task_id) or (task_name != task_id and not task_name.endswith(f"-{task_id}")):
            errors.append("trellis.task task.json id does not match its directory")
        task_status = task_data.get("status")
        if task_status not in STARTED_TRELLIS_STATUSES:
            errors.append("trellis.task task.json does not prove the task was started")
        if archived and task_status not in COMPLETED_TRELLIS_STATUSES:
            errors.append("archived trellis.task must have completed status")

    artifact_value = trellis.get("check_artifact", "check.md")
    if not _is_nonempty_string(artifact_value):
        errors.append("trellis.check_artifact must be a non-empty relative path")
    elif artifact_value != "check.md":
        errors.append("trellis.check_artifact must be the canonical check.md artifact")
    else:
        artifact_rel = Path(artifact_value)
        artifact = (task_dir / artifact_rel).resolve(strict=False)
        try:
            artifact.relative_to(task_dir.resolve(strict=True))
        except (OSError, ValueError):
            errors.append("trellis.check_artifact must stay inside the task directory")
        else:
            artifact_error = _trusted_project_path_error(root, artifact, "trellis.check artifact")
            if artifact_error is not None:
                errors.append(artifact_error)
            else:
                try:
                    check_content = artifact.read_text(encoding="utf-8")
                except (FileNotFoundError, OSError, UnicodeDecodeError):
                    errors.append("trellis.check artifact must exist as a valid UTF-8 file")
                else:
                    if not check_content.strip():
                        errors.append("trellis.check artifact must not be empty")
                    else:
                        errors.extend(_check_verdict_errors(check_content))

    if trellis.get("finished") is True:
        if not archived:
            errors.append("trellis.finished requires the task to be archived")
        if task_status not in COMPLETED_TRELLIS_STATUSES:
            errors.append("trellis.finished requires task.json status completed or done")
        errors.extend(_validate_finished_trellis_state(root, task_name))
    return errors


def _validate_trellis_receipt_path(root: Path, trellis: dict[str, Any], source: Path) -> list[str]:
    task_name = trellis.get("task")
    if not _is_nonempty_string(task_name):
        return []
    task_dir, archived, task_errors = _find_trellis_task(root, task_name)
    if task_dir is None or task_errors:
        return []
    expected = task_dir / "completion.json"
    source_error = _trusted_project_path_error(root, source, "completion receipt")
    if source_error is not None:
        return [source_error]
    if not archived or not _same_path(source, expected):
        return [
            "Trellis receipt file must be archive/<YYYY-MM>/<task>/completion.json"
        ]
    return []


def validate_receipt(
    data_or_path: Mapping[str, Any] | Path | str,
    expected_root: Path | None = None,
) -> list[str]:
    """Validate a receipt without trusting its project_root to authorize reads.

    Path/string inputs are also bound to the trusted project; required Trellis
    receipts must be the archived task's ``completion.json``. Mapping inputs
    validate schema and trusted persisted state but have no source-file claim.
    """

    receipt_source: Path | None = None
    if not isinstance(data_or_path, Mapping):
        receipt_source = _lexical_absolute_path(data_or_path)
        if expected_root is not None:
            source_error = _trusted_project_path_error(
                Path(expected_root),
                receipt_source,
                "completion receipt",
            )
            if source_error is not None:
                return [source_error]
            receipt_source = _canonical_path(receipt_source)
    data, load_errors = _receipt_data(data_or_path)
    if load_errors:
        return load_errors
    assert data is not None
    errors: list[str] = []
    errors.extend(_credential_errors(data, "receipt"))

    if type(data.get("schema_version")) is not int or data.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {RECEIPT_SCHEMA_VERSION}")
    if data.get("workflow_mode") not in RECEIPT_WORKFLOW_MODES:
        errors.append(f"workflow_mode must be one of: {', '.join(RECEIPT_WORKFLOW_MODES)}")
    project_root = data.get("project_root")
    canonical_root: Path | None = None
    if not _is_nonempty_string(project_root) or not Path(str(project_root)).is_absolute():
        errors.append("project_root must be a non-empty absolute path")
    if expected_root is None:
        errors.append("expected_root is required to verify completion against trusted project state")
    else:
        trusted_root = _canonical_path(expected_root)
        if _is_nonempty_string(project_root) and Path(project_root).is_absolute():
            if os.path.normcase(project_root) != os.path.normcase(str(trusted_root)):
                errors.append("project_root does not match expected_root or is not canonical")
            else:
                canonical_root = trusted_root

    requirements = data.get("requirements")
    requirement_kinds: dict[str, tuple[int, list[str]]] = {}
    if not isinstance(requirements, list) or not requirements:
        errors.append("requirements must be a non-empty list")
    else:
        seen_ids: set[str] = set()
        for index, requirement in enumerate(requirements):
            prefix = f"requirements[{index}]"
            if not isinstance(requirement, dict):
                errors.append(f"{prefix} must be an object")
                continue
            requirement_id = requirement.get("id")
            if not _is_nonempty_string(requirement_id):
                errors.append(f"{prefix}.id must be a non-empty string")
                continue
            if requirement_id in seen_ids:
                errors.append(f"duplicate requirement id at {prefix}.id")
                continue
            seen_ids.add(requirement_id)
            if requirement.get("status") != "passed":
                errors.append(f"{prefix}.status must be passed")
            kinds = requirement.get("evidence_kinds")
            kind_errors = _validate_string_list(kinds, f"{prefix}.evidence_kinds", allow_empty=False)
            errors.extend(kind_errors)
            if isinstance(kinds, list):
                normalized = [kind for kind in kinds if _is_nonempty_string(kind)]
                if len(normalized) != len(set(normalized)):
                    errors.append(f"{prefix}.evidence_kinds contains duplicates")
                requirement_kinds[requirement_id] = (index, normalized)

    evidence = data.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("evidence must be an object keyed by acceptance ID and evidence kind")
        evidence = {}
    for requirement_id, (requirement_index, kinds) in requirement_kinds.items():
        records = evidence.get(requirement_id)
        if not isinstance(records, dict):
            errors.append(f"evidence is missing an entry for requirements[{requirement_index}].id")
            continue
        for kind_index, kind in enumerate(kinds):
            references = records.get(kind)
            if not isinstance(references, list) or not references or any(
                not _is_nonempty_string(reference) for reference in references
            ):
                errors.append(
                    f"evidence for requirements[{requirement_index}] is missing "
                    f"evidence_kinds[{kind_index}]"
                )
    if isinstance(evidence, dict):
        for acceptance_id in evidence:
            if acceptance_id not in requirement_kinds:
                errors.append("evidence references an unknown acceptance ID")

    adversarial = data.get("adversarial_check")
    if not isinstance(adversarial, dict):
        errors.append("adversarial_check must be an object")
    else:
        if adversarial.get("passed") is not True:
            errors.append("adversarial_check.passed must be true")
        if not _is_nonempty_string(adversarial.get("summary")):
            errors.append("adversarial_check.summary must be a non-empty string")

    quality = data.get("quality_checks")
    if not isinstance(quality, dict):
        errors.append("quality_checks must be an object")
    else:
        for name in QUALITY_CHECKS:
            if quality.get(name) is not True:
                errors.append(f"quality_checks.{name} must be true")

    trellis = data.get("trellis")
    if not isinstance(trellis, dict) or not isinstance(trellis.get("required"), bool):
        errors.append("trellis.required must be a boolean")
    elif trellis["required"]:
        if not _is_nonempty_string(trellis.get("task")):
            errors.append("trellis.task must name the required task")
        if trellis.get("check_passed") is not True:
            errors.append("trellis.check_passed must be true when Trellis is required")
        if trellis.get("finished") is not True:
            errors.append("trellis.finished must be true when Trellis is required")
    elif trellis.get("finished") is True or trellis.get("check_passed") is True:
        errors.append("trellis cannot claim check/finish completion when required is false")

    git = data.get("git")
    if not isinstance(git, dict):
        errors.append("git must be an object")
    else:
        commit_performed = git.get("commit_performed")
        push_performed = git.get("push_performed")
        if not isinstance(commit_performed, bool):
            errors.append("git.commit_performed must be a boolean")
        elif commit_performed and not _is_nonempty_string(git.get("commit")):
            errors.append("git.commit must be present when commit_performed is true")
        elif not commit_performed and git.get("commit") is not None:
            errors.append("git.commit must be null when commit_performed is false")
        if not isinstance(push_performed, bool):
            errors.append("git.push_performed must be a boolean")
        elif push_performed and not _is_nonempty_string(git.get("branch")):
            errors.append("git.branch must be present when push_performed is true")
        elif not push_performed and git.get("branch") is not None:
            errors.append("git.branch must be null when push_performed is false")
    if canonical_root is not None:
        require_trellis = isinstance(trellis, dict) and trellis.get("required") is True
        errors.extend(
            _validate_receipt_project(
                canonical_root,
                requirement_kinds,
                require_trellis=require_trellis,
            )
        )
        if require_trellis:
            errors.extend(_validate_trellis_receipt(canonical_root, trellis))
            if receipt_source is not None:
                errors.extend(_validate_trellis_receipt_path(canonical_root, trellis, receipt_source))
    return errors


def release_version() -> str:
    """Return the repository release version when packaged alongside the repo."""

    script_path = Path(__file__).resolve()
    candidates = [script_path.parents[1] / "VERSION", script_path.parents[3] / "VERSION"]
    for candidate in candidates:
        try:
            version = candidate.read_text(encoding="utf-8").strip()
        except (FileNotFoundError, OSError, UnicodeDecodeError):
            continue
        if version:
            return version
    return f"contract-{CONTRACT_VERSION}"


def version_text() -> str:
    return (
        f"dxm-validator {release_version()} "
        f"contract={CONTRACT_VERSION} "
        f"baseline-schema={BASELINE_SCHEMA_VERSION} receipt-schema={RECEIPT_SCHEMA_VERSION}"
    )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recoverable local write primitives for DXM-managed project files."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import shutil
import socket
import stat
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from dxm_policy import LIMITS


ERROR_WRITE_FAILED = "DXM_E_WRITE_FAILED"
ERROR_DISK_FULL = "DXM_E_DISK_FULL"
ERROR_PERMISSION_DENIED = "DXM_E_PERMISSION_DENIED"
ERROR_CONCURRENT_OPERATION = "DXM_E_CONCURRENT_OPERATION"
ERROR_RECOVERY_REQUIRED = "DXM_E_RECOVERY_REQUIRED"

TRANSACTION_STATES = frozenset({"prepared", "applying", "committed", "recovery_required"})
TRANSACTION_MODES = frozenset({"init", "scaffold-only"})
OPERATION_ID_RE = re.compile(r"^[0-9a-f]{32}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class DxmIoError(RuntimeError):
    """A stable DXM write/recovery error that does not expose raw system detail."""

    def __init__(self, code: str, summary: str, *, cause: BaseException | None = None) -> None:
        self.code = code
        self.summary = summary
        self.cause = cause
        super().__init__(f"{code}: {summary}")


def normalize_lf(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def _error_code(exc: OSError) -> str:
    if exc.errno == errno.ENOSPC:
        return ERROR_DISK_FULL
    if exc.errno in {errno.EACCES, errno.EPERM, errno.EROFS}:
        return ERROR_PERMISSION_DENIED
    return ERROR_WRITE_FAILED


def _raise_io(summary: str, exc: OSError) -> None:
    raise DxmIoError(_error_code(exc), summary, cause=exc) from exc


def _fsync_directory(directory: Path) -> None:
    """Best-effort metadata flush; Windows does not permit opening directories."""

    if os.name == "nt":
        return
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def atomic_replace_bytes(path: Path, content: bytes) -> None:
    """Durably replace one file using a temporary sibling on the same filesystem."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.dxm-", suffix=".tmp", dir=path.parent)
    except OSError as exc:
        _raise_io("could not prepare a managed write", exc)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except OSError as exc:
        _raise_io("could not atomically replace a managed file", exc)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def atomic_replace_text(path: Path, content: str) -> None:
    atomic_replace_bytes(path, normalize_lf(content).encode("utf-8"))


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_path(path: Path) -> str | None:
    try:
        return _sha256_bytes(path.read_bytes())
    except (OSError, FileNotFoundError):
        return None


def _canonical_root(root: Path) -> Path:
    return root.resolve(strict=False)


def _is_reparse_or_symlink(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except OSError as exc:
        _raise_io("could not inspect DXM local state", exc)
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse_flag)


def _validate_local_state_topology(root: Path) -> None:
    """Reject links and non-directories before recovery touches local state."""

    canonical_root = _canonical_root(root)
    for relative, label in (
        (".dxm", ".dxm"),
        (".dxm/locks", ".dxm/locks"),
        (".dxm/transactions", ".dxm/transactions"),
    ):
        path = canonical_root.joinpath(*relative.split("/"))
        if not os.path.lexists(path):
            continue
        if _is_reparse_or_symlink(path):
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, f"{label} must not be a link or reparse point")
        try:
            info = os.lstat(path)
        except OSError as exc:
            _raise_io("could not inspect DXM local state", exc)
        if not stat.S_ISDIR(info.st_mode):
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, f"{label} must be a directory")


def _validate_regular_state_file(path: Path, label: str) -> None:
    if not os.path.lexists(path):
        return
    if _is_reparse_or_symlink(path):
        raise DxmIoError(ERROR_RECOVERY_REQUIRED, f"{label} must not be a link or reparse point")
    try:
        info = os.lstat(path)
    except OSError as exc:
        _raise_io("could not inspect DXM local state", exc)
    if not stat.S_ISREG(info.st_mode):
        raise DxmIoError(ERROR_RECOVERY_REQUIRED, f"{label} must be a regular file")


def _valid_operation_id(value: Any) -> bool:
    return isinstance(value, str) and OPERATION_ID_RE.fullmatch(value) is not None


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _journal_relative_target(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise DxmIoError(ERROR_RECOVERY_REQUIRED, f"a DXM transaction journal has an invalid {label}")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        "\\" in value
        or "\x00" in value
        or posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or posix.as_posix() != value
        or any(part in {"", ".", ".."} for part in posix.parts)
    ):
        raise DxmIoError(ERROR_RECOVERY_REQUIRED, f"a DXM transaction journal has an invalid {label}")
    target = _canonical_root(root).joinpath(*posix.parts)
    try:
        actual_relative = target.resolve(strict=False).relative_to(_canonical_root(root)).as_posix()
    except (OSError, ValueError) as exc:
        raise DxmIoError(
            ERROR_RECOVERY_REQUIRED,
            "a DXM transaction journal escaped its project root",
            cause=exc,
        ) from exc
    if actual_relative != value:
        raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal escaped its project root")
    return target


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(_canonical_root(root)).as_posix()
    except ValueError as exc:
        raise DxmIoError(ERROR_WRITE_FAILED, "managed path escaped the locked project root", cause=exc) from exc


def _safe_remove(path: Path) -> None:
    try:
        if not os.path.lexists(path):
            return
        if _is_reparse_or_symlink(path):
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction cleanup target is unsafe")
        info = os.lstat(path)
        if stat.S_ISDIR(info.st_mode):
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
    except OSError as exc:
        _raise_io("could not clean up a completed DXM transaction", exc)


def _windows_pid_is_alive(pid: int) -> bool | None:
    """Query process state without using ``os.kill(pid, 0)`` on Windows."""

    import ctypes
    from ctypes import wintypes

    synchronize = 0x00100000
    wait_object_0 = 0x00000000
    wait_timeout = 0x00000102
    error_access_denied = 5
    error_invalid_parameter = 87

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(synchronize, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        if error == error_invalid_parameter:
            return False
        if error == error_access_denied:
            return True
        return None
    try:
        wait_result = kernel32.WaitForSingleObject(handle, 0)
        if wait_result == wait_timeout:
            return True
        if wait_result == wait_object_0:
            return False
        return None
    finally:
        kernel32.CloseHandle(handle)


class ProjectLock:
    """Exclusive root-local lock for DXM write and recovery operations."""

    def __init__(self, root: Path, mode: str) -> None:
        self.root = _canonical_root(root)
        self.mode = mode
        self.path = self.root / ".dxm" / "locks" / "project.lock"
        self.operation_id = uuid.uuid4().hex
        self._held = False

    @staticmethod
    def _read(path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _pid_is_alive(pid: Any) -> bool | None:
        if type(pid) is not int or pid < 1:
            return None
        if os.name == "nt":
            return _windows_pid_is_alive(pid)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return None
        return True

    @classmethod
    def is_stale(cls, state: dict[str, Any] | None) -> bool:
        if state is None:
            return True
        started = state.get("started_epoch")
        if type(started) not in (int, float):
            return True
        if time.time() - float(started) > LIMITS["lock_stale_seconds"]:
            return True
        if state.get("hostname") == socket.gethostname():
            alive = cls._pid_is_alive(state.get("pid"))
            return alive is False
        return False

    @staticmethod
    def _is_valid_state(state: dict[str, Any] | None) -> bool:
        return bool(
            isinstance(state, dict)
            and _valid_operation_id(state.get("operation_id"))
            and state.get("mode") in {*TRANSACTION_MODES, "recover"}
            and type(state.get("pid")) is int
            and state["pid"] > 0
            and isinstance(state.get("hostname"), str)
            and bool(state["hostname"])
            and type(state.get("started_epoch")) in (int, float)
        )

    def acquire(self) -> None:
        _validate_local_state_topology(self.root)
        _validate_regular_state_file(self.path, ".dxm/locks/project.lock")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            state = self._read(self.path)
            if self.is_stale(state):
                raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a stale DXM project lock requires explicit recovery", cause=exc) from exc
            raise DxmIoError(ERROR_CONCURRENT_OPERATION, "another DXM write operation holds the project lock", cause=exc) from exc
        except OSError as exc:
            _raise_io("could not acquire the DXM project lock", exc)
        state = {
            "operation_id": self.operation_id,
            "mode": self.mode,
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "started_epoch": time.time(),
        }
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(state, handle, ensure_ascii=True, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._held = True
        except OSError as exc:
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                pass
            _raise_io("could not persist the DXM project lock", exc)

    def release(self) -> None:
        if not self._held:
            return
        _validate_local_state_topology(self.root)
        _validate_regular_state_file(self.path, ".dxm/locks/project.lock")
        state = self._read(self.path)
        if not self._is_valid_state(state) or state.get("operation_id") != self.operation_id:
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "the DXM project lock changed ownership during the operation")
        try:
            self.path.unlink(missing_ok=True)
            _fsync_directory(self.path.parent)
        except OSError as exc:
            _raise_io("could not release the DXM project lock", exc)
        self._held = False

    def __enter__(self) -> "ProjectLock":
        self.acquire()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()


@dataclass
class ProjectTransaction:
    """Records enough state to recover an interrupted multi-file DXM write."""

    root: Path
    mode: str
    operation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entries: list[dict[str, Any]] = field(default_factory=list)
    state: str = "prepared"

    def __post_init__(self) -> None:
        self.root = _canonical_root(self.root)
        if not _valid_operation_id(self.operation_id):
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction has an invalid operation identifier")
        if self.mode not in TRANSACTION_MODES:
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction has an invalid mode")
        if self.state not in TRANSACTION_STATES:
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction has an invalid state")
        self.transactions_root = self.root / ".dxm" / "transactions"
        self.journal_path = self.transactions_root / f"{self.operation_id}.json"
        self.backup_dir = self.transactions_root / self.operation_id / "backups"
        self._started = False

    def _journal_data(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "operation_id": self.operation_id,
            "root": str(self.root),
            "mode": self.mode,
            "state": self.state,
            "entries": self.entries,
        }

    def _save_journal(self) -> None:
        atomic_replace_text(self.journal_path, json.dumps(self._journal_data(), ensure_ascii=False, indent=2) + "\n")

    def start(self) -> None:
        if self._started:
            return
        _validate_local_state_topology(self.root)
        try:
            self.transactions_root.mkdir(parents=True, exist_ok=True)
            _validate_local_state_topology(self.root)
            if os.path.lexists(self.backup_dir.parent):
                raise FileExistsError(self.backup_dir.parent)
            self.backup_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a duplicate DXM transaction identifier was detected", cause=exc) from exc
        except OSError as exc:
            _raise_io("could not prepare the DXM transaction journal", exc)
        self._save_journal()
        self._started = True

    def write_text(self, path: Path, content: str) -> bool:
        return self.write_bytes(path, normalize_lf(content).encode("utf-8"))

    def write_bytes(self, path: Path, content: bytes) -> bool:
        if not self._started:
            self.start()
        relative = _relative_path(self.root, path)
        try:
            previous = path.read_bytes() if path.exists() else None
        except OSError as exc:
            _raise_io("could not read a managed file before replacement", exc)
        if previous == content:
            return False
        index = len(self.entries)
        backup_relative: str | None = None
        if previous is not None:
            backup = self.backup_dir / f"{index:04d}.bak"
            atomic_replace_bytes(backup, previous)
            backup_relative = backup.relative_to(self.root).as_posix()
        entry = {
            "path": relative,
            "existed": previous is not None,
            "old_sha256": _sha256_bytes(previous) if previous is not None else None,
            "new_sha256": _sha256_bytes(content),
            "backup": backup_relative,
            "applied": False,
        }
        self.entries.append(entry)
        self.state = "applying"
        self._save_journal()
        try:
            atomic_replace_bytes(path, content)
        except DxmIoError as exc:
            self.state = "recovery_required"
            try:
                self._save_journal()
            except DxmIoError:
                pass
            raise exc
        entry["applied"] = True
        self._save_journal()
        return True

    def _restore_entry(self, entry: dict[str, Any]) -> None:
        relative = entry.get("path")
        target = _journal_relative_target(self.root, relative, "path")
        expected = entry.get("new_sha256")
        actual = _sha256_path(target)
        if actual != expected:
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a managed file changed after an interrupted DXM transaction")
        if entry.get("existed") is True:
            backup_value = entry.get("backup")
            if not isinstance(backup_value, str) or not backup_value:
                raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal is missing a backup")
            backup = _journal_relative_target(self.root, backup_value, "backup path")
            try:
                old_content = backup.read_bytes()
            except OSError as exc:
                _raise_io("could not read a DXM transaction backup", exc)
            if _sha256_bytes(old_content) != entry.get("old_sha256"):
                raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction backup does not match its journal")
            atomic_replace_bytes(target, old_content)
            return
        try:
            target.unlink()
            _fsync_directory(target.parent)
        except OSError as exc:
            _raise_io("could not remove a newly created managed file during recovery", exc)

    def _entry_requires_restore(self, entry: dict[str, Any]) -> bool:
        """Detect the crash window between replace and journal acknowledgement."""

        relative = entry.get("path")
        expected_new = entry.get("new_sha256")
        if not isinstance(relative, str) or not _is_sha256(expected_new):
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal is malformed")
        target = _journal_relative_target(self.root, relative, "path")
        actual = _sha256_path(target)
        if actual == expected_new:
            return True
        if entry.get("existed") is True and actual == entry.get("old_sha256"):
            return False
        if entry.get("existed") is False and actual is None:
            return False
        raise DxmIoError(
            ERROR_RECOVERY_REQUIRED,
            "a managed file changed during an interrupted DXM transaction",
        )

    def rollback(self, *, strict_cleanup: bool = False) -> None:
        if not self._started:
            return
        try:
            for entry in reversed(self.entries):
                if entry.get("applied") is True or self._entry_requires_restore(entry):
                    self._restore_entry(entry)
        except DxmIoError:
            self.state = "recovery_required"
            try:
                self._save_journal()
            except DxmIoError:
                pass
            raise
        self.state = "committed"
        self._save_journal()
        self.cleanup(strict=strict_cleanup)

    def commit(self) -> None:
        if not self._started:
            return
        self.state = "committed"
        self._save_journal()
        self.cleanup()

    def cleanup(self, *, strict: bool = False) -> None:
        try:
            _validate_local_state_topology(self.root)
            expected_journal = self.transactions_root / f"{self.operation_id}.json"
            expected_operation_dir = self.transactions_root / self.operation_id
            if self.journal_path != expected_journal or self.backup_dir.parent != expected_operation_dir:
                raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction cleanup target is invalid")
            if os.path.lexists(expected_operation_dir):
                _safe_remove(self.backup_dir.parent)
            try:
                self.journal_path.unlink(missing_ok=True)
            except OSError as exc:
                _raise_io("could not clean up a completed DXM transaction", exc)
        except DxmIoError:
            # A committed leftover is safe; doctor can ask the user to clean it later.
            if strict:
                raise


def _load_journal(path: Path, root: Path) -> ProjectTransaction:
    root = _canonical_root(root)
    _validate_local_state_topology(root)
    transactions_root = root / ".dxm" / "transactions"
    if path.parent != transactions_root or path.suffix != ".json":
        raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal is outside the transactions directory")
    _validate_regular_state_file(path, "DXM transaction journal")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal is unreadable", cause=exc) from exc
    allowed_fields = {"schema_version", "operation_id", "root", "mode", "state", "entries"}
    if not isinstance(data, dict) or set(data) != allowed_fields or data.get("schema_version") != 1:
        raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal has an unsupported schema")
    if data.get("root") != str(root):
        raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal targets a different project root")
    operation_id = data.get("operation_id")
    mode = data.get("mode")
    entries = data.get("entries")
    state = data.get("state")
    if (
        not _valid_operation_id(operation_id)
        or mode not in TRANSACTION_MODES
        or not isinstance(entries, list)
        or state not in TRANSACTION_STATES
        or path.name != f"{operation_id}.json"
    ):
        raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal is malformed")
    if state == "prepared" and entries:
        raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a prepared DXM transaction journal must not contain entries")

    seen_paths: set[str] = set()
    required_entry_fields = {"path", "existed", "old_sha256", "new_sha256", "backup", "applied"}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != required_entry_fields:
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal entry is malformed")
        relative = entry.get("path")
        _journal_relative_target(root, relative, "path")
        if relative in seen_paths:
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal has duplicate managed paths")
        seen_paths.add(relative)
        if type(entry.get("existed")) is not bool or type(entry.get("applied")) is not bool:
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal entry is malformed")
        if not _is_sha256(entry.get("new_sha256")):
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal entry is malformed")
        if entry["existed"]:
            if not _is_sha256(entry.get("old_sha256")):
                raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal entry is malformed")
            expected_backup = transactions_root / str(operation_id) / "backups" / f"{index:04d}.bak"
            expected_relative = _relative_path(root, expected_backup)
            if entry.get("backup") != expected_relative:
                raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal has an invalid backup path")
        elif entry.get("old_sha256") is not None or entry.get("backup") is not None:
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "a DXM transaction journal entry is malformed")
    transaction = ProjectTransaction(root, mode, operation_id=operation_id, entries=entries, state=state)
    transaction.journal_path = path
    transaction._started = True
    return transaction


@dataclass(frozen=True)
class RecoveryInspection:
    lock_state: str
    pending_transactions: tuple[str, ...]
    committed_transactions: int
    issues: tuple[str, ...]
    broken: bool = False

    @property
    def recovery_required(self) -> bool:
        return bool(
            self.broken
            or self.pending_transactions
            or self.committed_transactions
            or self.lock_state in {"stale", "malformed"}
        )

    @property
    def write_blocked(self) -> bool:
        return self.recovery_required or self.lock_state == "active"


def _journal_paths(transactions_root: Path) -> list[Path]:
    try:
        return sorted(transactions_root.glob("*.json"))
    except OSError as exc:
        _raise_io("could not enumerate DXM transaction journals", exc)


def inspect_recovery_state(root: Path) -> RecoveryInspection:
    """Inspect local lock/journal state without changing the project."""

    root = _canonical_root(root)
    try:
        _validate_local_state_topology(root)
    except DxmIoError as exc:
        return RecoveryInspection("unsafe", (), 0, (exc.summary,), broken=True)

    lock = ProjectLock(root, "recover")
    lock_state = "absent"
    issues: list[str] = []
    broken = False
    if os.path.lexists(lock.path):
        try:
            _validate_regular_state_file(lock.path, ".dxm/locks/project.lock")
        except DxmIoError as exc:
            lock_state = "malformed"
            issues.append(exc.summary)
            broken = True
        else:
            state = lock._read(lock.path)
            if not lock._is_valid_state(state):
                lock_state = "malformed"
                issues.append("the DXM project lock is malformed")
                broken = True
            elif lock.is_stale(state):
                lock_state = "stale"
                issues.append("a stale DXM project lock requires explicit recovery")
            else:
                lock_state = "active"
                issues.append("a DXM write operation currently holds the project lock")

    pending: list[str] = []
    committed = 0
    transactions_root = root / ".dxm" / "transactions"
    if transactions_root.is_dir():
        try:
            journals = _journal_paths(transactions_root)
        except DxmIoError as exc:
            issues.append(exc.summary)
            broken = True
            journals = []
        for journal in journals:
            try:
                transaction = _load_journal(journal, root)
            except DxmIoError:
                pending.append("malformed")
                issues.append("a DXM transaction journal is malformed or unsafe")
                broken = True
                continue
            if transaction.state == "committed":
                committed += 1
            else:
                pending.append(transaction.state)
    if pending and not broken:
        issues.append("an interrupted DXM transaction requires explicit recovery")
    if committed:
        issues.append("a completed DXM transaction cleanup is pending")
    return RecoveryInspection(lock_state, tuple(pending), committed, tuple(dict.fromkeys(issues)), broken=broken)


def pending_transaction_states(root: Path) -> list[str]:
    inspection = inspect_recovery_state(root)
    if inspection.pending_transactions:
        return list(inspection.pending_transactions)
    if inspection.committed_transactions:
        return ["committed"]
    return ["malformed"] if inspection.broken else []


def recover_transactions(root: Path, *, break_stale_lock: bool = False) -> int:
    """Recover all interrupted transactions under an explicit caller command."""

    root = _canonical_root(root)
    _validate_local_state_topology(root)
    state_root = root / ".dxm"
    if not os.path.lexists(state_root):
        return 0
    lock = ProjectLock(root, "recover")
    _validate_regular_state_file(lock.path, ".dxm/locks/project.lock")
    transactions_root = root / ".dxm" / "transactions"
    if not transactions_root.is_dir() and not os.path.lexists(lock.path):
        return 0
    if os.path.lexists(lock.path):
        state = lock._read(lock.path)
        if not break_stale_lock or not lock.is_stale(state):
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "recovery requires an unlocked project or an explicit stale-lock break")
        try:
            lock.path.unlink()
        except OSError as exc:
            _raise_io("could not clear a stale DXM project lock", exc)
    with lock:
        _validate_local_state_topology(root)
        if not transactions_root.is_dir():
            return 0
        journals = _journal_paths(transactions_root)
        for journal in journals:
            transaction = _load_journal(journal, root)
            if transaction.state == "committed":
                transaction.cleanup(strict=True)
                continue
            transaction.rollback(strict_cleanup=True)
    return len(journals)

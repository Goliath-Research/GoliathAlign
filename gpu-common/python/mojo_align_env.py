"""GOLIATH_ALIGN_* env contract.

``MOJO_ALIGN_*`` and ``METHYLGRAPHER_MOJO_*`` remain one-cycle fallbacks.
"""

from __future__ import annotations

import os
import sys

INSTALL_PREFIX = "/opt/goliath-align"
_MID_PREFIX = "/opt/mojo-align"
_LEGACY_PREFIX = "/opt/methylgrapher-mojo"
_CANON = "GOLIATH_ALIGN_"
_MID = "MOJO_ALIGN_"
_OLD = "METHYLGRAPHER_MOJO_"
_warned: set[str] = set()


def _warn_once(key: str, msg: str) -> None:
    if key in _warned:
        return
    _warned.add(key)
    print(msg, file=sys.stderr)


def getenv(suffix: str, default: str = "") -> str:
    """Read ``GOLIATH_ALIGN_<suffix>``, then ``MOJO_ALIGN_``, then ``METHYLGRAPHER_MOJO_``."""
    canon_key = _CANON + suffix
    value = os.environ.get(canon_key, "").strip()
    if value:
        return value
    mid_key = _MID + suffix
    mid = os.environ.get(mid_key, "").strip()
    if mid:
        _warn_once(mid_key, f"warning: {mid_key} is deprecated; use {canon_key}")
        return mid
    old_key = _OLD + suffix
    legacy = os.environ.get(old_key, "").strip()
    if legacy:
        _warn_once(old_key, f"warning: {old_key} is deprecated; use {canon_key}")
        return legacy
    return default


def install_prefix() -> str:
    """In-container install root (``/opt/goliath-align``)."""
    if os.path.isdir(INSTALL_PREFIX):
        return INSTALL_PREFIX
    if os.path.isdir(_MID_PREFIX):
        _warn_once(
            _MID_PREFIX,
            f"warning: {_MID_PREFIX} is deprecated; use {INSTALL_PREFIX}",
        )
        return _MID_PREFIX
    if os.path.isdir(_LEGACY_PREFIX):
        _warn_once(
            _LEGACY_PREFIX,
            f"warning: {_LEGACY_PREFIX} is deprecated; use {INSTALL_PREFIX}",
        )
        return _LEGACY_PREFIX
    return INSTALL_PREFIX


def python_search_paths() -> list[str]:
    cwd = os.getcwd()
    root = getenv("ROOT")
    prefix = install_prefix()
    out: list[str] = []
    for path in (
        cwd,
        os.path.join(cwd, "methylgrapher"),
        os.path.join(cwd, "giraffe", "python"),
        os.path.join(cwd, "fq2bam-meth", "python"),
        os.path.join(cwd, "gpu-common", "python"),
        root,
        os.path.join(root, "methylgrapher") if root else "",
        os.path.join(root, "giraffe", "python") if root else "",
        os.path.join(root, "fq2bam-meth", "python") if root else "",
        os.path.join(root, "gpu-common", "python") if root else "",
        prefix,
        os.path.join(prefix, "methylgrapher"),
        os.path.join(prefix, "giraffe", "python"),
        os.path.join(prefix, "fq2bam-meth", "python"),
        os.path.join(prefix, "gpu-common", "python"),
        os.path.join(prefix, "scripts"),
    ):
        if path and path not in out:
            out.append(path)
    return out


def ensure_sys_path() -> None:
    """Prepend cwd / ``GOLIATH_ALIGN_ROOT`` / ``/opt/goliath-align`` onto ``sys.path``."""
    for path in reversed(python_search_paths()):
        if path not in sys.path:
            sys.path.insert(0, path)

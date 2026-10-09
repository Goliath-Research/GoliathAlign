"""Shim — replaces ``engine.min_mmap_bridge`` with ``giraffe/python/min_mmap_bridge.py`` in sys.modules."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ._pkg_shim import load_sibling as _load_sibling

if TYPE_CHECKING:
    # Runtime replaces this module in sys.modules. Give the checker the same exports.
    from min_mmap_bridge import *  # noqa: F403
else:
    _impl = _load_sibling('min_mmap_bridge', 'giraffe/python/min_mmap_bridge.py')
    # Identity swap so monkeypatch / ``is`` checks hit the real implementation.
    sys.modules[__name__] = _impl

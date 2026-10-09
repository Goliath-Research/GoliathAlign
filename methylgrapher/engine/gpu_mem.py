"""Shim — replaces ``engine.gpu_mem`` with ``gpu-common/python/gpu_mem.py`` in sys.modules."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ._pkg_shim import load_sibling as _load_sibling

if TYPE_CHECKING:
    # Runtime replaces this module in sys.modules. Give the checker the same exports.
    from gpu_mem import *  # noqa: F403
else:
    _impl = _load_sibling('gpu_mem', 'gpu-common/python/gpu_mem.py')
    # Identity swap so monkeypatch / ``is`` checks hit the real implementation.
    sys.modules[__name__] = _impl

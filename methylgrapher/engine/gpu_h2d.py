"""Shim — replaces ``engine.gpu_h2d`` with ``giraffe/python/gpu_h2d.py`` in sys.modules."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ._pkg_shim import load_sibling as _load_sibling

if TYPE_CHECKING:
    # Runtime replaces this module in sys.modules. Give the checker the same exports.
    from gpu_h2d import *  # noqa: F403
else:
    _impl = _load_sibling('gpu_h2d', 'giraffe/python/gpu_h2d.py')
    # Identity swap so monkeypatch / ``is`` checks hit the real implementation.
    sys.modules[__name__] = _impl

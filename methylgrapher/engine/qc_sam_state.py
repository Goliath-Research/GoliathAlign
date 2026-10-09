"""Shim — replaces ``engine.qc_sam_state`` with ``giraffe/python/qc_sam_state.py`` in sys.modules."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ._pkg_shim import load_sibling as _load_sibling

if TYPE_CHECKING:
    # Runtime replaces this module in sys.modules. Give the checker the same exports.
    from qc_sam_state import *  # noqa: F403
else:
    _impl = _load_sibling('qc_sam_state', 'giraffe/python/qc_sam_state.py')
    # Identity swap so monkeypatch / ``is`` checks hit the real implementation.
    sys.modules[__name__] = _impl

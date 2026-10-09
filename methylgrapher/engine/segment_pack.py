"""Shim — replaces ``engine.segment_pack`` with ``giraffe/python/segment_pack.py`` in sys.modules."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ._pkg_shim import load_sibling as _load_sibling

if TYPE_CHECKING:
    # Runtime replaces this module in sys.modules. Give the checker the same exports.
    from segment_pack import *  # noqa: F403
else:
    _impl = _load_sibling('segment_pack', 'giraffe/python/segment_pack.py')
    # Identity swap so monkeypatch / ``is`` checks hit the real implementation.
    sys.modules[__name__] = _impl

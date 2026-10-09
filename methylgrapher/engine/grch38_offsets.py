"""Shim — replaces ``engine.grch38_offsets`` with ``giraffe/python/grch38_offsets.py`` in sys.modules."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ._pkg_shim import load_sibling as _load_sibling

if TYPE_CHECKING:
    # Runtime replaces this module in sys.modules. Give the checker the same exports.
    from grch38_offsets import *  # noqa: F403
else:
    _impl = _load_sibling('grch38_offsets', 'giraffe/python/grch38_offsets.py')
    # Identity swap so monkeypatch / ``is`` checks hit the real implementation.
    sys.modules[__name__] = _impl

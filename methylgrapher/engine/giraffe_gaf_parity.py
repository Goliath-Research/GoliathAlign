"""Shim — replaces ``engine.giraffe_gaf_parity`` with ``giraffe/python/giraffe_gaf_parity.py`` in sys.modules."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ._pkg_shim import load_sibling as _load_sibling

if TYPE_CHECKING:
    # Runtime replaces this module in sys.modules. Give the checker the same exports.
    from giraffe_gaf_parity import *  # noqa: F403
else:
    _impl = _load_sibling('giraffe_gaf_parity', 'giraffe/python/giraffe_gaf_parity.py')
    # Identity swap so monkeypatch / ``is`` checks hit the real implementation.
    sys.modules[__name__] = _impl

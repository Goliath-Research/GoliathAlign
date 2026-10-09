"""Shim — replaces ``engine.quartet_map`` with ``giraffe/python/quartet_map.py`` in sys.modules."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ._pkg_shim import load_sibling as _load_sibling

if TYPE_CHECKING:
    # Runtime replaces this module in sys.modules. Give the checker the same exports.
    # Star-import skips leading underscores; callers also use these helpers.
    from quartet_map import *  # noqa: F403
    from quartet_map import (
        _iter_fastq,
        _iter_fastq_batches,
        _parse_mg_fastq_header,
        _pe_extra_tags,
        _read_batch_size,
    )
else:
    _impl = _load_sibling('quartet_map', 'giraffe/python/quartet_map.py')
    # Identity swap so monkeypatch / ``is`` checks hit the real implementation.
    sys.modules[__name__] = _impl

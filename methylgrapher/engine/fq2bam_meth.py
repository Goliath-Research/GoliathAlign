"""Shim — replaces ``engine.fq2bam_meth`` with ``fq2bam-meth/python/fq2bam_meth.py`` in sys.modules."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ._pkg_shim import load_sibling as _load_sibling

if TYPE_CHECKING:
    # Runtime replaces this module in sys.modules. Give the checker the same exports.
    # Star-import skips leading underscores; callers also use these helpers.
    from fq2bam_meth import *  # noqa: F403
    from fq2bam_meth import _parse_flagstat, _parse_samtools_stats
else:
    _impl = _load_sibling('fq2bam_meth', 'fq2bam-meth/python/fq2bam_meth.py')
    # Identity swap so monkeypatch / ``is`` checks hit the real implementation.
    sys.modules[__name__] = _impl

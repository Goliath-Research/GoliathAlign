"""dense-v1 pack: bounded-memory builder must match the legacy in-memory build byte-for-byte."""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import pytest

from mojo_linear_pack import build_dense_pack, encode_kmers_contig, read_fasta_contigs


def _legacy_bins(fasta: Path, k: int) -> dict:
    """Original (pre-streaming) algorithm: global concat + stable sort."""
    contigs = read_fasta_contigs(fasta)
    km_parts, loc_parts = [], []
    for cid, (_, seq) in enumerate(contigs):
        km, loc = encode_kmers_contig(seq, k, cid)
        if km.size:
            km_parts.append(km)
            loc_parts.append(loc)
    kmers = np.concatenate(km_parts)
    locs = np.concatenate(loc_parts)
    order = np.argsort(kmers, kind="mergesort")
    kmers, locs = kmers[order], locs[order]
    n = int(kmers.size)
    change = np.ones(n, dtype=bool)
    change[1:] = kmers[1:] != kmers[:-1]
    starts = np.nonzero(change)[0].astype(np.uint64)
    offsets = np.append(starts, np.uint64(n))
    post = np.empty(n * 2, dtype=np.uint32)
    post[0::2] = (locs >> np.uint64(32)).astype(np.uint32)
    post[1::2] = (locs & np.uint64(0xFFFFFFFF)).astype(np.uint32)
    return {
        "kmers.bin": kmers[starts].astype("<u8").tobytes(),
        "offsets.bin": offsets.astype("<u8").tobytes(),
        "postings.bin": post.astype("<u4").tobytes(),
        "n_keys": int(starts.size),
        "n_postings": n,
    }


def _write_fasta(path: Path, seed: int = 7, sizes=(5000, 37, 3, 12000, 800)) -> None:
    rng = random.Random(seed)
    lines = []
    for i, n in enumerate(sizes):
        # low-complexity runs + Ns + lowercase exercise skew, skips and case folding
        seq = "".join(rng.choice("ACGTTTTTtn") for _ in range(n))
        if n > 100:
            seq = seq[:50] + "T" * 60 + "N" * 20 + seq[130:]
        lines.append(f">ctg{i} desc")
        lines += [seq[j : j + 61] for j in range(0, len(seq), 61)]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


@pytest.mark.parametrize(
    "k,bits,mem_gb,sizes",
    [
        (15, None, None, (5000, 37, 3, 12000, 800)),
        (15, 0, None, (5000, 37, 3, 12000, 800)),
        (15, 4, None, (5000, 37, 3, 12000, 800)),
        (15, 30, None, (5000, 37, 3, 12000, 800)),
        (5, 3, None, (5000, 37, 3, 12000, 800)),
        (21, 8, None, (5000, 37, 3, 12000, 800)),
        # Tiny cap: forces multi-chunk contigs (pass 1) and recursive bucket splits (pass 2).
        (15, 2, 1e-6, (200000, 5000, 70000)),
        (5, 0, 1e-6, (200000, 3000)),
    ],
)
def test_streaming_pack_matches_legacy(tmp_path: Path, k: int, bits, mem_gb, sizes) -> None:
    fasta = tmp_path / "ref.fa"
    _write_fasta(fasta, sizes=sizes)
    out = tmp_path / f"pack_k{k}_{bits}"
    meta = build_dense_pack(fasta, out, k=k, bucket_bits=bits, max_mem_gb=mem_gb)
    want = _legacy_bins(fasta, k)
    for name in ("kmers.bin", "offsets.bin", "postings.bin"):
        assert (out / name).read_bytes() == want[name], name
    assert meta["n_keys"] == want["n_keys"]
    assert meta["n_postings"] == want["n_postings"]
    disk = json.loads((out / "meta.json").read_text())
    assert disk["contigs"] == [n for n, _ in read_fasta_contigs(fasta)]
    assert disk["n_bases"] == sum(len(s) for _, s in read_fasta_contigs(fasta))
    seq_bytes = (out / "sequences.bin").read_bytes()
    assert seq_bytes == b"".join(s for _, s in read_fasta_contigs(fasta))
    assert not (out / ".build_tmp").exists()

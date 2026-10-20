"""Dense Mojo linear k-mer pack (dense-v1) — fleet sibling of bwameth.

Layout under ``${REF}.mojo_linear_k${k}/``:

  meta.json      format=dense-v1, k, n_keys, n_postings, contigs
  kmers.bin      uint64 LE, sorted unique 2-bit-encoded k-mers
  offsets.bin    uint64 LE, length n_keys+1 (CSR starts into postings)
  postings.bin   uint32 LE pairs (contig_id, pos) — 8 bytes/posting

k ≤ 31 (fits in uint64 with 2 bits/base). Ambiguous bases skip the window.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Sequence, Tuple

import numpy as np

_BASE_CODE = np.full(256, 255, dtype=np.uint8)
_BASE_CODE[ord("A")] = 0
_BASE_CODE[ord("C")] = 1
_BASE_CODE[ord("G")] = 2
_BASE_CODE[ord("T")] = 3
_BASE_CODE[ord("a")] = 0
_BASE_CODE[ord("c")] = 1
_BASE_CODE[ord("g")] = 2
_BASE_CODE[ord("t")] = 3


def pack_is_complete(cache_dir: Path) -> bool:
    return (
        (cache_dir / "meta.json").is_file()
        and (cache_dir / "kmers.bin").is_file()
        and (cache_dir / "offsets.bin").is_file()
        and (cache_dir / "postings.bin").is_file()
        and (cache_dir / "sequences.bin").is_file()
        and (cache_dir / "contig_offsets.bin").is_file()
    )


def write_sequences_bin(c2t_fasta: Path, out_dir: Path) -> dict:
    """Write Mojo-mmap'd contig bases (no newlines) + u64 CSR offsets.

    Offline pack step only — runtime Mojo never loads FASTA via Python.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    names: List[str] = []
    starts: List[int] = []
    seq_path = out_dir / "sequences.bin"
    with seq_path.open("wb") as fh:
        for name, seq in iter_fasta_contigs(c2t_fasta):
            names.append(name)
            starts.append(fh.tell())
            fh.write(seq)
        starts.append(fh.tell())
    if not names:
        raise RuntimeError(f"no contigs in {c2t_fasta}")
    offsets = np.asarray(starts, dtype=np.uint64)
    (out_dir / "contig_offsets.bin").write_bytes(offsets.astype("<u8", copy=False).tobytes())
    (out_dir / "contigs.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    meta_path = out_dir / "meta.json"
    meta: dict = {}
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["contigs"] = names
    meta["n_contigs"] = len(names)
    meta["n_bases"] = int(offsets[-1])
    meta["sequences"] = "sequences.bin+contig_offsets.bin"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote sequences.bin n_contigs={len(names)} n_bases={int(offsets[-1])} → {out_dir}",
        flush=True,
    )
    return meta


def _ensure_ref_link(cache_dir: Path, c2t_fasta: Path) -> None:
    """Point ``cache_dir/ref.fa`` at the C2T FASTA (symlink preferred)."""
    ref_link = cache_dir / "ref.fa"
    c2t_fasta = Path(c2t_fasta)
    if ref_link.exists() or ref_link.is_symlink():
        return
    try:
        ref_link.symlink_to(c2t_fasta.resolve())
    except OSError:
        import shutil

        shutil.copy2(c2t_fasta, ref_link)


def ensure_dense_pack(
    *,
    c2t_fasta: Path,
    cache_dir: Path,
    k: int = 15,
    log: Optional[Callable[[str], None]] = None,
) -> Path:
    """Return a complete dense-v1 pack, building under an exclusive flock if missing.

    Concurrent workers serialize on ``${cache_dir}.lock``. After the lock is
    acquired the pack is re-checked so only the first builder runs.
    Set ``METHYLGRAPHER_LINEAR_CACHE_BUILD=0`` to fail instead of building.
    """
    c2t_fasta = Path(c2t_fasta)
    cache_dir = Path(cache_dir)

    def _log(msg: str) -> None:
        if log is not None:
            log(msg)
        else:
            print(msg, flush=True)

    if pack_is_complete(cache_dir):
        _ensure_ref_link(cache_dir, c2t_fasta)
        return cache_dir

    auto = os.environ.get("METHYLGRAPHER_LINEAR_CACHE_BUILD", "1").strip().lower()
    if auto in ("0", "false", "no", "off"):
        raise RuntimeError(
            f"Mojo dense-v1 pack missing at {cache_dir} "
            f"(METHYLGRAPHER_LINEAR_CACHE_BUILD={auto})"
        )

    if not c2t_fasta.is_file():
        raise FileNotFoundError(f"C2T FASTA required to build pack: {c2t_fasta}")

    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    lock_path = Path(str(cache_dir) + ".lock")
    _log(f"mojo_linear_pack: waiting for lock {lock_path}")
    t0 = time.time()
    with lock_path.open("a+", encoding="utf-8") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        _log(f"mojo_linear_pack: acquired lock after {time.time() - t0:.1f}s")
        if pack_is_complete(cache_dir):
            _log(f"mojo_linear_pack: pack already complete (other worker) → {cache_dir}")
            _ensure_ref_link(cache_dir, c2t_fasta)
            return cache_dir
        # If k-mer bins exist but sequences.bin was added later, only patch that.
        has_kmers = (cache_dir / "kmers.bin").is_file() and (cache_dir / "meta.json").is_file()
        if has_kmers and not (cache_dir / "sequences.bin").is_file():
            _log(f"mojo_linear_pack: writing sequences.bin into existing pack → {cache_dir}")
            write_sequences_bin(c2t_fasta, cache_dir)
            _ensure_ref_link(cache_dir, c2t_fasta)
            return cache_dir
        _log(f"mojo_linear_pack: building dense-v1 k={k} → {cache_dir}")
        build_dense_pack(c2t_fasta, cache_dir, k=k)
        _ensure_ref_link(cache_dir, c2t_fasta)
        lock_fh.write(f"built k={k} t={time.time():.0f}\n")
        lock_fh.flush()
    return cache_dir


def iter_fasta_contigs(path: Path) -> Iterator[Tuple[str, bytes]]:
    """Yield (name, upper-cased sequence) one contig at a time (bounded memory)."""
    name = ""
    chunks: List[bytes] = []
    with Path(path).open("rb") as fh:
        for raw in fh:
            if raw.startswith(b">"):
                if name:
                    yield name, b"".join(chunks).upper()
                header = raw[1:].decode("ascii", errors="replace").strip()
                name = header.split()[0] if header else "unnamed"
                chunks = []
            else:
                chunks.append(raw.strip())
    if name:
        yield name, b"".join(chunks).upper()


def read_fasta_contigs(path: Path) -> List[Tuple[str, bytes]]:
    return list(iter_fasta_contigs(path))


def encode_kmers_contig(seq: bytes, k: int, contig_id: int) -> Tuple[np.ndarray, np.ndarray]:
    """Return (kmers u64, locs u64 packed as contig_id<<32|pos) for one contig."""
    n = len(seq)
    if n < k:
        return np.empty(0, dtype=np.uint64), np.empty(0, dtype=np.uint64)
    codes8 = _BASE_CODE[np.frombuffer(seq, dtype=np.uint8)]
    n_win = n - k + 1
    # Window invalid if any base > 3 (N/other → 255 in table).
    bad = codes8 > 3
    # rolling OR of bad flags across window via cumsum trick
    bad_u32 = bad.astype(np.uint32)
    cumbad = np.zeros(n + 1, dtype=np.uint32)
    cumbad[1:] = np.cumsum(bad_u32)
    window_bad = (cumbad[k:] - cumbad[:-k]) > 0

    # 2-bit pack: sum codes[i+j] << 2*(k-1-j)
    kmers = np.zeros(n_win, dtype=np.uint64)
    for j in range(k):
        shift = np.uint64(2 * (k - 1 - j))
        kmers |= codes8[j : j + n_win].astype(np.uint64) << shift

    pos = np.arange(n_win, dtype=np.uint64)
    locs = (np.uint64(contig_id) << np.uint64(32)) | pos
    keep = ~window_bad
    # Also drop any window that still has high bits from 255 codes
    keep &= kmers < (np.uint64(1) << np.uint64(2 * k))
    return kmers[keep], locs[keep]


_DEFAULT_BUCKET_BITS = 10
_DEFAULT_MAX_MEM_GB = 16.0
# Conservative working-set estimates (bytes per element) used to size chunks.
_PASS1_BYTES_PER_BASE = 96
_PASS2_BYTES_PER_POSTING = 64
_SPLIT_BITS = 8


def _bucket_bits(k: int, requested: Optional[int]) -> int:
    bits = _DEFAULT_BUCKET_BITS if requested is None else int(requested)
    return max(0, min(bits, 2 * k))


def _append(path: Path, arr: np.ndarray) -> None:
    with path.open("ab") as fh:
        fh.write(arr.tobytes())


class _PackWriter:
    """Appends sorted CSR output for consecutive k-mer ranges."""

    def __init__(self, out_dir: Path) -> None:
        self.kf = (out_dir / "kmers.bin").open("wb")
        self.of = (out_dir / "offsets.bin").open("wb")
        self.pf = (out_dir / "postings.bin").open("wb")
        self.base = 0
        self.n_keys = 0
        self.last_key: Optional[int] = None

    def emit_sorted(self, km: np.ndarray, cid: np.ndarray, pos: np.ndarray) -> None:
        if km.size == 0:
            return
        change = np.ones(km.size, dtype=bool)
        change[1:] = km[1:] != km[:-1]
        if self.last_key is not None and int(km[0]) == self.last_key:
            change[0] = False  # same key continues from previous chunk
        starts = np.nonzero(change)[0]
        self.kf.write(km[starts].astype("<u8").tobytes())
        self.of.write((starts.astype(np.uint64) + np.uint64(self.base)).astype("<u8").tobytes())
        self.n_keys += int(starts.size)
        del change, starts
        post = np.empty(km.size * 2, dtype="<u4")
        post[0::2] = cid
        post[1::2] = pos
        self.pf.write(post.tobytes())
        self.base += int(km.size)
        self.last_key = int(km[-1])

    def close(self) -> None:
        self.of.write(np.asarray([self.base], dtype="<u8").tobytes())
        for fh in (self.kf, self.of, self.pf):
            fh.close()


def _emit_bucket(
    stem: Path,
    count: int,
    low_bits: int,
    kmer_dtype: np.dtype,
    budget: int,
    writer: _PackWriter,
) -> None:
    """Sort+emit one on-disk bucket (stem.k/.c/.p) whose k-mers share all bits
    above ``low_bits``. Buckets larger than ``budget`` postings are split on
    the next bits by streaming, then emitted in k-mer order (recursively)."""
    kp, cp, pp = (Path(f"{stem}.{x}") for x in ("k", "c", "p"))
    isz = kmer_dtype.itemsize
    if count <= budget or low_bits == 0:
        if count <= budget:
            km = np.fromfile(kp, dtype=kmer_dtype)
            order = np.argsort(km, kind="stable")
            km = km[order]
            cid = np.fromfile(cp, dtype="<u4")[order]
            pos = np.fromfile(pp, dtype="<u4")[order]
            del order
            writer.emit_sorted(km, cid, pos)
            del km, cid, pos
        else:
            # Every posting has the same k-mer: already in (contig, pos) order.
            for lo in range(0, count, budget):
                n = min(budget, count - lo)
                km = np.fromfile(kp, dtype=kmer_dtype, count=n, offset=lo * isz)
                cid = np.fromfile(cp, dtype="<u4", count=n, offset=lo * 4)
                pos = np.fromfile(pp, dtype="<u4", count=n, offset=lo * 4)
                writer.emit_sorted(km, cid, pos)
        for x in (kp, cp, pp):
            x.unlink()
        return
    sb = min(_SPLIT_BITS, low_bits)
    sub_shift = low_bits - sb
    mask = (1 << sb) - 1
    sub_counts = np.zeros(1 << sb, dtype=np.int64)
    for lo in range(0, count, budget):
        n = min(budget, count - lo)
        km = np.fromfile(kp, dtype=kmer_dtype, count=n, offset=lo * isz)
        cid = np.fromfile(cp, dtype="<u4", count=n, offset=lo * 4)
        pos = np.fromfile(pp, dtype="<u4", count=n, offset=lo * 4)
        sub = ((km.astype(np.uint64) >> np.uint64(sub_shift)) & np.uint64(mask)).astype(np.int64)
        order = np.argsort(sub, kind="stable")
        sub = sub[order]
        present, first = np.unique(sub, return_index=True)
        bounds = list(first) + [sub.size]
        km, cid, pos = km[order], cid[order], pos[order]
        del order, sub
        for i, sbk in enumerate(present):
            a, b = int(bounds[i]), int(bounds[i + 1])
            sstem = Path(f"{stem}_{int(sbk):03d}")
            _append(Path(f"{sstem}.k"), km[a:b])
            _append(Path(f"{sstem}.c"), cid[a:b])
            _append(Path(f"{sstem}.p"), pos[a:b])
            sub_counts[int(sbk)] += b - a
        del km, cid, pos
    for x in (kp, cp, pp):
        x.unlink()
    for sbk in range(1 << sb):
        if sub_counts[sbk]:
            _emit_bucket(
                Path(f"{stem}_{sbk:03d}"), int(sub_counts[sbk]), sub_shift, kmer_dtype, budget, writer
            )


def build_dense_pack(
    c2t_fasta: Path,
    out_dir: Path,
    k: int = 15,
    *,
    bucket_bits: Optional[int] = None,
    tmp_dir: Optional[Path] = None,
    max_mem_gb: Optional[float] = None,
) -> dict:
    """Build a dense-v1 pack with memory bounded by ``max_mem_gb`` (by design).

    Pass 1 streams the FASTA one contig at a time, encodes it in chunks of at
    most ``max_mem_gb / _PASS1_BYTES_PER_BASE`` bases, and appends valid
    windows to on-disk buckets keyed by the top ``bucket_bits`` k-mer bits in
    (contig, position) order. Pass 2 emits buckets in k-mer order; a bucket
    is loaded and stable-sorted only if it fits the budget, otherwise it is
    split on the next bits by streaming (recursively). Output is byte-identical
    to a global stable sort of all postings, independent of genome size.
    """
    if k < 1 or k > 31:
        raise ValueError(f"k must be in 1..31, got {k}")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    mem_gb = _DEFAULT_MAX_MEM_GB if max_mem_gb is None else float(max_mem_gb)
    if mem_gb <= 0:
        raise ValueError("max_mem_gb must be > 0")
    mem_bytes = int(mem_gb * (1 << 30))
    chunk_bases = max(1 << 16, mem_bytes // _PASS1_BYTES_PER_BASE)
    budget = max(1 << 12, mem_bytes // _PASS2_BYTES_PER_POSTING)
    bits = _bucket_bits(k, bucket_bits)
    n_buckets = 1 << bits
    shift = np.uint64(2 * k - bits)
    kmer_dtype = np.dtype("<u4") if k <= 16 else np.dtype("<u8")
    work = Path(tmp_dir) if tmp_dir is not None else out_dir / ".build_tmp"
    if work.exists():
        import shutil

        shutil.rmtree(work)
    work.mkdir(parents=True)

    def _stem(b: int) -> Path:
        return work / f"b{b:05d}"

    print(
        f"reading FASTA {c2t_fasta} (max_mem_gb={mem_gb:g} chunk_bases={chunk_bases} "
        f"bucket_budget={budget} buckets={n_buckets})",
        flush=True,
    )
    names: List[str] = []
    total_bases = 0
    counts = np.zeros(n_buckets, dtype=np.int64)
    for cid, (name, seq) in enumerate(iter_fasta_contigs(c2t_fasta)):
        names.append(name)
        n = len(seq)
        total_bases += n
        for start in range(0, max(n - k + 1, 0), chunk_bases):
            piece = seq[start : start + chunk_bases + k - 1]
            km, loc = encode_kmers_contig(piece, k, cid)
            del piece
            if not km.size:
                continue
            pos = ((loc & np.uint64(0xFFFFFFFF)) + np.uint64(start)).astype("<u4")
            del loc
            if bits:
                bucket = (km >> shift).astype(np.int64)
                order = np.argsort(bucket, kind="stable")
                bucket = bucket[order]
                km, pos = km[order], pos[order]
                del order
                present, first = np.unique(bucket, return_index=True)
                bounds = list(first) + [bucket.size]
                del bucket
            else:
                present, bounds = np.zeros(1, dtype=np.int64), [0, km.size]
            km = km.astype(kmer_dtype)
            for i, b in enumerate(present):
                lo, hi = int(bounds[i]), int(bounds[i + 1])
                st = _stem(int(b))
                _append(Path(f"{st}.k"), km[lo:hi])
                _append(Path(f"{st}.c"), np.full(hi - lo, cid, dtype="<u4"))
                _append(Path(f"{st}.p"), pos[lo:hi])
                counts[int(b)] += hi - lo
            del km, pos
        del seq
        if (cid + 1) % 5 == 0:
            print(f"  encoded {cid + 1} ({name}, {n} bp)", flush=True)
    if not names:
        raise RuntimeError(f"no contigs in {c2t_fasta}")
    print(f"contigs={len(names)} bases={total_bases}", flush=True)
    n_postings = int(counts.sum())
    if n_postings == 0:
        raise RuntimeError("no valid k-mers (check alphabet / k)")

    print(f"sorting {n_postings} postings in {n_buckets} buckets…", flush=True)
    writer = _PackWriter(out_dir)
    for b in range(n_buckets):
        if counts[b]:
            _emit_bucket(_stem(b), int(counts[b]), 2 * k - bits, kmer_dtype, budget, writer)
    writer.close()
    n_keys = writer.n_keys
    assert writer.base == n_postings
    import shutil

    shutil.rmtree(work, ignore_errors=True)
    print(f"wrote bins n_keys={n_keys} n_postings={n_postings}", flush=True)

    meta = {
        "format": "dense-v1",
        "k": k,
        "n_keys": n_keys,
        "n_postings": n_postings,
        "contigs": names,
        "c2t_fasta": str(c2t_fasta),
        "endian": "little",
        "kmer_encoding": "2bit-ACGT",
        "posting": "u32_contig_id,u32_pos0",
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    write_sequences_bin(c2t_fasta, out_dir)
    legacy = out_dir / "hits.tsv"
    if legacy.is_file():
        legacy.unlink()
    print(f"OK dense-v1 → {out_dir}", flush=True)
    return meta


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build dense-v1 Mojo linear k-mer pack")
    p.add_argument("--ref", required=True, help="C2T FASTA (or raw FASTA to index as-is)")
    p.add_argument("--out", required=True, help="Output pack directory")
    p.add_argument("-k", type=int, default=15)
    p.add_argument(
        "--sequences-only",
        action="store_true",
        help="Only (re)write sequences.bin + contig_offsets.bin for an existing pack",
    )
    p.add_argument(
        "--bucket-bits",
        type=int,
        default=None,
        help=f"k-mer prefix bits for on-disk partitioning (default {_DEFAULT_BUCKET_BITS})",
    )
    p.add_argument("--tmp-dir", default=None, help="Scratch dir for buckets (default OUT/.build_tmp)")
    p.add_argument(
        "--max-mem-gb",
        type=float,
        default=float(os.environ.get("MOJO_LINEAR_PACK_MAX_MEM_GB", _DEFAULT_MAX_MEM_GB)),
        help="Working-memory cap in GiB (env MOJO_LINEAR_PACK_MAX_MEM_GB; default 16)",
    )
    args = p.parse_args(argv)
    if args.sequences_only:
        write_sequences_bin(Path(args.ref), Path(args.out))
        return 0
    build_dense_pack(
        Path(args.ref),
        Path(args.out),
        k=args.k,
        bucket_bits=args.bucket_bits,
        tmp_dir=Path(args.tmp_dir) if args.tmp_dir else None,
        max_mem_gb=args.max_mem_gb,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# MojoFq2bamMeth benchmarks (linear WGBS Align)

> **Repository:** GoliathAlign (formerly `mojo-align`). `GOLIATH_ALIGN_*` is the environment family. `MOJO_ALIGN_*` and `/opt/mojo-align` remain one-cycle aliases of `GOLIATH_ALIGN_*` and `/opt/goliath-align`.

Science contract: directional PE → BAM + QC. See [`LINEAR_FQ2BAM_SPEC.md`](LINEAR_FQ2BAM_SPEC.md).

## Toy fixture

From the repository root (`samtools` on `PATH`). `fq2bam-meth/scripts/run_toy_fq2bam_meth.sh` and `benchmark_fq2bam_meth.sh` look for `bin/methylGrapher` next to `scripts/`, which is the flat tree from `scripts/stage_flat_image_tree.sh`.

```bash
./bin/methylGrapher MojoFq2bamMeth \
  -fq1 fq2bam-meth/tests/data/fq2bam_fixture/R1.fastq \
  -fq2 fq2bam-meth/tests/data/fq2bam_fixture/R2.fastq \
  -ref fq2bam-meth/tests/data/fq2bam_fixture/ref.fa \
  -out_bam /tmp/toy.bam -out_qc_dir /tmp/toy_qc -sample_id toy \
  -device cpu -k 8 -t 2
# Clara wall clock beside Mojo (GPU require on; pbrun or the image inside the script):
fq2bam-meth/scripts/benchmark_clara_fq2bam_meth.sh [R1] [R2] [REF] nvidia
```

## Parabricks sample parity (`align.linear.parabricks` vs `align.linear.mojo`)

End-to-end concordance on NVIDIA’s public `parabricks_sample` bundle (or any
FASTQ pair), writing side-by-side product dirs:

```bash
fq2bam-meth/scripts/fetch_parabricks_sample.sh   # → /work/samples/parabricks_sample
fq2bam-meth/scripts/parity_linear_parabricks_vs_mojo.sh --device nvidia
```

See [`LINEAR_PARITY.md`](LINEAR_PARITY.md) and [`LINEAR_ENGINES.md`](LINEAR_ENGINES.md)
(parity = frozen k-mer fallback; `fm` = default; `speed` = opt-in).

Output is **BAM only**. Parity/speed stream SAM through a FIFO into
`samtools view -u`, then `fixmate` / `sort -l 1` / `markdup`. FM writes native
BGZF. Sort/emit is automatic from `nvidia-smi` total HBM (dedicated Align
worker) plus a FASTQ-size `n` estimate: one-shot when the uncompressed BAM
fits, SSD tiles when it would not (30× or a small GPU). No `--low-memory`
flag. Python `heapq` merges tiled runs.

| Backend | Device | Fixture | Notes |
|---------|--------|---------|-------|
| Mojo linear | `cpu` / `DeviceContext(api=cpu)` | PASS | streaming batches + hash postings; seeds→extend |
| Mojo linear | `nvidia:sm_90` | PASS (toy) / operator (subset) | GPU seeds wired into extend; `GPU_REQUIRE=1` bakeoff |
| Mojo linear | `amdgpu:gfx942` | operator | ROCm image `1.70-mojo-rocm` |
| BWA-MEM | CPU | PASS | `LINEAR_MAPPER=bwa` only; **blocked** when `GPU_REQUIRE=1` |

## Clara baseline (B0)

Harness: [`scripts/benchmark_clara_fq2bam_meth.sh`](../scripts/benchmark_clara_fq2bam_meth.sh).

| Run | Wall | Status |
|-----|------|--------|
| Mojo toy (`GPU_REQUIRE=1`, nvidia) | ~1.8 s | recorded locally |
| Clara `pbrun fq2bam_meth` | — | **PENDING** (`pbrun` not on this host; operator on NGC/GH200) |

## Production gates (operator)

| Gate | Criterion | Status |
|------|-----------|--------|
| Toy PE BAM + QC schema | mapped > 0, JSON keys, `mapper=mojo` | **PASS** (CI/local) |
| NVIDIA subset vs Clara `pbrun fq2bam_meth` | Mojo wall **&lt; Clara** (strict) | **PENDING** operator on GH200 |
| AMD MI300X twin | Mojo AMD wall ≈ NVIDIA Mojo twin; ≫ BWA CPU | **PENDING** ROCm bakeoff |
| Complete status | both wall-clock gates green | **PENDING** (default mapper is already `mojo`) |

Record operator runs from the repository root:

```bash
fq2bam-meth/scripts/benchmark_clara_fq2bam_meth.sh /path/to/R1.fastq.gz /path/to/R2.fastq.gz /path/to/ref.fa nvidia
fq2bam-meth/scripts/parity_linear_parabricks_vs_mojo.sh --device nvidia
```

`benchmark_fq2bam_meth.sh` resolves `bin/methylGrapher` as the parent of `scripts/` (the flat tree). On this checkout, call `./bin/methylGrapher MojoFq2bamMeth` as in the toy section.

## BWA-MEM mapper

```bash
export METHYLGRAPHER_LINEAR_MAPPER=bwa
```
# GoliathAlign

GoliathAlign is a standalone bisulfite alignment toolkit. It maps whole-genome bisulfite reads on Linux x86-64 and ARM64, using CPU, NVIDIA CUDA, or AMD HIP through Mojo `DeviceContext`. The linear aligner, `MojoFq2bamMeth`, follows the directional C→T / G→A method used by [bwa-meth](https://github.com/brentp/bwa-meth) and by NVIDIA Clara Parabricks `fq2bam_meth`. The same install aligns reads to converted genome graphs and calls methylation from the resulting GAF.

The command name is `methylGrapher`. Mojo is the implementation language. The pixi workspace in [`pixi.toml`](pixi.toml) is still named `mojo-align` and records version `0.1.0`. This tree was previously published as `mojo-align`. The GitHub repository is [Goliath-Research/GoliathAlign](https://github.com/Goliath-Research/GoliathAlign).

License: MIT ([`LICENSE`](LICENSE)). `methylgrapher/` is a methylGrapher derivative; see [`methylgrapher/LICENSE`](methylgrapher/LICENSE) and [`methylgrapher/NOTICE`](methylgrapher/NOTICE).

Longer notes live under [`docs/`](docs/index.md). An optional MkDocs Material site builds from that directory with `mkdocs build`. The CI docs job runs that build and has no deploy step.

## Install

Pixi solves the Mojo / MAX toolchain, Python, pytest, and Pyrefly for `linux-64` and `linux-aarch64`:

```bash
curl -fsSL https://pixi.sh/install.sh | bash   # once, if pixi is not on PATH
pixi install
./bin/methylGrapher help
```

`samtools` is required for `MojoFq2bamMeth` (it is not a pixi dependency). `bwa` is required only when `METHYLGRAPHER_LINEAR_MAPPER=bwa` or when the Mojo mapper fails and falls back. `vg` is required for `PrepareGenome` and for the `cpu_vg` graph aligner.

From a checkout, `./bin/methylGrapher` runs the Python engine (`python -m engine.cli`) through pixi. Set `METHYLGRAPHER_ENGINE=mojo` to compile and run `methylgrapher/src/main.mojo` instead. Both entry points accept `MojoFq2bamMeth` and call `engine.fq2bam_meth`.

```bash
METHYLGRAPHER_ENGINE=mojo ./bin/methylGrapher help
pixi run typecheck
pixi run python -m pytest
```

The published host runtime is separate from a pixi checkout. See [Release 0.1.0-jammy](docs/release.md).

## Platforms and devices

| Host | How |
|------|-----|
| Linux x86-64 | pixi platform `linux-64` |
| Linux ARM64 | pixi platform `linux-aarch64` |

Host architecture is independent of the compute device. `-device` and `METHYLGRAPHER_ALIGN_DEVICE` accept `auto`, `cpu`, `nvidia`, and `amd`.

| Device | Kernel label | `DeviceContext` API |
|--------|--------------|---------------------|
| `nvidia` | `nvidia:sm_90` | `cuda` |
| `amd` | `amdgpu:gfx942`, or `amdgpu:` plus `METHYLGRAPHER_AMDGPU_ARCH` | `hip` |
| `cpu` | host | `cpu` |
| `auto` | NVIDIA, then AMD, then CPU | probed in that order |

`auto` tries `DeviceContext`, then `nvidia-smi`, then `rocm-smi` / `rocminfo`. A checkout compile with `METHYLGRAPHER_ENGINE=mojo` passes `--target-accelerator`. The default target is `nvidia:sm_90`. If `METHYLGRAPHER_AMDGPU_ARCH` is set and no target override is set, the target is `amdgpu:$METHYLGRAPHER_AMDGPU_ARCH`. Override either choice with `METHYLGRAPHER_TARGET_ACCELERATOR`.

Names this tree reads first are `GOLIATH_ALIGN_*` and the directory `/opt/goliath-align`. `MOJO_ALIGN_*`, `METHYLGRAPHER_MOJO_*`, `/opt/mojo-align`, and `/opt/methylgrapher-mojo` still resolve, and the process prints a deprecation warning.

## Packages

| Path | Role |
|------|------|
| `gpu-common/` | Device selection, seed kernels, HBM preflight |
| `fq2bam-meth/` | Linear WGBS mapper (`MojoFq2bamMeth`) |
| `giraffe/` | Graph mapper (`MojoGiraffe`, GBZ stream map) |
| `methylgrapher/` | `methylGrapher` CLI, `Align`, methylation calling |
| `numeric/` | DeviceContext centroid-stream kernels |

Mojo include paths, also set by `bin/methylGrapher`:

```text
-I gpu-common/src -I fq2bam-meth/src -I giraffe/src -I methylgrapher/src -I numeric/src
```

## Linear alignment

`MojoFq2bamMeth` is the linear whole-genome bisulfite aligner. It is the same method class as bwa-meth and Clara Parabricks `fq2bam_meth`: convert read 1 C→T and read 2 G→A, map against a C→T reference (preferring a bwa-meth dual-strand FASTA, `${REF}.bwameth.c2t`), and emit a coordinate-sorted, duplicate-marked BAM.

```bash
./bin/methylGrapher MojoFq2bamMeth \
  -fq1 R1.fastq.gz -fq2 R2.fastq.gz -ref GRCh38.fa \
  -out_bam sample.bam -out_qc_dir sample_qc -sample_id SAMPLE \
  -device auto -t 16 -k 15
```

The mapper writes:

| Output | Contents |
|--------|----------|
| `-out_bam` | BAM. The default `fm` engine writes coordinate-sorted, duplicate-marked BGZF and then runs `samtools index` (`.bai`). `parity`, `speed`, and `bwa` run `samtools fixmate`, `sort`, and `markdup` first. |
| `-out_bam` parent `/ <sample_id>.json` | Parabricks-shaped metrics (`engine` is `mojo_fq2bam_meth`) |
| `-out_qc_dir/alignment_summary.json` | `flagstat`, `samtools stats`, and the mapper name |
| `-out_qc_dir/<sample_id>.json` | Copy of the metrics JSON |
| `-work_dir/mojo_fq2bam_meth.log` | Command log. Without `-work_dir`, the log is under a temporary `mojo_fq2bam_*` directory |

`METHYLGRAPHER_LINEAR_ENGINE` selects the Mojo mapper: `fm` (default; BWA `.bwt` / `.sa` / `.pac` on the converted reference), `parity` (frozen k-mer pack), or `speed` (k-mer consensus). `METHYLGRAPHER_LINEAR_MAPPER=bwa` forces BWA-MEM on CPU. If the Mojo mapper fails, the orchestrator falls back to BWA-MEM unless `METHYLGRAPHER_GPU_REQUIRE` is `1`, `true`, `yes`, or `on`.

Set `METHYLGRAPHER_WRITE_METH_TAGS=1` to add `XM:Z` and `XG:Z` tags after alignment. Details: [`fq2bam-meth/docs/LINEAR_FQ2BAM_SPEC.md`](fq2bam-meth/docs/LINEAR_FQ2BAM_SPEC.md), [`fq2bam-meth/docs/LINEAR_ENGINES.md`](fq2bam-meth/docs/LINEAR_ENGINES.md).

A paired-end fixture lives at `fq2bam-meth/tests/data/fq2bam_fixture/`. Concordance against a Clara `fq2bam_meth` BAM is `fq2bam-meth/scripts/parity_linear_parabricks_vs_mojo.sh` (default gates: mapped-rate absolute delta ≤ 0.02, primary-contig idxstats Spearman ≥ 0.95).

## Graph alignment and methylation calls

`Align` converts the FASTQ pair, maps it to the C→T and G→A indexes under `-index_prefix`, and writes `alignment.gaf` in `-work_dir`. `-align_engine` (or `METHYLGRAPHER_ALIGN_ENGINE`) is `cpu_vg` (default; `vg giraffe` GAF with named coordinates), `mojo_giraffe`, or `gpu_giraffe`.

`MojoGiraffe` maps one graph (GFA, or a GBZ quartet `-gbz` / `-dist` / `-min` / `-zipcodes`) straight to `-out_gaf`. Optional `-out_sam` plus `-segment_offsets` writes a linear SAM file.

`MethylCall` reads `alignment.gaf` and writes `graph.methyl`. `MergeCpG` writes `graph.cpg.tsv`. `ConversionRate` prints a conversion-rate estimate. `PrepareGenome` builds the converted GFA pair, the CpG table, and the `vg giraffe` indexes those commands expect.

`METHYLGRAPHER_MCALL_ENGINE=python` forces the Mojo CLI to run `Align`, `MethylCall`, `MergeCpG`, and `ConversionRate` through the Python engine.

Command reference: [`docs/cli.md`](docs/cli.md). Graph contract: [`giraffe/docs/GIRAFFE_SPEC.md`](giraffe/docs/GIRAFFE_SPEC.md).

## Flat tree and host runtime

`scripts/stage_flat_image_tree.sh [DEST]` copies the packages into one tree (`engine/`, `src/`, `scripts/`, `tests/`, `bin/methylGrapher`). `DEST` defaults to `./_flat_image`.

`scripts/package_host_runtime.sh` builds `goliath-align-host-linux-amd64-jammy.tar.gz` inside `ubuntu:22.04`. That archive is the artifact for release [0.1.0-jammy](docs/release.md). Its `bin/methylGrapher` runs the bundled `mojo` on `src/main.mojo`. Set `METHYLGRAPHER_MCALL_ENGINE=python` to run `python -m engine.cli` instead.

Helper scripts under `fq2bam-meth/scripts/` such as `run_toy_fq2bam_meth.sh` treat the parent of `scripts/` as the root, which matches that flat tree (`bin/methylGrapher` beside `scripts/`). From this checkout, call `./bin/methylGrapher` with paths under `fq2bam-meth/tests/data/fq2bam_fixture/`. `fq2bam-meth/scripts/parity_linear_parabricks_vs_mojo.sh` walks two directories up and runs from this checkout.

## CI and type checking

GitHub Actions (`.github/workflows/ci.yml`) installs pixi, runs `methylGrapher help`, Pyrefly, a pytest subset, and the flat-tree stage. It also validates [`.goliath/product.json`](.goliath/product.json) and builds the MkDocs site. The docs job does not upload the site.

Python helpers are checked with [Pyrefly](https://pyrefly.org) using [`pyrefly.toml`](pyrefly.toml) and the Python 3.13 interpreter locked by pixi. Mojo sources are outside the check. `methylgrapher/python_reference/` is frozen upstream and is excluded.

```bash
pixi run typecheck
```

History of the Python-to-Mojo port and the repository rename is in [`MIGRATION_LOG.md`](MIGRATION_LOG.md).

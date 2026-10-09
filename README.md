# GoliathAlign

**GoliathApp** is the platform. **GoliathOmics** is the genomics product. **GoliathAlign** (formerly mojo-align) aligns reads. **MethylExtractor** calls methylation from linear BAM files. **GoliathWeb** is the public hub.

Index: [../GoliathApp/docs/workspace-index.md](../GoliathApp/docs/workspace-index.md).

Multiplatform Mojo aligner (MIT). It runs on Linux x86-64 and ARM64, on CPU and on NVIDIA CUDA or AMD HIP through Mojo `DeviceContext`. TPU and AWS Trainium are not implemented. The first product consumer is GoliathOmics whole-genome bisulfite sequencing. The linear path follows **bwa-meth**. `methylgrapher/` follows **methylGrapher**. Git history includes the former tree named `methylGrapher-mojo` (that repository no longer exists). This repository was named `mojo-align` until 2026-09-28. The local directory is GoliathAlign. The Git remote stays `Goliath-Research/mojo-align` until `gh repo rename GoliathAlign` is run on a logged-in machine; see [`MIGRATION_LOG.md`](MIGRATION_LOG.md).

Unified CLI remains `bin/methylGrapher`. Mojo is the language, not the product name.

## One-cycle aliases

| Current | Still accepted |
|---------|----------------|
| `GOLIATH_ALIGN_*` | `MOJO_ALIGN_*` (deprecation warning) |
| `/opt/goliath-align` | `/opt/mojo-align` (symlink in the image) |
| Sibling checkout `../GoliathAlign` | `../mojo-align` |

Image repository and tags stay `goliath/methylgrapher:*-mojo-*`.

## Packages

| Package | Role | License |
|---------|------|---------|
| `gpu-common/` | Portable DeviceContext device select + seed kernels + HBM preflight | **MIT** — see [`LICENSE`](LICENSE) |
| `fq2bam-meth/` | Mojo linear WGBS mapper (`align.linear.mojo`); published **bwa-meth** method class | **MIT** — see [`LICENSE`](LICENSE) |
| `giraffe/` | MojoGiraffe / GBZ stream map (`align.pangenome_wgbs.mojo`) | **MIT** — see [`LICENSE`](LICENSE) |
| `methylgrapher/` | Science + Align orchestration + `engine/` CLI | **MIT** — [`methylgrapher/LICENSE`](methylgrapher/LICENSE) (methylGrapher) |
| `numeric/` | Post-align DeviceContext kernels (centroid stream) | **MIT** — see [`LICENSE`](LICENSE) |

The whole monorepo is MIT open source. Linear mapping follows [bwa-meth](https://github.com/brentp/bwa-meth); `methylgrapher/` is a methylGrapher derivative.

## Align paths

Canonical align IDs are folder names under each sample. GoliathOmics creates those directories. This repository writes only the `-work_dir` it is given. Before/after bakeoffs keep Clara and `vg` as first-class arms. Mojo is the preferred science path.

| ID | Runtime | Role |
|----|---------|------|
| `align.linear.parabricks` | NVIDIA Parabricks `fq2bam_meth` | **Before** linear baseline |
| `align.linear.mojo` | MojoFq2bamMeth (`fq2bam-meth`) | **After** portable linear |
| `align.pangenome.parabricks` | Parabricks `giraffe` (BAM) | Stock non-BS pangenome (not WGBS GAF) |
| `align.pangenome.vg` / `align.pangenome_wgbs.vg` | `vg giraffe` (`cpu_vg`) | **Before** named-coordinate GAF oracle |
| `align.pangenome_wgbs.mojo` | MojoGiraffe dual-graph | **After** preferred WGBS science |

Optional extract staging (GoliathOmics compare harness; not written by this CLI):

| ID | Tool | Role |
|----|------|------|
| `extract.methylextractor/` | MethylExtractor | Production linear extract |
| `extract.methyldackel/` | Upstream MethylDackel | Optional A/B only |

```
/work/samples/<sampleId>/
  *.fastq.gz
  align.linear.parabricks/   # BAM, BAI, metrics
  align.linear.mojo/         # same shape — parity vs Parabricks
  align.pangenome.parabricks/
  align.pangenome.vg/          # or align.pangenome_wgbs.vg
  align.pangenome_wgbs.mojo/
  extract.methylextractor/     # optional staging
  extract.methyldackel/        # optional A/B
```

Multiple align dirs may coexist for side-by-side parity and linear-to-pangenome comparisons. Comparison reports land under `/work/samples/_comparisons/<stamp>/`.

## Quick start

```bash
pixi install
./bin/methylGrapher help
METHYLGRAPHER_ENGINE=mojo ./bin/methylGrapher help
pixi run python -m pytest
```

## Linear parity (Clara vs Mojo)

```bash
fq2bam-meth/scripts/fetch_parabricks_sample.sh   # once → /work/samples/parabricks_sample
fq2bam-meth/scripts/parity_linear_parabricks_vs_mojo.sh --device nvidia
```

Details: [`fq2bam-meth/docs/LINEAR_PARITY.md`](fq2bam-meth/docs/LINEAR_PARITY.md).

Mojo include paths (also set by `bin/methylGrapher`):

```text
-I gpu-common/src -I fq2bam-meth/src -I giraffe/src -I methylgrapher/src -I numeric/src
```

## Supported platforms

The pixi environment supports Linux x86-64 (`linux-64`) and Linux ARM64 (`linux-aarch64`) hosts. Host architecture is independent of the compute backends: CPU, NVIDIA CUDA, and AMD HIP. TPU and AWS Trainium backends are not implemented.

## Fleet image

This repo does not build the worker image. GoliathOmics `Dockerfile.mojo` expects a flat `engine/` + `src/` tree. Assemble it, then build from the GoliathOmics checkout (Docker image, and a `.sif` when Apptainer is installed):

```bash
bash scripts/stage_flat_image_tree.sh /tmp/goliath-align-flat
export GOLIATH_ALIGN_ROOT=/tmp/goliath-align-flat   # or point at this repo; the build script stages it
# in the GoliathOmics repo:
#   bash scripts/build_goliath_align_image.sh
#   bash scripts/run_goliath_align_sif.sh /work/goliath/images/methylgrapher-1.70-mojo-cuda.sif -- Align ...
```

In-container paths are `/opt/goliath-align` (symlink `/opt/mojo-align`) and the `methylGrapher` entrypoint. `MOJO_ALIGN_ROOT` still works for one cycle.

## CI

GitHub Actions is the CI for this repository (`.github/workflows/ci.yml`). Env family is `GOLIATH_ALIGN_*`.

## Type checking

Python helpers are checked with [Pyrefly](https://pyrefly.org). The config is [`pyrefly.toml`](pyrefly.toml). It follows the CI import path and the Python 3.13 interpreter locked by pixi. Mojo sources are outside the check. `methylgrapher/python_reference/` is frozen upstream and is excluded.

```bash
pixi run typecheck
```

## Migration notes

See [`MIGRATION_LOG.md`](MIGRATION_LOG.md) for the Python-to-Mojo science cutover and the 2026-09-28 repository rename.

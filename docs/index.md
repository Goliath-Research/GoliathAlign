# GoliathAlign

GoliathAlign is a standalone toolkit for whole-genome bisulfite alignment. It runs on Linux x86-64 and Linux ARM64. Compute devices are CPU, NVIDIA CUDA, and AMD HIP, selected through Mojo `DeviceContext`.

The linear command, `MojoFq2bamMeth`, maps a paired FASTQ against a C→T reference the way [bwa-meth](https://github.com/brentp/bwa-meth) and NVIDIA Clara Parabricks `fq2bam_meth` do, and writes a coordinate-sorted BAM plus a QC JSON report. `Align` and `MojoGiraffe` map the same kind of reads onto C→T and G→A genome graphs and write GAF. `MethylCall` turns that GAF into per-cytosine methylation counts.

Install a checkout with pixi, or unpack the Ubuntu 22.04 host runtime from release `0.1.0-jammy`. The command in both cases is `methylGrapher`.

| Topic | Page |
|-------|------|
| Pixi install and external tools | [Install](install.md) |
| Hosts, devices, and aligner engines | [Platforms and engines](platforms.md) |
| Linear BAM aligner | [Linear alignment](linear.md) |
| Graph GAF aligner and methylation calls | [Graph alignment](graph.md) |
| Every command, with inputs and outputs | [Command line](cli.md) |
| `v0.1.0-jammy` tarball | [Release 0.1.0-jammy](release.md) |

Package notes that sit next to the code:

| Path | Subject |
|------|---------|
| `fq2bam-meth/docs/LINEAR_FQ2BAM_SPEC.md` | Linear pipeline, devices, environment variables |
| `fq2bam-meth/docs/LINEAR_ENGINES.md` | `fm`, `parity`, and `speed` |
| `fq2bam-meth/docs/LINEAR_PARITY.md` | Clara `fq2bam_meth` concordance harness |
| `fq2bam-meth/docs/BENCHMARK_FQ2BAM_METH.md` | Linear wall-clock notes |
| `giraffe/docs/GIRAFFE_SPEC.md` | GBZ / GFA GAF contract |
| `giraffe/docs/BENCHMARK_GIRAFFE.md` | Giraffe timing notes |
| `giraffe/docs/ROCM_GIRAFFE_GATES.md` | AMD device target |
| `giraffe/docs/PHASE0_GH200_ALIGN.md` | Why Parabricks `giraffe` is BAM-only |
| `methylgrapher/docs/BENCHMARK_MCALL.md` | MethylCall subset timing |
| `numeric/README.md` | Centroid-stream kernels |

This site is optional. From a checkout, `mkdocs build` writes `site/`. The CI docs job runs that build and has no deploy step.

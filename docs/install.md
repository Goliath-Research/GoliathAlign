# Install

GoliathAlign's toolchain is the pixi environment in the repository root. The lockfile covers two hosts:

| Platform | Machines |
|----------|----------|
| `linux-64` | Linux x86-64 |
| `linux-aarch64` | Linux ARM64 |

Pixi installs Mojo / MAX (`modular` 26.6), Python (≥ 3.11 and &lt; 3.14; the lock solves 3.13), pytest, and Pyrefly. It does not install `samtools`, `bwa`, or `vg`.

```bash
curl -fsSL https://pixi.sh/install.sh | bash   # once, if pixi is not on PATH
cd /path/to/GoliathAlign
pixi install
./bin/methylGrapher help
```

`pixi.toml` names the workspace `mojo-align` and sets `version = "0.1.0"`. That version is the project version. The published host-runtime label is `0.1.0-jammy` ([Release](release.md)).

## Which launcher you are running

A git checkout and the jammy tarball do not start the same way.

| Tree | Default process | Other process |
|------|-----------------|---------------|
| Checkout `bin/methylGrapher` | `pixi run python -m engine.cli` | `METHYLGRAPHER_ENGINE=mojo` runs `mojo run --target-accelerator … methylgrapher/src/main.mojo` |
| Jammy `goliath-align/bin/methylGrapher` | Bundled `mojo src/main.mojo` when `mojo-env/bin/mojo` exists | `METHYLGRAPHER_MCALL_ENGINE=python` runs `python -m engine.cli`. The same Python command is the fallback when `mojo` is absent |

`MojoFq2bamMeth` on either launcher ends in `fq2bam-meth/python/fq2bam_meth.py` (copied to `engine/fq2bam_meth.py` in a flat tree or in the tarball). The map kernel is still `linear_mapper.mojo`.

The checkout's Mojo launch defaults `--target-accelerator` to `nvidia:sm_90`. If `METHYLGRAPHER_AMDGPU_ARCH` is set and `METHYLGRAPHER_TARGET_ACCELERATOR` is empty, the target is `amdgpu:$METHYLGRAPHER_AMDGPU_ARCH`. Set `METHYLGRAPHER_TARGET_ACCELERATOR` to pick a label yourself (`nvidia:sm_90` or `amdgpu:gfx942`).

## Tools the commands call

| Tool | When the code requires it |
|------|---------------------------|
| `samtools` | Every `MojoFq2bamMeth` run (`index`, and `flagstat` / `stats`; `fixmate` / `sort` / `markdup` for non-`fm` mappers) |
| `bwa` | `METHYLGRAPHER_LINEAR_MAPPER=bwa`, or Mojo failure when GPU require is off |
| `vg` | `PrepareGenome`, `vg_check`, and `align_engine=cpu_vg` |
| `pigz` or `gzip` | FM mapper, when `-fq1` / `-fq2` end in `.gz` (`linear_fastq.mojo` shells out to decompress) |

## Checks

```bash
pixi run typecheck          # Pyrefly, config in pyrefly.toml
pixi run python -m pytest   # full Python suite
pixi run help               # Mojo CLI help text
```

Python on `PYTHONPATH` for a checkout is `methylgrapher`, `giraffe/scripts`, `giraffe/python`, `fq2bam-meth/python`, and `gpu-common/python`. `bin/methylGrapher` exports that path before it starts.

## Names the runtime still accepts

`gpu-common/src/mojo_align_env.mojo` and `methylgrapher/engine/mojo_align_env.py` read `GOLIATH_ALIGN_<SUFFIX>` first. If that variable is empty they read `MOJO_ALIGN_<SUFFIX>`, then `METHYLGRAPHER_MOJO_<SUFFIX>`, and print a deprecation warning.

Install-prefix probes, in order: `/opt/goliath-align`, `/opt/mojo-align`, `/opt/methylgrapher-mojo`. A missing directory does not create it; the fallback returns `/opt/goliath-align` as the prefix string.

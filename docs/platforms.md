# Platforms and engines

## Hosts

The pixi environment is solved for `linux-64` and `linux-aarch64` only. The jammy release tarball is built on `ubuntu:22.04` and records `arch=amd64` in `HOST_RUNTIME.txt`. An ARM64 machine uses a pixi checkout rather than that tarball.

## Devices

Device strings are `auto`, `cpu`, `nvidia`, and `amd`. Flags: `-device` on `MojoFq2bamMeth` and `MojoGiraffe`. Environment: `METHYLGRAPHER_ALIGN_DEVICE` (linear default) and `METHYLGRAPHER_GIRAFFE_DEVICE` (graph seed path).

`gpu-common/src/gpu_kernels.mojo` labels kernels as follows.

| Request | Label | API passed to `DeviceContext` |
|---------|-------|-------------------------------|
| `nvidia` or `cuda` | `nvidia:sm_90` | `cuda` |
| `amd`, `hip`, or `rocm` | `amdgpu:gfx942` | `hip` |
| anything else, including `cpu` | `cpu` | `cpu` |

For AMD, a non-empty `METHYLGRAPHER_AMDGPU_ARCH` replaces `gfx942` (`amdgpu:` concatenated with that value).

`auto` (`gpu-common/src/gpu_device.mojo`) probes CUDA `DeviceContext`, then HIP `DeviceContext`, then `nvidia-smi -L`, then `rocm-smi --showproductname`, then `rocminfo`, and otherwise selects CPU.

`METHYLGRAPHER_GPU_REQUIRE` empty or `1` fails the NVIDIA/AMD path when `DeviceContext` cannot be created. `0` allows a host seed extract. The value `1`, `true`, `yes`, or `on` also refuses the linear BWA fallback.

Drivers older than 580 need `MODULAR_NVPTX_COMPILER_PATH` pointing at `ptxas` before a CUDA `DeviceContext` is created. The jammy launcher searches `$ROOT/cuda/bin/ptxas`, `/usr/local/cuda/bin/ptxas`, and `/usr/bin/ptxas` when that variable is unset.

## Linear engines

`MojoFq2bamMeth` has two independent switches.

`METHYLGRAPHER_LINEAR_MAPPER` (`fq2bam-meth/python/fq2bam_meth.py`):

| Value | Behavior |
|-------|----------|
| empty, `auto`, or `mojo` | Mojo linear mapper, including when `-device cpu` |
| `bwa` | BWA-MEM on the converted reference |

`METHYLGRAPHER_LINEAR_ENGINE`, used when the mapper is `mojo`:

| Value | Module | Index |
|-------|--------|-------|
| empty, `fm`, `bwa-mem`, `bwamem`, `default` | `fq2bam-meth/src/linear_gpu_fm.mojo` | BWA `.bwt`, `.sa`, `.pac` on the C→T FASTA |
| `parity`, `science`, `kmer`, `k-mer` | `fq2bam-meth/src/linear_gpu_locate.mojo` | Dense k-mer pack (`kmers.bin`, `offsets.bin`, `postings.bin`, `meta.json`) |
| `speed`, `fast` | `fq2bam-meth/src/linear_gpu_speed.mojo` | Same dense pack |

The `fm` engine writes a BGZF BAM that is already coordinate-sorted and duplicate-marked. The other engines stream SAM into `samtools`. Any other string raises `RuntimeError`.

## Graph engines

`Align` selects a mapper with `-align_engine` or `METHYLGRAPHER_ALIGN_ENGINE`. The default when both are unset is `cpu_vg`.

| Value | Also accepted | Mapper |
|-------|---------------|--------|
| `cpu_vg` | `cpu`, `vg` | `vg giraffe -o gaf -M 2` with named coordinates |
| `mojo_giraffe` | `mojo` | Mojo Giraffe. GBZ quartet when those files exist, otherwise GFA |
| `gpu_giraffe` | `gpu`, `gh200` | Mojo GBZ/GFA. `METHYLGRAPHER_GPU_GIRAFFE_FALLBACK` is `mojo` (default), `vg`, or `error` |

`GOLIATH_ALIGN_GIRAFFE_READY` defaults to on. `0`, `false`, `no`, `off`, or `vg` keeps `align_engine=gpu_giraffe` but selects the `vg` path (`mojo_giraffe_ready` in `giraffe/python/quartet_map.py`). `MOJO_ALIGN_GIRAFFE_READY` and `METHYLGRAPHER_MOJO_GIRAFFE_READY` are the deprecated names of the same variable.

`MojoGiraffe` is its own command. It does not consult `-align_engine`. It takes `-device auto|cpu|nvidia|amd` and writes the GAF you name with `-out_gaf`.

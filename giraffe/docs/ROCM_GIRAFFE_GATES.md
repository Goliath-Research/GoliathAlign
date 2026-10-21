# AMD Mojo Giraffe device

> **Repository:** GoliathAlign (formerly `mojo-align`). `GOLIATH_ALIGN_*` is the environment family. `MOJO_ALIGN_*` and `/opt/mojo-align` remain one-cycle aliases of `GOLIATH_ALIGN_*` and `/opt/goliath-align`.

`MojoGiraffe -device amd` uses the same `DeviceContext` sources as `-device nvidia` (`gpu-common` and `giraffe_gpu_map_kernels`). The kernel label is `amdgpu:gfx942` unless `METHYLGRAPHER_AMDGPU_ARCH` is set, in which case the label is `amdgpu:` plus that value. The API string is `hip`.

```bash
METHYLGRAPHER_ENGINE=mojo \
METHYLGRAPHER_TARGET_ACCELERATOR=amdgpu:gfx942 \
  ./bin/methylGrapher MojoGiraffe \
  -gfa graph.gfa -fq1 R1.fastq -out_gaf out.gaf -device amd
```

The GBZ stream map prints `target=` from `kernel_target_label`. On AMD that string is `amdgpu:gfx942` or `amdgpu:$METHYLGRAPHER_AMDGPU_ARCH`.

## Host tools the probe uses

- `rocm-smi --showproductname` and, if that fails, `rocminfo`, when `-device auto` is choosing a device
- A HIP `DeviceContext`. `METHYLGRAPHER_GPU_REQUIRE` empty or `1` fails the run when that context cannot be created

## Measurement record

| Gate | How | Status |
|------|-----|--------|
| Device probe | MojoGiraffe `-device amd` prints `target=amdgpu:gfx942` (or `amdgpu:` plus `METHYLGRAPHER_AMDGPU_ARCH`) | operator, on a machine with HIP |
| Toy GBZ PE | Same golden as `BENCHMARK_GIRAFFE.md` | operator |
| Full-depth dual-map wall | Operator timing on an Instinct GPU | **PENDING** |

## Selecting another mapper

```bash
export METHYLGRAPHER_ALIGN_ENGINE=cpu_vg
# or
export METHYLGRAPHER_GPU_GIRAFFE_FALLBACK=vg
# or
export GOLIATH_ALIGN_GIRAFFE_READY=0
export METHYLGRAPHER_GIRAFFE_DEVICE=cpu
```

`METHYLGRAPHER_MCALL_ENGINE=python` runs `Align` / `MethylCall` through `engine.cli`.

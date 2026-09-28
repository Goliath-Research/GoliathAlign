# ROCm Mojo Giraffe gates (AMD Instinct)

> **Repository:** GoliathAlign (formerly `mojo-align`). `GOLIATH_ALIGN_*` is the environment family. `MOJO_ALIGN_*` and `/opt/mojo-align` remain one-cycle aliases of `GOLIATH_ALIGN_*` and `/opt/goliath-align`.

Companion to the GoliathOmics multi-GPU align notes. Build from the GoliathOmics checkout (sibling of this repo).

## Image

```bash
# From GoliathOmics (stages this repo into workers/docker/methylgrapher)
GOLIATH_ALIGN_GPU_VARIANT=rocm \
GOLIATH_ALIGN_IMAGE_TAG=1.70-mojo-rocm \
  bash scripts/build_goliath_align_image.sh

# CUDA twin (Lambda / NGC hosts)
GOLIATH_ALIGN_GPU_VARIANT=cuda \
GOLIATH_ALIGN_IMAGE_TAG=1.70-mojo-cuda \
  bash scripts/build_goliath_align_image.sh
```

Alias `:1.70-mojo` may point at the CUDA build for backward compatibility.

Site pin:

```json
"actionConfig": {
  "methylgrapher_wgbs": {
    "engine": "mojo",
    "align_engine": "gpu_giraffe",
    "giraffe_device": "auto",
    "align_device": "auto",
    "image": "goliath/methylgrapher:1.70-mojo-rocm"
  }
}
```

## Host prerequisites

- ROCm driver + `rocm-smi`
- Container runtime with AMD GPU device access (ROCm container toolkit / `--device=/dev/kfd --device=/dev/dri`)
- Shared NFS: genomes, `/work/cache/mojo_segments`, sample dirs

## Measurement gates

| Gate | How | Status |
|------|-----|--------|
| Device probe | `docker run --rm … methylGrapher MojoGiraffe … -device amd` logs `kernel_target=amdgpu` (or `amdgpu:gfx942`) | image smoke |
| Toy GBZ PE | Same golden as NVIDIA (`docs/BENCHMARK_GIRAFFE.md`) | operator |
| Known-mapped Buffy C2T | 13/13 style fixture | operator |
| Full Buffy wall | ≤ target vs GH200 baseline (~2 h goal) | **PENDING** MI300X bakeoff |
| Parity | DS20M / subset `graph.methyl` vs NVIDIA Mojo (and optional `cpu_vg`) | **PENDING** |

Same Mojo DeviceContext sources as NVIDIA (`gpu-common` + `giraffe_gpu_map_kernels`). No HIP rewrite. Clara remains NVIDIA-only (explicit linear/stock path).

**Build note (2026-08-14):** `:1.70-mojo-rocm` image builds from GoliathAlign on GH200 hosts; `smoke_64k.sh` CUDA/cupy probe is skipped/irrelevant on ROCm — use `-device amd` on MI300X for the DeviceContext gate. Instinct Buffy wall remains **PENDING** bakeoff.

## Rollback

`giraffe_device=cpu` or `gpu_giraffe_fallback=vg` or stock `:1.70` + `engine=python`.

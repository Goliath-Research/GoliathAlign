# numeric

> **Repository:** GoliathAlign (formerly `mojo-align`). `GOLIATH_ALIGN_*` is the environment family. `MOJO_ALIGN_*` and `/opt/mojo-align` remain one-cycle aliases of `GOLIATH_ALIGN_*` and `/opt/goliath-align`.

Portable DeviceContext kernels for GoliathOmics post-align science (centroid
stream first). Device select and HBM preflight come from `gpu-common/`.

| Module | Role |
|--------|------|
| `src/centroid_kernels.mojo` | DeviceContext scatter-add, bin histogram, device probe |
| `python/centroid_kernels.py` | Host reference + Python API used by methylutils |

Include path: `-I gpu-common/src -I numeric/src`.

`gpu_backend=mojo` in GoliathOmics loads `python/centroid_kernels.py` from
`GOLIATH_ALIGN_ROOT` (or `/opt/goliath-align` after `stage_flat_image_tree.sh`).

Device probe (DeviceContext via gpu-common):

```bash
pixi run numeric-probe
```

# numeric

> **Repository:** GoliathAlign (formerly `mojo-align`). `GOLIATH_ALIGN_*` is the environment family. `MOJO_ALIGN_*` and `/opt/mojo-align` remain one-cycle aliases of `GOLIATH_ALIGN_*` and `/opt/goliath-align`.

DeviceContext kernels for a centroid stream: scatter-add into an accumulator, bin a histogram, and merge centroid positions. Device selection and HBM preflight come from `gpu-common/`.

| Module | Role |
|--------|------|
| `src/centroid_kernels.mojo` | DeviceContext scatter-add, bin histogram, device probe |
| `python/centroid_kernels.py` | Host reference that matches those kernels, plus `probe_device` |

Include path: `-I gpu-common/src -I numeric/src`.

`numeric/python` on `PYTHONPATH` makes `import centroid_kernels` load the host reference. `scripts/stage_flat_image_tree.sh` copies that file to `engine/centroid_kernels.py` in the flat tree.

Device probe (DeviceContext via gpu-common):

```bash
pixi run numeric-probe
```

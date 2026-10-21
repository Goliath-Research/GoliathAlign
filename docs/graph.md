# Graph alignment

Graph commands map bisulfite reads onto a genome graph and call methylation from GAF. They do not produce the linear BAM that `MojoFq2bamMeth` produces. NVIDIA Clara Parabricks `pbrun giraffe` writes BAM only (no GAF, no named coordinates). The probe recorded in `giraffe/docs/PHASE0_GH200_ALIGN.md` is why graph alignment here goes through `vg giraffe` or `MojoGiraffe`.

## PrepareGenome

`PrepareGenome` reads a GFA and writes a lambda-injected graph, fully converted C→T and G→A GFAs, a CpG table, a node-replacement JSON file, and `vg autoindex -w giraffe` indexes.

| Flag | Role |
|------|------|
| `-gfa` | Input GFA |
| `-prefix` | Output prefix |
| `-lp` | Optional lambda phage FASTA. Omitted: the report says conversion rate cannot be estimated |
| `-trim` | `Y` / `yes` / `true` trims SNV bubbles while converting. Default is off |
| `-t` / `-thread` | Threads passed to `vg autoindex`. Default 1 |
| `-vg_path` | `vg` binary. Default `vg`, or `config.ini` key `default.vg_path` when that file loads |

Files written beside `-prefix`:

| File | Role |
|------|------|
| `<prefix>.prepare.genome.report.txt` | `vg` version check and index logs |
| `<prefix>.wl.gfa` | Graph plus lambda segment |
| `<prefix>.wl.C2T.gfa` | Every C converted to T |
| `<prefix>.wl.G2A.gfa` | Every G converted to A |
| `<prefix>.cpg.tsv` | CpG sites on the original graph |
| `<prefix>.wl.node.replacement.json` | C→T and G→A replacement node ids |
| `<prefix>.wl.C2T.*` and `<prefix>.wl.G2A.*` | `vg` Giraffe index files (`autoindex` prefix is the GFA path without `.gfa`) |

## Align

`Align` converts `-fq1` and optional `-fq2` into the work directory, maps them, and leaves `alignment.gaf` there.

| Flag | Default | Role |
|------|---------|------|
| `-index_prefix` | required | Prefix from `PrepareGenome` (`<prefix>.wl.C2T` and `<prefix>.wl.G2A` are the graph indexes) |
| `-fq1` | required | Read 1 FASTQ |
| `-fq2` | omitted | Single-end when omitted |
| `-work_dir` | `./` | Converted FASTQs and `alignment.gaf` |
| `-t` / `-thread` | 1 | Threads |
| `-directional` | `Y` | `Y`: read 1 is C→T and read 2 is G→A. `N`: each read is mapped as both conversions |
| `-compress` | `N` | `Y` gzip-compresses the converted FASTQs |
| `-align_engine` | `METHYLGRAPHER_ALIGN_ENGINE` or `cpu_vg` | `cpu_vg`, `mojo_giraffe`, or `gpu_giraffe` |
| `-vg_path` | `vg` | Used by `cpu_vg` and by a `vg` fallback |

Directional conversion writes `<work_dir>/C2T.R1.fastq` and `<work_dir>/G2A.R2.fastq` (plus `.gz` when `-compress Y`). The mapper reads those files. `Align` then deletes the converted FASTQs and any `alignment.<n>.gaf` shards. What remains is `<work_dir>/alignment.gaf` and a `<work_dir>/report.txt` log of the conversion.

`cpu_vg` shards aligner output and merges it into `<work_dir>/alignment.gaf`. `mojo_giraffe` and `gpu_giraffe` write `<work_dir>/alignment.gaf` directly. A pair-count mismatch between the two converted FASTQs raises `RuntimeError` before the GPU map.

`METHYLGRAPHER_DUAL_GRAPH_PARALLEL` defaults off, so the C→T graph and the G→A graph run one after the other. `1` or `auto` with two or more visible GPUs pins one graph per GPU (`CUDA_VISIBLE_DEVICES` / `HIP_VISIBLE_DEVICES`).

## MojoGiraffe

Native command on the Mojo CLI (`METHYLGRAPHER_ENGINE=mojo`, or the jammy launcher's default). Two input shapes:

```text
methylGrapher MojoGiraffe -gfa <gfa> -fq1 <fastq> -out_gaf <path>
    [-fq2 <fastq>] [-device auto|cpu|nvidia|amd] [-k <kmer>]

methylGrapher MojoGiraffe -gbz <gbz> -dist <dist> -min <min>
    [-zipcodes <zip>] -fq1 <fastq> [-fq2 <fastq>] -out_gaf <path>
    [-device auto|cpu|nvidia|amd] [-k <kmer>]
```

`-out_sam <path> -segment_offsets <dir>` switches emission to linear SAM (`GOLIATH_ALIGN_EMIT=sam`). The GAF path is the one `MethylCall` reads.

The GBZ stream map (`giraffe/src/giraffe_stream_map.mojo`) prints `target=` from `kernel_target_label` (`nvidia:sm_90` or `amdgpu:gfx942` unless `METHYLGRAPHER_AMDGPU_ARCH` is set). AMD measurement notes are in `giraffe/docs/ROCM_GIRAFFE_GATES.md`.

## MethylCall, MergeCpG, ConversionRate

`MethylCall` opens `<work_dir>/alignment.gaf` (or `alignment.gaf.gz` / `alignment.gaf.gzip`) and writes `<work_dir>/graph.methyl`.

| Flag | Default |
|------|---------|
| `-work_dir` | `./` |
| `-index_prefix` | required |
| `-minimum_identity` | 20 |
| `-minimum_mapq` | 0 |
| `-discard_multimapped` | `Y` |
| `-cg_only` | `Y` |
| `-genotyping_cytosine` | `N` (writes `genotype.info.txt` when `Y`) |
| `-t` | 1 |
| `-batch_size` | 4096 |

The GFA worker count is fixed at 1.

`MergeCpG` reads `<index_prefix>.cpg.tsv`, `<work_dir>/graph.methyl`, and `<work_dir>/genotype.info.txt`, and writes `<work_dir>/graph.cpg.tsv`.

`ConversionRate` prints the estimate from `estimate_conversion_rate_print` and writes no file of its own. `PrepareGenome` has to have seen `-lp`, and `MethylCall` has to have run, for that estimate to mean a measured rate.

`Main` runs `Align` and then `MethylCall` with the flags above.

On the Mojo CLI, `METHYLGRAPHER_MCALL_ENGINE=python` sends `Align`, `MethylCall`, `MergeCpG`, and `ConversionRate` to `engine.cli`. `PrepareGenome` and `Main` always go to `engine.cli`.

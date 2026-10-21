# Command line

```text
methylGrapher <command> [arguments]
```

The Python engine (`engine/cli.py`, methylGrapher 0.2.0 plus the Mojo cutover) accepts:

| Command | What it does |
|---------|----------------|
| `help`, `-h`, `--help` | Prints the banner, version `0.2.0`, and command text |
| `PrepareGenome` | Convert and index a GFA. [Graph alignment](graph.md) |
| `Align` | FASTQ → `<work_dir>/alignment.gaf` |
| `MojoFq2bamMeth` | FASTQ pair + FASTA → BAM and QC JSON. [Linear alignment](linear.md) |
| `MethylCall` | `<work_dir>/alignment.gaf` → `<work_dir>/graph.methyl` |
| `MergeCpG` | `graph.methyl` → `<work_dir>/graph.cpg.tsv` |
| `ConversionRate` | Print a conversion-rate estimate |
| `Main` | `Align` then `MethylCall` |
| `vg_check` | Run `vg version` (or `-vg_path`) |
| `MergeGAF` | Accepted, then returns 0. The 0.2.0 CLI has no merge implementation, and this port keeps that |

An unknown command prints `Unknown command:` and exits 1. An argument that does not start with `-` prints `Unknown argument:` and exits 1. `MojoFq2bamMeth` is the exception: its remaining arguments are parsed by argparse (`-fq1`, `-fq2`, …).

The Mojo CLI (`methylgrapher/src/main.mojo`, version string `0.1.0-mojo`) adds `MojoGiraffe` and handles `help`, `vg_check`, `Align`, `MethylCall`, `MergeCpG`, and `ConversionRate` in Mojo unless `METHYLGRAPHER_MCALL_ENGINE=python`. `PrepareGenome`, `Main`, and `MergeGAF` are forwarded to `engine.cli`. `MojoFq2bamMeth` is forwarded there as well; the map itself is `linear_mapper.mojo`.

Flags are `-key value` (one dash, even for multi-letter names). `-t` and `-thread` both set the thread count on the Python engine.

## help

`./bin/methylGrapher help` prints the Python help. `METHYLGRAPHER_ENGINE=mojo ./bin/methylGrapher help` prints the Mojo help, including `MojoGiraffe`. The jammy `bin/methylGrapher help` prints the Mojo help unless `METHYLGRAPHER_MCALL_ENGINE=python`.

## MojoFq2bamMeth

```text
methylGrapher MojoFq2bamMeth \
  -fq1 R1.fastq.gz -fq2 R2.fastq.gz -ref ref.fa \
  -out_bam sample.bam -out_qc_dir qc -sample_id SAMPLE \
  [-t 16] [-device auto|cpu|nvidia|amd] [-work_dir DIR] \
  [-k 15] [-cache_dir DIR]
```

Required flags are `-fq1`, `-fq2`, `-ref`, `-out_bam`, `-out_qc_dir`, and `-sample_id`. Outputs are listed in [Linear alignment](linear.md).

## Align

```text
methylGrapher Align \
  -index_prefix PREFIX -fq1 reads_1.fastq -work_dir DIR \
  [-fq2 reads_2.fastq] [-t 1] [-directional Y] [-compress N] \
  [-align_engine cpu_vg|gpu_giraffe|mojo_giraffe]
```

Output file: `<work_dir>/alignment.gaf`. The converted FASTQs and per-shard GAF files are removed before the command returns. `<work_dir>/report.txt` keeps the conversion log.

## MojoGiraffe

Available when the process is `main.mojo` (checkout with `METHYLGRAPHER_ENGINE=mojo`, or the jammy launcher).

```text
methylGrapher MojoGiraffe -gfa graph.gfa -fq1 R1.fastq -out_gaf out.gaf \
  [-fq2 R2.fastq] [-device auto|cpu|nvidia|amd] [-k K]

methylGrapher MojoGiraffe -gbz graph.gbz -dist graph.dist -min graph.min \
  [-zipcodes graph.zipcodes] -fq1 R1.fastq [-fq2 R2.fastq] -out_gaf out.gaf \
  [-device auto|cpu|nvidia|amd] [-k K]
```

`-out_sam PATH -segment_offsets DIR` writes linear SAM instead of relying on a later BAM conversion.

## MethylCall

```text
methylGrapher MethylCall -work_dir DIR -index_prefix PREFIX \
  [-minimum_identity 20] [-minimum_mapq 0] \
  [-discard_multimapped Y] [-cg_only Y] [-genotyping_cytosine N] \
  [-t 1] [-batch_size 4096]
```

Input: `<work_dir>/alignment.gaf` (or `.gz` / `.gzip`). Output: `<work_dir>/graph.methyl`. With `-genotyping_cytosine Y`, also `<work_dir>/genotype.info.txt`.

## PrepareGenome, MergeCpG, ConversionRate, Main, vg_check

```text
methylGrapher PrepareGenome -gfa in.gfa -prefix PREFIX [-lp lambda.fa] [-trim N] [-t 1]

methylGrapher MergeCpG -index_prefix PREFIX -work_dir DIR

methylGrapher ConversionRate -index_prefix PREFIX -work_dir DIR

methylGrapher Main -index_prefix PREFIX -fq1 R1.fastq -work_dir DIR \
  [-fq2 R2.fastq] [-t 1] [-directional Y] [-compress N] \
  [-align_engine cpu_vg] [MethylCall flags...]

methylGrapher vg_check [-vg_path vg]
```

`PrepareGenome` outputs are listed in [Graph alignment](graph.md). `MergeCpG` writes `<work_dir>/graph.cpg.tsv`. `ConversionRate` prints to stdout. `vg_check` prints the `vg version` output. The Python checker looks for `vg version v` in that output. The Mojo checker prints the combined stdout and stderr and then `Success: vg binary seems to be fine` or `Error: Cannot find vg version`.

## Flat-tree launcher

`scripts/stage_flat_image_tree.sh` writes `bin/methylGrapher` that `cd`s to the flat root, sets `PYTHONPATH` to `scripts` and that root, and runs `pixi run python -m engine.cli`. `METHYLGRAPHER_ENGINE=mojo` runs `pixi run mojo -I src src/main.mojo` with no `--target-accelerator` flag. The checkout launcher and the jammy launcher are the ones described in [Install](install.md).

# Linear alignment

`MojoFq2bamMeth` is a portable linear whole-genome bisulfite aligner in the method class of bwa-meth and NVIDIA Clara Parabricks `fq2bam_meth`. It is a separate command from graph `Align`. Graph alignment writes GAF; this command writes BAM.

Clara Parabricks exposes the same method as `pbrun fq2bam_meth` (the bisulfite form of `fq2bam`). GoliathAlign does not shell out to `pbrun` during a normal map. The parity harness can run `pbrun` beside `MojoFq2bamMeth` so the two BAMs can be compared.

## Conversion

Directional bisulfite, which is the default and the only mode this command implements:

| Sequence | Conversion |
|----------|------------|
| Read 1 | C→T (`-bs_r1 C2T` inside the Mojo mapper) |
| Read 2 | G→A (`-bs_r2 G2A`) |
| Reference | C→T, both strands when a bwa-meth FASTA is present |

Reference resolution (`resolve_c2t_fasta`):

1. `${REF}.bwameth.c2t` when that file exists. This is the bwa-meth / Clara index source: forward contigs converted C→T and reverse contigs converted G→A (`f*` and `r*` names).
2. Else `${REF}.C2T.fa` when that file exists.
3. Else the command writes a single-strand C→T FASTA under `-work_dir` (or returns the bwa-meth sibling path when `REF` is under `/genomes/` or `/work/genomes/` and the parent directory exists).

On the Mojo mapper the read conversion runs inside the mapper, so the original FASTQ paths are passed through. The BWA mapper rewrites `C2T.R1.fastq.gz` and `G2A.R2.fastq.gz` under the work directory first.

Mapping only the single-strand C→T reference drops the reads that belong on the G→A strand. The dual-strand bwa-meth FASTA is the file the `fm` engine and Clara both index.

## Engines

Default mapper: Mojo. Default Mojo engine: `fm`.

`fm` memory-maps the BWA FM-index (`.bwt`, `.sa`, `.pac`, `.ann`) and seeds with SMEMs. `parity` and `speed` use a dense k-mer pack. The pack directory is `-cache_dir`, or `METHYLGRAPHER_LINEAR_CACHE_DIR`, or `${bwameth.c2t}.mojo_linear_k${k}`, or `${REF}.mojo_linear_k${k}`, or `work/mojo_linear_index`. `k` comes from `-k` or `METHYLGRAPHER_LINEAR_K` (default 15). `METHYLGRAPHER_LINEAR_CACHE_BUILD=1` (the default) builds a missing pack under a lock file. `0` fails if the pack is missing. The `fm` engine does not build that pack.

Knobs for seed length, sort tiles, and BGZF threads are listed in `fq2bam-meth/docs/LINEAR_ENGINES.md`.

## Inputs

`fq2bam_meth.main` requires all of the following:

| Flag | Meaning |
|------|---------|
| `-fq1` | Read 1 FASTQ, plain or `.gz` |
| `-fq2` | Read 2 FASTQ, plain or `.gz` |
| `-ref` | Reference FASTA |
| `-out_bam` | Output BAM path |
| `-out_qc_dir` | Directory for QC JSON |
| `-sample_id` | Sample id written into the metrics JSON and used as the JSON file name |

Optional:

| Flag | Default |
|------|---------|
| `-t` | `METHYLGRAPHER_BWA_THREADS` or 16. Threads for BWA and for `samtools sort` / `markdup`. The Mojo `fm` mapper does not use this as a map-thread count. |
| `-device` | `METHYLGRAPHER_ALIGN_DEVICE` or `auto` |
| `-work_dir` | A new temporary directory `mojo_fq2bam_*` |
| `-k` | `METHYLGRAPHER_LINEAR_K` or 15 |
| `-cache_dir` | Resolved as above |

The command returns an error if `samtools` is not on `PATH`.

## Outputs

| File | When |
|------|------|
| The `-out_bam` path | Always, when the run finishes. `fm` moves the mapper's coordinate-sorted, duplicate-marked BAM into place and runs `samtools index`. Other mappers run `samtools fixmate -m`, `sort -l 1`, and, unless `METHYLGRAPHER_LINEAR_MARKDUP` is `0` / `false` / `no` / `off`, `markdup`, then `index`. |
| `<sample_id>.json` next to the BAM | Parabricks-shaped metrics. `engine` is `mojo_fq2bam_meth`. `mapper` is `mojo`, `bwa`, or `bwa_fallback`. `metrics_source` is `samtools+placeholders`. |
| `<out_qc_dir>/alignment_summary.json` | Parsed `flagstat`, `samtools stats` SN fields, and `mapper` |
| `<out_qc_dir>/<sample_id>.json` | Copy of the metrics file |
| `<work_dir>/mojo_fq2bam_meth.log` | Every command line and device probe |

`METHYLGRAPHER_WRITE_METH_TAGS` set to `1`, `true`, `yes`, or `on` rewrites the BAM with `XM:Z` / `XG:Z` after the index step (`fq2bam-meth/python/meth_tags.py`).

The metrics JSON includes `quality_yield`, a 100-cycle `mean_quality_by_cycle` filled from the samtools average quality, `insert_size_metrics`, `alignment_summary.mapped_rate`, and placeholder `gc_bias_summary` / `pre_adapter_summaries` fields. Those placeholders are listed in `placeholder_fields`.

Stdout on success is `MojoFq2bamMeth OK` plus the BAM path.

## Clara concordance harness

`fq2bam-meth/scripts/parity_linear_parabricks_vs_mojo.sh` runs this command and, unless `--skip-clara` is set, Clara `fq2bam_meth`. Clara uses `pbrun` on `PATH` when it is present, otherwise Docker image `METHYL_PARABRICKS_IMAGE` (default `nvcr.io/nvidia/clara/clara-parabricks:4.5.1-1`).

The script's default sample directory is `/work/samples/parabricks_sample`. It writes:

```text
<sample-dir>/align.linear.parabricks/<sample-id>.bam
<sample-dir>/align.linear.mojo/<sample-id>.bam
<sample-dir>/linear_parity_report.json
```

`fq2bam-meth/scripts/compare_linear_align_parity.py` scores the two BAMs. Defaults, also the script's defaults: absolute mapped-rate delta ≤ 0.02, Spearman of primary-contig mapped counts (chromosomes 1–22, X, Y, MT) ≥ 0.95.

`fq2bam-meth/scripts/compare_gatk_picard_metrics.py` runs GATK `ValidateSamFile` and Picard-style alignment and insert-size metrics when `gatk` or `GATK_JAR` / `PICARD_JAR` is available.

Fetch of the public Parabricks tutorial bundle is `fq2bam-meth/scripts/fetch_parabricks_sample.sh`. Building a missing bwa-meth index is `fq2bam-meth/scripts/ensure_bwameth_index.sh`. Building a missing Mojo k-mer pack is `fq2bam-meth/scripts/ensure_mojo_linear_index.sh`.

## Toy pair

From the repository root, with `samtools` on `PATH`:

```bash
./bin/methylGrapher MojoFq2bamMeth \
  -fq1 fq2bam-meth/tests/data/fq2bam_fixture/R1.fastq \
  -fq2 fq2bam-meth/tests/data/fq2bam_fixture/R2.fastq \
  -ref fq2bam-meth/tests/data/fq2bam_fixture/ref.fa \
  -out_bam /tmp/toy.bam \
  -out_qc_dir /tmp/toy_qc \
  -sample_id toy \
  -device cpu -k 8 -t 2
```

`fq2bam-meth/scripts/run_toy_fq2bam_meth.sh` and `benchmark_fq2bam_meth.sh` look for `bin/methylGrapher` in the parent of `scripts/`. That layout is what `scripts/stage_flat_image_tree.sh` produces. In this checkout the parent of `fq2bam-meth/scripts/` has no `bin/`, so use the command above.

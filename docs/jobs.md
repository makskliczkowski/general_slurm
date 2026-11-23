# Run jobs

## Single job

```bash
gs run --time=04:00:00 --mem=16G --cpus-per-task=4 --print -- ./build/sim inputs/a.cfg --steps 100
gs run --cpu --time=01:00:00 -- bash scripts/step.sh inputs/a.cfg
gs run --time=04:00:00 -- '{GS_PYTHON}' scripts/run.py inputs/a.cfg
gs run --time=04:00:00 jobs/my_job.slurm inputs/a.cfg        # an existing .slurm script
```

`gs run` loads `GS_MODULES` (or builds `GS_VENV`), adds the placement, makes the log folder, prints the banner and records the line in `submissions.tsv`.

For a script with declared arguments, a `--print` preview and a `GS_DATA` folder, use a template (`gs new job|array|launcher|python PATH`). A job script sources `lib/gs.sh`, declares its arguments, prints the banner, prepares the environment and runs the program:

```bash
source "${GS_HOME:?set GS_HOME to the general_slurm folder}/lib/gs.sh"
gs_positional INPUT "the input file"
gs_option --steps STEPS 100 "number of steps"
gs_flag --print PRINT "show the plan, compute nothing"
gs_parse "$@"
gs_path GS_DATA "the root of the result folders"
OUT="${GS_DATA}/$(basename "${INPUT%.*}")"
gs_frame "$@"
gs_job
gs_data "${OUT}"
gs_setup_env
./build/sim "${INPUT}" --steps "${STEPS}" --out "${OUT}"
```

`gs check SCRIPT...` verifies the header (`# usage:`, `# example:`), `set -euo pipefail`, `bash -n` and `shellcheck`. A launcher calls `gs_placement [--cpu]`, `gs_logs TAG` and `gs_sbatch PRINT [K=V...] -- ARGS...`.

## Array with one table row per task

One run per line in `runs.txt` (`#` starts a comment). `gs new array jobs/sweep.slurm` writes the script, and `gs_row` returns the row of `GS_TASK`.

```text
# name      size   seed
case_a      32     1
case_b      64     2
```

```bash
GS_TASK=0 bash jobs/sweep.slurm runs.txt            # test one row locally
sbatch --array=0-1 --time=06:00:00 --partition="$GS_PARTITION" --gres="$GS_GRES" jobs/sweep.slurm runs.txt
```

## Sharded array that requeues itself

`gs submit` runs `GS_COMMAND` over the configs, each task with its share (`--shard k/n`). Unknown `--option=value` words go to `sbatch`. `--cpu` selects `GS_CPU_PARTITION`, and `--command "..."` replaces `GS_COMMAND` for one call. The program side is in [library](library.md).

```bash
gs submit runs/a.toml runs/b.toml --tasks 4 --max-running 2 --time=12:00:00 --mem=16G --print
```

## Experiment of several packed arrays

A run folder `runs/<name>/` holds the configs and a table `arrays.txt`. Each line is one array.

`CONFIG LABEL... RUNS HOURS [KEY=VALUE...] [request]`

```text
# CONFIG   LABEL    RUNS  HOURS  OPTIONS
base       small    24    1.5    cpus=4 mem=16G
base       large    12    6.0    cpus=8 mem=32G
ablation   large    8     6.0    mem=32G request
```

Packing rules:

1. A run takes `GS_MARGIN * HOURS`.
2. Runs share a task up to `GS_TARGET_HOURS`. A longer run gets a task of its own.
3. The time limit is the task hours rounded up plus 2 hours, capped at `GS_MAX_HOURS`.
4. `KEY=VALUE` becomes `--KEY=VALUE` for `sbatch` (`cpus=` becomes `--cpus-per-task=`).
5. A line that ends with `request` runs only when its `CONFIG` is named on the command line.

```bash
gs table runs/exp1 small --print       # preview the arrays that match "small"
gs table runs/exp1 base                # submit the non-request arrays that match "base"
gs status runs/exp1 --since now-2days  # task counts by job name and sacct state
gs rerun 123456 --time=24:00:00 --print
```

Every submission through `gs_sbatch` appends the job id, the time and the quoted `sbatch` command to `GS_LOG_ROOT/submissions.tsv`. Run `gs rerun` from the folder where the job was submitted.

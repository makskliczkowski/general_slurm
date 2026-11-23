# Slurm Helpers

Helpers for Slurm job scripts, for any project and any cluster.

A repository keeps its run folders, one `slurm.env` file, and the short scripts specific to it. `general_slurm` handles the rest:

- cluster and project environment profiles selected by login-node host name
- declared script arguments and automatic `--help`
- a uniform log banner and tagged progress lines in bash and Python
- single jobs, row-based job arrays, and sharded arrays that requeue themselves
- packing of experiment tables into arrays
- status summaries and failed-task resubmission

## 1. Install

Clone the repository or add it as a submodule, export `GS_HOME`, add `bin` to `PATH`, and install the Python package when using Python helpers.

```bash
git submodule add <url> deps/general_slurm
export GS_HOME="$PWD/deps/general_slurm"
export PATH="$GS_HOME/bin:$PATH"
python -m pip install -e deps/general_slurm
```

## 2. Cluster and project settings

Settings live at three levels so no repository script names a cluster or user path.

| Level | File | Holds |
| --- | --- | --- |
| cluster | `~/.config/general_slurm/<cluster>.sh` | partitions, GPU request, time limits, modules, log root |
| project | `~/.config/general_slurm/<project>/<cluster>.sh` | per-cluster project paths such as `GS_DATA` and `GS_VENV` |
| repository | `slurm.env` at the repository root | `KEY=VALUE` lines read at run time (`GS_COMMAND`, `GS_VENV`, table args) |

### Shared `~/.bashrc` across clusters

Several clusters can share one home directory and one `~/.bashrc`. `gs env install` adds a marked block to `~/.bashrc` that sources `lib/cluster.sh` and calls `gs_cluster_load`.

`gs_cluster_load` reads `~/.config/general_slurm/hosts` (`PATTERN CLUSTER` per line, glob patterns on the short host name). The first matching pattern wins, so put narrow patterns before wide ones with `--before PATTERN`. It exports `GS_CLUSTER` and sources `<cluster>.sh` plus every `<project>/<cluster>.sh` for that cluster.

Submitted jobs inherit the login shell environment (`sbatch --export=ALL`). Because `GS_CLUSTER` is already set inside the job, compute nodes skip host detection. A host that matches no pattern prints one warning on `stderr` and loads nothing. See `profiles/example.sh` and `profiles/hosts.example` for starter files.

### Configure a cluster and a project

```bash
# 1. Map login-node host names to cluster names (narrow patterns first)
gs env host 'n2login*' clusterA
gs env host 'login*' clusterB

# 2. Set cluster defaults (~/.config/general_slurm/clusterA.sh)
gs env set clusterA GS_PARTITION gpu
gs env set clusterA GS_GRES gpu:a100:1
gs env set clusterA GS_CPU_PARTITION normal
gs env set clusterA GS_MAX_HOURS 48
gs env set clusterA GS_TARGET_HOURS 12
gs env set clusterA GS_MODULES "python/3.12 cuda/12.4"
gs env set clusterA GS_LOG_ROOT /path/to/scratch/logs

# 3. Set per-project paths for that cluster (~/.config/general_slurm/myproject/clusterA.sh)
gs env set clusterA GS_DATA /path/to/scratch/myproject/data --project myproject
gs env set clusterA GS_VENV /path/to/.venvs/myproject --project myproject

# 4. Install the ~/.bashrc loader, inspect active settings, and verify the node
gs env install
gs env show
gs doctor
```

On a cluster that rejects `--requeue`, set `SBATCH_NO_REQUEUE=1` in `<cluster>.sh`. `sbatch` then submits without `--requeue`, and `gs_finish` exits nonzero with a resubmit message when runs remain.

### Settings reference

| Variable | Level | Meaning | Default |
| --- | --- | --- | --- |
| `GS_PARTITION`, `GS_GRES` | cluster | GPU partition and GPU request (`gpu:a100:1` when required) | required for GPU jobs |
| `GS_CPU_PARTITION` | cluster | CPU partition for `--cpu` | required for `--cpu` |
| `GS_MAX_HOURS`, `GS_TARGET_HOURS` | cluster | partition time limit and packing target, in hours | required by `gs table` |
| `GS_MAX_RESTARTS` | cluster | maximum self-requeues of one task | `10` |
| `GS_MODULES` | cluster | space-separated modules loaded by `gs_modules` / `gs_venv` | none |
| `GS_LOG_ROOT` | cluster | root folder for logs and `submissions.tsv` | `logs` |
| `GS_TAG` | cluster | prefix of tagged log lines | `gs:` |
| `SBATCH_NO_REQUEUE` | cluster | disable `--requeue` when set to `1` | unset |
| `GS_DATA` | project | result root used by `templates/job.slurm` and `templates/array.slurm` | required by those templates |
| `GS_COMMAND` | repository | command per config (`{}` is the config, `{NAME}` an env var) | required by `gs submit` |
| `GS_VENV`, `GS_EXTRAS` | repository | virtualenv path and pip extras built by `gs_venv` (`{GS_PYTHON}` uses it) | none |
| `GS_CONFIG_SUFFIX` | repository | suffix appended to `CONFIG` in `gs table` | none |
| `GS_ROW_ARGS` | repository | extra args per `gs table` line (`{N}` is field `N`) | none |
| `GS_SWEEP` | run | shared sweep name printed by `gs_sweep` | none |
| `GS_MARGIN` | run | time multiplier applied to `HOURS` in `gs table` | `1.3` |

`slurm.env` holds `KEY=VALUE` lines and is read without executing shell code. Variables already set in the environment override `slurm.env`.

## 3. Step-by-step workflows

### Step 1: Run a single job (C++, bash, or Python)

Submit any command or `.slurm` script directly with `gs run`. It loads `GS_MODULES` (or builds and activates `GS_VENV`), adds cluster placement, creates the log folder, prints the banner, and records the line in `submissions.tsv`.

```bash
# Preview, then submit any executable (-- separates gs options from your command)
gs run --time=04:00:00 --mem=16G --cpus-per-task=4 --print -- ./build/sim inputs/a.cfg --steps 100
gs run --time=04:00:00 --mem=16G --cpus-per-task=4 -- ./build/sim inputs/a.cfg --steps 100
gs run --cpu --time=01:00:00 -- bash scripts/step.sh inputs/a.cfg
gs run --time=04:00:00 -- '{GS_PYTHON}' scripts/run.py inputs/a.cfg --steps 100

# Or submit an existing .slurm script directly with cluster placement and log tracking
gs run --time=04:00:00 --mem=16G jobs/my_job.slurm inputs/a.cfg
```

For a reusable script with declared arguments, local preview (`--print`), and `GS_DATA` setup, create a job script and a launcher from templates:

```bash
gs new job jobs/my_job.slurm
gs new launcher jobs/submit.sh
```

A job script loads `lib/gs.sh`, declares its arguments, checks required paths, prints the banner, prepares the environment, and runs the target program:

```bash
#!/usr/bin/env bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=04:00:00
# Runs one input with the chosen executable.
# usage: my_job.slurm INPUT [--steps N] [--print]
# example: bash jobs/my_job.slurm inputs/a.cfg --steps 100
set -euo pipefail
source "${GS_HOME:?set GS_HOME to the general_slurm folder}/lib/gs.sh"

# ---- arguments and settings ----
gs_positional INPUT "the input file"
gs_option --steps STEPS 100 "number of steps"
gs_flag --print PRINT "show the plan, compute nothing"
gs_parse "$@"
gs_path GS_DATA "the root of the result folders"
OUT="${GS_DATA}/$(basename "${INPUT%.*}")"

# ---- preview ----
if (( PRINT )); then
    echo "would run ${INPUT} (${STEPS} steps) into ${OUT}"
    gs_print_settings
    exit 0
fi

# ---- banner and environment ----
gs_frame "$@"
gs_job
gs_data "${OUT}"
gs_modules

# ---- run (pick the command for your language) ----
# C++:    ./build/sim "${INPUT}" --steps "${STEPS}" --out "${OUT}"
# Bash:   bash scripts/step.sh "${INPUT}" "${OUT}" "${STEPS}"
# Python: gs_venv "${GS_ROOT:-${PWD}}" "${GS_VENV}" && "${GS_PYTHON}" scripts/run.py "${INPUT}" --steps "${STEPS}" --out "${OUT}"
./build/sim "${INPUT}" --steps "${STEPS}" --out "${OUT}"
```

Preview and test the script locally with the same arguments used on Slurm:

```bash
bash jobs/my_job.slurm inputs/a.cfg --steps 50 --print
bash jobs/my_job.slurm inputs/a.cfg --steps 50
```

In `jobs/submit.sh`, use `gs_placement`, `gs_logs`, and `gs_sbatch` to submit with cluster placement and log tracking:

```bash
gs_placement
LOGS="$(gs_logs single)"
mkdir -p "${LOGS}"
gs_sbatch "${PRINT}" -- --job-name=single --output="${LOGS}/%x_%j.log" \
    --time=04:00:00 --mem=16G --cpus-per-task=4 "${GS_PLACEMENT[@]}" jobs/my_job.slurm inputs/a.cfg --steps 50
```

Pass `--cpu` to `gs_placement --cpu` to select `GS_CPU_PARTITION` and `--gres=none`. Check the script layout with `gs check jobs/my_job.slurm jobs/submit.sh`.

### Step 2: Pack runs into a job array (C++, bash, or Python)

Two patterns cover job arrays depending on whether each task reads one row of a table or a shard of a config list.

#### A. Row-per-task array (`gs_row`, any executable)

Put one run per line in a plain table `runs.txt` (`#` starts a comment):

```text
# name      size   seed
case_a      32     1
case_b      64     1
case_c      64     2
```

Create `jobs/sweep.slurm` with `gs new array jobs/sweep.slurm`. Inside the script, `read -ra ROW <<< "$(gs_row "${TABLE}")"` selects the row matching `GS_TASK`:

- C++: `./build/sim "${ROW[0]}" "${ROW[1]}" "${ROW[2]}"`
- Bash: `bash scripts/step.sh "${ROW[@]}"`
- Python: `gs_venv "${GS_ROOT:-${PWD}}" "${GS_VENV}"` followed by `"${GS_PYTHON}" scripts/run.py "${ROW[@]}"`

Test one row locally, then submit the array:

```bash
GS_TASK=0 bash jobs/sweep.slurm runs.txt
mkdir -p logs
sbatch --array=0-2 --time=06:00:00 --mem=16G --partition="$GS_PARTITION" --gres="$GS_GRES" \
    --output=logs/%x_%A_%a.log jobs/sweep.slurm runs.txt
```

#### B. Sharded array with auto-requeue (`gs submit`)

For a program that accepts `--shard k/n`, put the command in `slurm.env` at the repository root:

```ini
# C++
GS_COMMAND=./build/sim {}

# Bash
GS_COMMAND=bash scripts/step.sh {}

# Python (builds GS_VENV once under a lock and sets GS_PYTHON)
GS_COMMAND={GS_PYTHON} scripts/run.py {}
GS_VENV=/path/to/.venvs/myproject
```

Preview and submit all configs as one array. Any unknown `--option=value` is passed directly to `sbatch`:

```bash
gs submit runs/a.toml runs/b.toml --tasks 4 --max-running 2 --time=12:00:00 --mem=16G --cpus-per-task=4 --print
gs submit runs/a.toml runs/b.toml --tasks 4 --max-running 2 --time=12:00:00 --mem=16G --cpus-per-task=4
```

Pass `--cpu` to target `GS_CPU_PARTITION`. Use `--command "..."` to override `GS_COMMAND` for one call.

### Step 3: Prepare an experiment of multiple packed arrays (`gs table`)

A run folder `runs/<name>/` holds the config files, an `arrays.txt` table, and optional notes (`run.md`). Each non-comment line in `arrays.txt` describes one array:

`CONFIG LABEL... RUNS HOURS [KEY=VALUE...] [request]`

```text
# CONFIG   LABEL    RUNS  HOURS  OPTIONS
base       small    24    1.5    cpus=4 mem=16G
base       large    12    6.0    cpus=8 mem=32G
ablation   large    8     6.0    mem=32G request
```

In `slurm.env`, set `GS_CONFIG_SUFFIX` (such as `.toml`) and `GS_ROW_ARGS` (such as `--tag {2}`, where `{N}` substitutes field `N` of the line).

Packing rules:

1. Each run takes `GS_MARGIN * HOURS` (default `1.3`).
2. Runs share a task up to `GS_TARGET_HOURS`. A longer run gets one task on its own.
3. The wall-time limit is the task hours rounded up plus 2 hours, capped at `GS_MAX_HOURS`.
4. `KEY=VALUE` options become `--KEY=VALUE` for `sbatch` (`cpus=` becomes `--cpus-per-task=`).
5. A line ending with `request` runs only when its `CONFIG` name is listed on the command line.

Preview, submit, inspect status, and rerun failed tasks:

```bash
gs table runs/exp1 small --print          # preview arrays matching "small"
gs table runs/exp1 base                   # submit all non-request arrays matching "base"
gs table runs/exp1 ablation large         # submit the "request" line for "ablation"
gs status runs/exp1 --since now-2days     # count tasks by job name and sacct state
gs rerun 123456 --time=24:00:00 --print   # preview rerun of failed/timed-out array tasks
```

## 4. Commands

Run `gs` with no arguments to list all subcommands, or `gs SUBCOMMAND --help` for flags and defaults.

| Command | Does |
| --- | --- |
| `gs env` | maps login host patterns to clusters, edits `<cluster>.sh` or `<project>/<cluster>.sh`, installs the `~/.bashrc` block, and prints active settings |
| `gs doctor` | checks Slurm binaries, loaded cluster, partitions and GPU types (`sinfo`), `GS_MAX_HOURS`, `slurm.env`, `GS_COMMAND`, and `GS_VENV` |
| `gs new job\|array\|launcher\|python PATH` | copies a template to `PATH` without overwriting existing files |
| `gs check SCRIPT...` | verifies the script header (`# usage:`, `# example:`), `set -euo pipefail`, `bash -n`, and `shellcheck` |
| `gs run [--] CMD [ARG...]` | submits one command via `jobs/run.slurm` or a `.slurm` script directly with cluster placement and `sbatch` options |
| `gs submit CONFIG...` | submits a sharded array via `jobs/shards.slurm` with `GS_PLACEMENT` and `sbatch` options |
| `gs table RUN_FOLDER [WORD...]` | packs `RUN_FOLDER/arrays.txt` into arrays and submits each selected line with `gs submit` |
| `gs status JOBID\|RUN_FOLDER\|PREFIX` | aggregates task counts by job name and state from `sacct` |
| `gs rerun JOBID` | resubmits a failed, timed-out, OOM, or node-failed single job or array tasks using `GS_LOG_ROOT/submissions.tsv` |

Every submission through `gs_sbatch` (`gs submit`, `gs table`, `gs rerun`, and launchers built with `gs_sbatch`) appends `JOBID`, timestamp, and the quoted `sbatch` command to `GS_LOG_ROOT/submissions.tsv`. Run `gs rerun` from the same directory where the job was submitted.

## 5. Script library and Python contract

Source `${GS_HOME}/lib/gs.sh` in bash scripts and import `general_slurm` in Python.

| Need | Bash (`lib/`) | Python (`general_slurm`) |
| --- | --- | --- |
| arguments | `gs_positional`, `gs_variadic`, `gs_option`, `gs_list`, `gs_flag`, `gs_parse "$@"` | `add_arguments(parser)`, `parse_shard` |
| settings | `gs_env`, `gs_need`, `gs_path`, `gs_print_settings` | - |
| log lines | `gs_frame "$@"`, `gs_info`, `gs_data`, `gs_progress`, `gs_checkpoint`, `gs_metric` | `frame`, `info`, `data`, `progress`, `checkpoint`, `metric` |
| job facts | `gs_job` (`GS_JOB_ID`, `GS_TASK`, `GS_TASKS`, `GS_RESTARTS`, `GS_CPUS`), `gs_sweep` | `Job.from_environment()` |
| environment | `gs_modules`, `gs_venv ROOT VENV [EXTRAS]`, `gs_setup_env` (venv if `GS_VENV` is set, else modules) | - |
| requeue & limits | `gs_run_each CONFIG... -- CMD...`, `gs_finish`, `gs_deadline`, `gs_latest DIR` | `shard`, `fits`, `fresh_allocation_fits`, `stop_on_signals`, `held_signals`, `budget_alarm`, `DONE`, `FAILED`, `LEFT` |
| tables | `gs_row TABLE`, `gs_pack TABLE MAX_HOURS TARGET [WORD...]` | `read_table`, `row`, `pack` |
| submission | `gs_placement [--cpu]`, `gs_logs TAG`, `gs_sbatch PRINT [K=V...] -- ARGS...` | - |
| status | - | `append_status(path, fields, columns)` |

### Log format

Both bash and Python emit the same structured lines so one parser can read all logs:

```text
gs: info script=/path/to/script
gs: info git=main@abc1234
== myjob job 12345 task 0 on node01 at 2026-11-23T06:00:00+01:00
== in /path/to/repo: arg1 arg2
gs: data=/path/to/data/run1
gs: progress=1/4
gs: checkpoint=/path/to/data/run1/ckpt.pt
gs: metric loss=0.012
== exit 0 at 2026-11-23T06:10:00+01:00
```

`gs_data` and `general_slurm.data` also append job ID, script path, and date to `job.txt` inside the data folder.

### Auto-requeue contract

`jobs/shards.slurm` passes `--shard k/n` and, when Slurm sets an allocation end time, `--deadline EPOCH --allocation-start EPOCH` to `GS_COMMAND`. A program following the contract (see `templates/job.py`):

1. runs only its slice from `general_slurm.shard`
2. starts a run only when its budget plus ten minutes fits before `--deadline` (`fits`), and exits `1` when even a fresh allocation cannot hold it (`fresh_allocation_fits`)
3. saves a checkpoint on `SIGTERM` (`stop_on_signals`) and protects active writes with `held_signals`
4. exits `0` (`DONE`) when finished, `130` (`LEFT`) when runs remain, and any other nonzero status on failure

Slurm sends `USR1` ten minutes before the time limit (`#SBATCH --signal=B:USR1@600`) and `TERM` on `scancel`. `gs_run_each` forwards both to the program as `TERM`. When runs are left after `USR1` or a self-budget stop, `gs_finish` calls `scontrol requeue` up to `GS_MAX_RESTARTS` times, never after `scancel`.

## 6. Tests and lint

```bash
python -m pytest -q
bin/gs check bin/gs libexec/gs-* jobs/*.slurm templates/*.sh templates/*.slurm
shellcheck -S warning lib/*.sh bin/gs libexec/gs-* jobs/*.slurm templates/*.sh templates/*.slurm
```

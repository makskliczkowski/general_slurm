# Settings

Settings are the variables that tell a job where and how to run. They live at three levels, so that no project names a cluster.

Run the setup commands on a **login node**. A project never names a cluster. It only reads variables, and every one of them can be overridden from outside.

| Level | Where | Holds | Knows about |
| --- | --- | --- | --- |
| cluster | `~/.config/general_slurm/<cluster>.sh` | partitions, GPU request, time limits, modules, log root | the cluster |
| project on a cluster | `~/.config/general_slurm/<project>/<cluster>.sh` | values of one project that differ on this cluster (data folder, virtualenv, a partition) | cluster and project |
| project | `slurm.env` in the repository | `KEY=VALUE` defaults: the command, the virtualenv path, table options | the project only |

All files sit in one folder, `GS_CONFIG_DIR` (default `~/.config/general_slurm`). The cluster files hold `export NAME=value` lines and are written with `gs env set`. The repository file `slurm.env` holds plain `KEY=VALUE` lines. It is read, never run as shell code.

## Precedence

For one variable, highest first:

1. `<project>/<cluster>.sh`, for the project of the current repository.
2. The environment: the cluster file (loaded at login), or a value you export by hand.
3. `slurm.env` of the repository.
4. The built-in default of the library (the Default column below).

So a project can ship defaults in `slurm.env`, a cluster can set its own, and one project can still differ from the cluster on one cluster. File 1 overrides a value you exported by hand. To change a single run, pass an `sbatch` option on the command line.

## The project

`GS_PROJECT` names the project. It is set in `slurm.env`, and by default it is the folder that holds `slurm.env`. Only the file of this project on this cluster is loaded, so projects on one cluster never see each other's values.

## Variables of the project itself

A project can use any variable name, not only `GS_*`. It sets the name in `slurm.env` when the value holds everywhere, or in its file for each cluster when the value differs (`gs env set CLUSTER NAME VALUE --project PROJECT`). The command uses it as `{NAME}` in `GS_COMMAND`, and a program reads it from the environment. The project lists the names that must have a value in `GS_REQUIRED`. `gs doctor` then fails on an empty one and says where to set it, and `gs info` shows each one with the file it comes from. `examples/` has two projects that do this.

## The cluster

`gs env install` adds a marked block to `~/.bashrc`. `GS_BASHRC` replaces that path, and `--print` shows the block and changes nothing. The block sources `lib/cluster.sh` and calls `gs_cluster_load`. That function reads the host map `hosts` (`PATTERN CLUSTER` per line, a glob on the short host name, first match wins), exports `GS_CLUSTER` and sources `<cluster>.sh`. `gs env host` appends a pattern, puts it before another pattern with `--before`, or changes the cluster of an existing pattern; the first pattern that matches wins. Several clusters can share one home folder and one `~/.bashrc`. `sbatch --export=ALL` hands the values to the job. `GS_CLUSTER` is already set there, so compute nodes skip host detection. A host that matches no pattern prints one warning on `stderr` and loads nothing. Starter files are `profiles/example.sh` and `profiles/hosts.example`.

## Reference

The level is where a setting usually belongs. Any setting can also be set at a more specific level.

| Variable | Level | Meaning | Default |
| --- | --- | --- | --- |
| `GS_PARTITION`, `GS_GRES` | cluster | GPU partition and GPU request (`gpu:a100:1` when the cluster needs the type) | needed for GPU jobs |
| `GS_CPU_PARTITION` | cluster | partition used with `--cpu` | needed with `--cpu` |
| `GS_MAX_HOURS`, `GS_TARGET_HOURS` | cluster | partition time limit and packing target, in hours | needed by `gs table` |
| `GS_MAX_RESTARTS` | cluster | self-requeues of one task | `10` |
| `GS_MODULES` | cluster | space-separated modules loaded by `gs_modules` and `gs_venv` | none |
| `GS_LOG_ROOT` | cluster | folder of logs and `submissions.tsv` | `logs` |
| `GS_TAG` | cluster | prefix of tagged log lines | `gs:` |
| `SBATCH_NO_REQUEUE` | cluster | `1` submits without `--requeue` | unset |
| `GS_DATA` | project | result root of the job templates | needed by them |
| `GS_VENV` | project | virtualenv built by `gs_venv`, used as `{GS_PYTHON}` | none |
| `GS_COMMAND` | project | command per config (`{}` is the config, `{NAME}` the variable NAME) | needed by `gs submit` |
| `GS_REQUIRED` | project | names of the project's own variables that `gs doctor` requires (space-separated) | none |
| `GS_EXTRAS` | project | pip extras installed into the virtualenv | none |
| `GS_CONFIG_SUFFIX` | project | suffix appended to `CONFIG` in `gs table` | none |
| `GS_ROW_ARGS` | project | extra arguments per `gs table` line (`{N}` is field `N`) | none |
| `GS_MARGIN` | run | multiplier of `HOURS` in `gs table` | `1.3` |
| `GS_SWEEP` | run | sweep name printed by `gs_sweep` | none |

On a cluster that rejects `--requeue`, set `SBATCH_NO_REQUEUE=1`. `sbatch` then submits without it, and `gs_finish` exits nonzero with a resubmit message when runs remain.

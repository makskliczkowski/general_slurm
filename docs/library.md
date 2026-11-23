# Library and Python contract

Source `${GS_HOME}/lib/gs.sh` in bash and import `general_slurm` in Python.

| Need | Bash | Python |
| --- | --- | --- |
| arguments | `gs_positional`, `gs_variadic`, `gs_option`, `gs_list`, `gs_flag`, `gs_parse "$@"` | `add_arguments(parser)`, `parse_shard` |
| settings | `gs_env`, `gs_need`, `gs_path`, `gs_print_settings` | - |
| log lines | `gs_frame "$@"`, `gs_info`, `gs_data`, `gs_progress`, `gs_checkpoint`, `gs_metric` | `frame`, `info`, `data`, `progress`, `checkpoint`, `metric` |
| job facts | `gs_job` (`GS_JOB_ID`, `GS_TASK`, `GS_TASKS`, `GS_RESTARTS`, `GS_CPUS`), `gs_sweep` | `Job.from_environment()` |
| environment | `gs_modules`, `gs_venv ROOT VENV [EXTRAS]`, `gs_setup_env` (venv if `GS_VENV` is set, else modules) | - |
| requeue and limits | `gs_run_each CONFIG... -- CMD...`, `gs_finish`, `gs_deadline`, `gs_latest DIR` | `shard`, `fits`, `fresh_allocation_fits`, `stop_on_signals`, `held_signals`, `budget_alarm`, `DONE`, `FAILED`, `LEFT` |
| tables | `gs_row TABLE`, `gs_pack TABLE MAX_HOURS TARGET [WORD...]` | `read_table`, `row`, `pack` |
| submission | `gs_placement [--cpu]`, `gs_logs TAG`, `gs_sbatch PRINT [K=V...] -- ARGS...` | - |
| settings files | `gs_cluster_load`, `gs_project_load`, `gs_setting_where`, `gs_setting_source` | - |
| status | - | `append_status(path, fields, columns)` |

## Log format

Bash and Python write the same lines, so one parser reads every log.

```text
gs: info script=/path/to/script
gs: info git=main@abc1234
== myjob job 12345 task 0 on node01 at 2026-01-01T06:00:00+01:00
== in /path/to/repo: arg1 arg2
gs: data=/path/to/data/run1
gs: progress=1/4
gs: checkpoint=/path/to/data/run1/ckpt.pt
gs: metric loss=0.012
== exit 0 at 2026-01-01T06:10:00+01:00
```

`gs_data` also appends the job id, the script and the date to `job.txt` in the data folder.

## Auto-requeue contract

`jobs/shards.slurm` passes `--shard k/n` to `GS_COMMAND` and, when Slurm sets an end time, `--deadline EPOCH --allocation-start EPOCH`. A program that follows the contract (see `templates/job.py` and the programs in `examples/`):

1. runs only its slice from `general_slurm.shard`
2. starts a run only when its budget plus ten minutes fits before `--deadline` (`fits`), and exits `1` when even a fresh allocation cannot hold it (`fresh_allocation_fits`)
3. saves a checkpoint on `SIGTERM` (`stop_on_signals`) and protects writes with `held_signals`
4. exits `0` (`DONE`) when finished, `130` (`LEFT`) when runs remain, and another nonzero status on failure

Slurm sends `USR1` ten minutes before the time limit (`#SBATCH --signal=B:USR1@600`) and `TERM` on `scancel`. `gs_run_each` forwards both to the program as `TERM`. When runs are left after `USR1` or a self-budget stop, `gs_finish` calls `scontrol requeue` up to `GS_MAX_RESTARTS` times, never after `scancel`.

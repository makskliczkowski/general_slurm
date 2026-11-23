# General Slurm

Helpers for Slurm job scripts. One checkout serves every project and every cluster you use.

A job script that names a partition, a GPU type, a module or a scratch path works on one cluster only. With `general_slurm` a project script names none of them.

It reads variables such as `GS_PARTITION` and `GS_DATA`, and the values come from small settings files that you keep in your home folder, one set per cluster and, where needed, one per project on that cluster.

> **The `GS_*` names are generic placeholders.** They are the names the library itself reads (the partition, the data folder, the command). A project is not limited to them as it can export its own variables from the same files (for example `FIT_CACHE` or `SIM_SCRATCH`), give them different values on each cluster, and use them in `GS_COMMAND` as `{FIT_CACHE}`. The project's scripts and programs read those variables.

## What it gives you

- **Settings by host name.** A login node is mapped to a cluster once. Its partitions, GPU request, time limits and modules are exported in every shell and inherited by every job.
- **Defaults for the library, for a cluster and for a project.** A project can override a cluster value on one cluster only (a different partition, its own data folder).
- **Checks before you submit.** `gs info` shows what the cluster has and which settings are active. `gs doctor` reports what a kind of job and a language still miss.
- **One way to submit.** `gs run` for one command, `gs submit` for a sharded array that requeues itself before the time limit, `gs table` for a table of runs packed into arrays, `gs status` and `gs rerun` for what failed.
- **The same log in bash, C++ and Python.** A banner, tagged progress, data, checkpoint and metric lines, and the exit status, in one form that a parser reads.

## Install

```bash
git submodule add <url> deps/general_slurm      # or clone it anywhere
export GS_HOME="$PWD/deps/general_slurm"
export PATH="$GS_HOME/bin:$PATH"
python -m pip install -e deps/general_slurm     # only for the Python helpers
```

Bash 3.2 or later is enough everywhere except `gs_venv` (bash 4.1 and `flock`, on the cluster).

## First steps

On a login node, once per cluster:

```bash
gs env host 'login*' clusterA                   # map the login-node host name to a cluster
gs env set clusterA GS_PARTITION gpu
gs env set clusterA GS_GRES gpu:1
gs env install                                  # load the cluster settings in every new shell
gs info                                         # what the cluster has and which settings are active
```

Then, in a project:

```bash
gs doctor --job shards --lang python            # what is still missing for this kind of job
gs run --time=01:00:00 --print -- ./build/sim inputs/a.cfg
gs submit runs/a.toml runs/b.toml --tasks 4 --time=12:00:00
```

Settings have three levels, and the most specific wins: the project on a cluster (`~/.config/general_slurm/<project>/<cluster>.sh`), the cluster (`~/.config/general_slurm/<cluster>.sh`), and the project defaults in `slurm.env`.

## Documentation

| Read | For |
| --- | --- |
| [docs/settings.md](docs/settings.md) | the three levels, precedence, how a cluster and a project are chosen, every variable |
| [docs/setup.md](docs/setup.md) | set up a cluster and a project, check what is missing with `gs info` and `gs doctor` |
| [docs/examples.md](docs/examples.md) | a C++ and a Python project on one cluster with different partitions (`examples/`) |
| [docs/jobs.md](docs/jobs.md) | single jobs, row arrays, sharded arrays that requeue, packed experiments, status and rerun |
| [docs/commands.md](docs/commands.md) | every `gs` subcommand |
| [docs/library.md](docs/library.md) | the bash and Python helpers, the log format, the auto-requeue contract |

## Development

```bash
python -m pytest -q
shellcheck -S warning lib/*.sh bin/gs libexec/gs-* jobs/*.slurm templates/*.sh templates/*.slurm
bin/gs check bin/gs libexec/gs-* jobs/*.slurm templates/*.sh templates/*.slurm
```

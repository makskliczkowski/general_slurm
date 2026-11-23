# Set up a cluster and a project

Run these commands on a login node. The levels and the precedence are explained in [settings](settings.md).

## A cluster, once

```bash
# map the login-node host names to a cluster name (narrow patterns first)
gs env host 'login-gpu*' clusterA
gs env host 'login*' clusterB

# defaults of every project on clusterA
gs env set clusterA GS_PARTITION gpu
gs env set clusterA GS_GRES gpu:1
gs env set clusterA GS_CPU_PARTITION normal
gs env set clusterA GS_MAX_HOURS 48
gs env set clusterA GS_TARGET_HOURS 12
gs env set clusterA GS_MODULES "python/3.12"

gs env install        # add the loader to ~/.bashrc, then open a new shell
gs info               # what this cluster has and which settings are active
```

## A project

Put the values that hold on every cluster into `slurm.env`, and the ones that differ into the project file of each cluster.

```bash
# in the repository: portable defaults
cat > slurm.env <<'EOF'
GS_PROJECT=fit
GS_COMMAND={GS_PYTHON} scripts/run.py {}
EOF

# per cluster: where this project keeps its data and environment, and a partition of its own
gs env set clusterA GS_DATA /scratch/fit/data --project fit
gs env set clusterA GS_VENV /scratch/fit/venv --project fit
gs env set clusterA GS_PARTITION gpu-big --project fit
```

`gs info` run inside the repository lists the settings files that exist and each setting with the file it comes from.

## Check what is missing

```bash
gs info                                       # banners: host, cluster, settings files, partitions, settings and their source, projects
gs doctor                                     # Slurm commands, partitions, GPU request, time limit, repository settings
gs doctor --job shards --lang python          # also: what this kind of job and language need
gs doctor --job table --lang cpp --cpu        # a CPU table of C++ runs
```

`--job` is one of `run` (`gs run`), `job` and `row` (the templates, which write into `GS_DATA`), `shards` (`gs submit`) and `table` (`gs table`). `--lang` is `python` (needs `GS_VENV`), `cpp` (warns when `GS_MODULES` is empty) or `bash`. A missing setting fails with the command or file that sets it. `gs doctor` starts no job, so it cannot see whether a program finds its GPU.

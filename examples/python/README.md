# Example: a Python script

A small Python script that follows the sharding contract of general_slurm, with the standard library only. It reads a config with one line `runs = N`, does its block of the runs (`--shard k/n`) and writes one line per run into the folder given by `--out`. The folder comes from the project's own variable `FIT_SCRATCH`, which has a different value on each cluster.

| File | Holds |
| --- | --- |
| `slurm.env` | `GS_PROJECT`, `GS_COMMAND` (uses `{GS_PYTHON}` and `{FIT_SCRATCH}`), and `GS_REQUIRED=FIT_SCRATCH` so that `gs doctor` fails while it is empty |
| `scripts/run.py`, `pyproject.toml` | the script, and the file the virtualenv is built from |
| `runs/a.toml`, `runs/b.toml` | two configs |

## Configure from scratch on a cluster

The cluster here is artificial. Its login nodes are `orion-login1`, `orion-login2`, ... and it has the CPU partitions `short` and `long` and the GPU partitions `gpu` and `gpu-big`. Run everything on a login node.

**1. The cluster, once.** Skip this when another project already did it.

```bash
gs env host 'orion-login*' orion          # login-node names that mean "orion"
gs env set orion GS_PARTITION gpu         # defaults of every project on orion
gs env set orion GS_GRES gpu:1
gs env set orion GS_CPU_PARTITION short
gs env set orion GS_MAX_HOURS 48
gs env set orion GS_TARGET_HOURS 12
gs env set orion GS_MODULES "python/3.12"
gs env install                            # then open a new shell
gs info                                   # orion, its partitions, the settings that are set
```

**2. This project on orion.** The project asks for the big GPU partition with two GPUs, a virtualenv of its own, and a scratch folder of its own:

```bash
cd examples/python
gs env set orion GS_PARTITION gpu-big --project example_python
gs env set orion GS_GRES gpu:2 --project example_python
gs env set orion GS_VENV /scratch/example_python/venv --project example_python
gs env set orion FIT_SCRATCH /scratch/example_python/out --project example_python
gs info                                   # each setting with the file it comes from
```

**3. Check and submit.**

```bash
gs doctor --job shards --lang python      # fails and names the setting while one is missing
gs submit runs/a.toml runs/b.toml --tasks 4 --time=01:00:00 --mem=4G --print    # preview the sbatch line
gs submit runs/a.toml runs/b.toml --tasks 4 --time=01:00:00 --mem=4G
gs status runs/ --since now-1day          # task counts by state
```

The first job builds the virtualenv under a lock (`gs_venv`, bash 4.1 and `flock`), then runs on `gpu-big` and writes `/scratch/example_python/out/a.txt` and `b.txt`. On another cluster, repeat step 1 with its names and step 2 with its values. Nothing in the project changes.

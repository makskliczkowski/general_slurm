# Example: a C++ program

A small C++ program that follows the sharding contract of general_slurm. It reads a config with one line `runs = N`, does its block of the runs (`--shard k/n`) and writes one line per run into the folder given by `--out`. The folder comes from the project's own variable `SIM_SCRATCH`, which has a different value on each cluster.

| File | Holds |
| --- | --- |
| `slurm.env` | `GS_PROJECT`, `GS_COMMAND` (uses `{SIM_SCRATCH}`), and `GS_REQUIRED=SIM_SCRATCH` so that `gs doctor` fails while it is empty |
| `src/sim.cpp`, `Makefile` | the program and its build |
| `runs/a.cfg`, `runs/b.cfg` | two configs |

## Configure from scratch on a cluster

The cluster here is artificial. Its login nodes are `orion-login1`, `orion-login2`, ... and it has the CPU partitions `short` and `long` and the GPU partition `gpu`. Run everything on a login node.

**1. The cluster, once.** Skip this when another project already did it.

```bash
gs env host 'orion-login*' orion          # login-node names that mean "orion"
gs env set orion GS_PARTITION gpu         # defaults of every project on orion
gs env set orion GS_GRES gpu:1
gs env set orion GS_CPU_PARTITION short
gs env set orion GS_MAX_HOURS 48
gs env set orion GS_TARGET_HOURS 12
gs env install                            # then open a new shell
gs info                                   # orion, its partitions, the settings that are set
```

**2. This project on orion.** The project asks for the long CPU partition, the compiler module, and a scratch folder of its own:

```bash
cd examples/cpp
gs env set orion GS_CPU_PARTITION long --project example_cpp
gs env set orion GS_MODULES "gcc/13" --project example_cpp
gs env set orion SIM_SCRATCH /scratch/example_cpp --project example_cpp
gs info                                   # each setting with the file it comes from
```

**3. Check, build, submit.**

```bash
gs doctor --job shards --lang cpp --cpu   # fails and names the setting while one is missing
make                                      # builds build/sim
gs submit runs/a.cfg runs/b.cfg --cpu --tasks 4 --time=01:00:00 --print    # preview the sbatch line
gs submit runs/a.cfg runs/b.cfg --cpu --tasks 4 --time=01:00:00
gs status runs/ --since now-1day          # task counts by state
```

The job runs on `long` and writes `/scratch/example_cpp/a.txt` and `b.txt`. On another cluster, repeat step 1 with its names and step 2 with its values. Nothing in the project changes.

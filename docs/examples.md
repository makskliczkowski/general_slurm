# Two example projects on one cluster

`examples/cpp` (a C++ program) and `examples/python` (a Python script) are two small projects that follow the sharding contract. Each holds a `slurm.env` with its command and its project name, a few configs in `runs/`, the program, and a README that configures it from scratch on an artificial cluster:

- [examples/cpp/README.md](../examples/cpp/README.md)
- [examples/python/README.md](../examples/python/README.md)

They name no cluster. Each has a variable of its own (`SIM_SCRATCH`, `FIT_SCRATCH`) that the command uses and that `GS_REQUIRED` lists, so `gs doctor` fails until the cluster has a value for it. Both share the cluster `orion`, and only the files of the home folder tell them apart:

```text
~/.config/general_slurm/
    hosts                        orion-login*  orion
    orion.sh                     GS_PARTITION=gpu  GS_GRES=gpu:1  GS_CPU_PARTITION=short  GS_MAX_HOURS=48  GS_TARGET_HOURS=12
    example_cpp/orion.sh         GS_CPU_PARTITION=long  GS_MODULES="gcc/13"  SIM_SCRATCH=/scratch/example_cpp
    example_python/orion.sh      GS_PARTITION=gpu-big  GS_GRES=gpu:2  GS_VENV=/scratch/example_python/venv  FIT_SCRATCH=/scratch/example_python/out
```

The C++ project runs on `long`, and the Python project on `gpu-big` with two GPUs. Both run unchanged on another cluster once that cluster has its files. A bash project needs no program of its own and no project file. A one-off command needs only `gs run --time=01:00:00 -- bash scripts/step.sh`.

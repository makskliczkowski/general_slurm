# Settings of one cluster: copy to ~/.config/general_slurm/<cluster>.sh, or write them with "gs env set <cluster> NAME VALUE".
# Only export lines. A project's own settings for this cluster go to ~/.config/general_slurm/<project>/<cluster>.sh.

# GPU placement: partition and request, fully qualified where the cluster asks for it (gpu:a100:1)
export GS_PARTITION=gpu
export GS_GRES=gpu:1
# CPU placement, for --cpu
export GS_CPU_PARTITION=normal
# job time limit of the GPU partition and packing target, in hours
export GS_MAX_HOURS=48
export GS_TARGET_HOURS=12
# restarts of a task with runs left
export GS_MAX_RESTARTS=10
# modules loaded by gs_venv, space separated
export GS_MODULES=""
# a cluster that rejects --requeue: sbatch reads this and submits without it, so tasks cannot requeue themselves
# export SBATCH_NO_REQUEUE=1

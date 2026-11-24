# Commands

`gs` with no argument lists the subcommands. `gs SUBCOMMAND --help` shows flags and defaults.

| Command | Does |
| --- | --- |
| `gs info` | summarizes host, cluster, settings files, partitions, active settings with their source, and projects |
| `gs doctor [--job K] [--lang L] [--cpu]` | checks Slurm, partitions, GPU request, time limit, repository settings, and what a job kind and language need |
| `gs env` | maps host patterns to clusters, edits cluster and project settings, installs the `~/.bashrc` block |
| `gs jupyter [--root DIR] [--port N] [--kernel NAME]` | starts JupyterLab with the project virtualenv and registers a kernel that inherits the job environment |
| `gs new job\|array\|launcher\|python PATH` | copies a template without overwriting |
| `gs check SCRIPT...` | checks the script layout |
| `gs run [--] CMD...` | submits one command or `.slurm` script with the placement |
| `gs submit CONFIG...` | submits a sharded array |
| `gs table RUN_FOLDER [WORD...]` | packs `arrays.txt` and submits each selected line |
| `gs status JOBID\|RUN_FOLDER\|PREFIX` | counts tasks by job name and state |
| `gs rerun JOBID` | resubmits failed, timed-out, out-of-memory or node-failed tasks |

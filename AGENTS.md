# AGENTS.md

`general_slurm`: helpers for Slurm job scripts of any project and cluster. Bash library in `lib/`, the `gs` command in `bin/` with its
subcommands in `libexec/`, the general job script `jobs/shards.slurm`, the Python package in `python/general_slurm/`, script templates in
`templates/`, examples of a cluster settings file and a host map in `profiles/` (cluster selection by host name: `lib/cluster.sh`, `gs env`). The README is the documentation: settings, the contract, the script layout, the helpers.

## Rules

- General only: no file names a cluster, a user, a project or a tool that uses the library. Cluster values live in the user's settings files
  outside the repository; project values in the project's `slurm.env`.
- Bash 3.2 compatible everywhere except `gs_venv` (bash 4.1, `flock`): no associative arrays, no `mapfile`, empty arrays guarded under `set -u`.
- Python 3.9, no dependencies. Bash and Python give the same log lines and the same packing; `tests/test_jobs.py` checks the packing.
- Every file has the header and the `#! EOF` footer of its language; templates keep their summary as the first comment lines. One statement per
  line, comments above the line, aligned variable blocks. shellcheck exceptions only in `.shellcheckrc`.
- Tests: `python -m pytest -q` (with `python/` importable: `pip install -e .`). Lint: `shellcheck -S warning lib/*.sh bin/gs libexec/gs-* jobs/*.slurm templates/*.sh templates/*.slurm`
  and `bin/gs check bin/gs libexec/gs-* jobs/*.slurm templates/*.sh templates/*.slurm`.

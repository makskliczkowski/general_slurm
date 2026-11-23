"""The bash side: the requeue cases of jobs/shards.slurm, packing in bash against Python, and previews that write nothing.

jobs/shards.slurm runs with stub scontrol and squeue and a stub program. The program reads its config name ("a", "b"), exits with EXIT_<name>
and, with SIGNAL_<name>=USR1, sends USR1 to the job script before it exits, as the time limit would.
"""

import os
import stat
import subprocess
from pathlib import Path

import pytest

import general_slurm as gs

HOME    = Path(__file__).resolve().parents[1]
PROGRAM = """#!/bin/bash
name=$(basename "$1")
echo "run $name" >> "$RUN_LOG"
exit_var="EXIT_$name"
signal_var="SIGNAL_$name"
if [[ -n "${!signal_var:-}" ]]; then
    kill -"${!signal_var}" "$PPID"
    sleep 0.3
fi
exit "${!exit_var:-0}"
"""
SCONTROL = """#!/bin/bash
if [[ "$1" == requeue ]]; then
    echo "scontrol requeue $2"
    exit "${SCONTROL_EXIT:-0}"
fi
exit 1
"""


def _executable(path: Path, text: str) -> Path:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


@pytest.fixture
def cluster(tmp_path):
    """Stub commands on PATH, the stub program, and two configs a and b."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _executable(bin_dir / "scontrol", SCONTROL)
    _executable(bin_dir / "squeue", "#!/bin/bash\nexit 0\n")
    program = _executable(tmp_path / "program", PROGRAM)
    for name in ("a", "b"):
        (tmp_path / name).write_text("")
    return tmp_path, bin_dir, program


def _run_task(cluster, **variables):
    """Run jobs/shards.slurm as one array task; return its exit status, the configs it ran and its last line."""
    tmp_path, bin_dir, program = cluster
    run_log = tmp_path / "runs.log"
    run_log.write_text("")
    environment = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "GS_HOME": str(HOME), "SLURM_JOB_ID": "1",
                   "GS_CONFIGS": f"{tmp_path / 'a'} {tmp_path / 'b'}", "GS_COMMAND": f"{program} {{}}", "RUN_LOG": str(run_log), **variables}
    result = subprocess.run(["bash", str(HOME / "jobs" / "shards.slurm")], cwd=tmp_path, env=environment, capture_output=True, text=True)
    lines = [line for line in result.stdout.splitlines() if not line.startswith(("==", "gs:"))]
    return result.returncode, run_log.read_text().split("run ")[1:], lines[-1] if lines else ""


@pytest.mark.parametrize("variables, status, runs, last", [
    # runs left: requeued
    ({"EXIT_a": "130"}, 0, ["a", "b"], "requeued with runs left"),
    # the cluster refuses the requeue: nonzero, so Slurm does not show the task as completed
    ({"EXIT_a": "130", "SCONTROL_EXIT": "1"}, 1, ["a", "b"], "refused the requeue"),
    # restart cap reached
    ({"EXIT_a": "130", "SLURM_RESTART_COUNT": "10"}, 1, ["a", "b"], "stopped with runs left"),
    # USR1 (time limit) during a: b is left and the task requeues
    ({"SIGNAL_a": "USR1"}, 0, ["a"], "requeued with runs left"),
    # TERM (scancel) during a: b is left, no requeue
    ({"SIGNAL_a": "TERM"}, 1, ["a"], "stopped with runs left"),
    # all done
    ({}, 0, ["a", "b"], "finished"),
    # a fails, b still runs
    ({"EXIT_a": "1"}, 1, ["a", "b"], "failed (exit 1)"),
])
def test_requeue_cases(cluster, variables, status, runs, last):
    """Reference: the exit status, the configs run and the last line that each case of the contract must give."""
    code, ran, line = _run_task(cluster, **variables)
    assert (code, [name.strip() for name in ran]) == (status, runs)
    assert last in line


def test_bash_and_python_packing_agree(tmp_path):
    """gs_pack and general_slurm.pack give the same arrays on a table with packed, long, optioned and request lines."""
    table = tmp_path / "arrays.txt"
    table.write_text("# config label runs hours\n"
                     "full  4x4 ite    35  0.3\n"
                     "full  4x4 iaite  70  0.5   cpus=8 mem=32G\n"
                     "sweep 8x8 iaite   5  40.0  cpus=8\n"
                     "extra 4x4 ite     3  1.0   request\n")
    for words in ([], ["full"], ["iaite"], ["extra"]):
        bash = subprocess.run(["bash", "-c", f'source "{HOME}/lib/gs.sh" && gs_pack "{table}" 48 12 {" ".join(words)}'],
                              cwd=tmp_path, capture_output=True, text=True, env={**os.environ, "GS_HOME": str(HOME)})
        lines   = [line.split("\t") for line in bash.stdout.splitlines()]
        python  = [[a.config, " ".join(a.labels), str(a.runs), str(a.per_task), str(a.tasks), str(a.limit), " ".join(f"{k}={v}" for k, v in a.options.items())]
                   for a in gs.pack(table, 48, 12, words)]
        assert lines == python


def test_shards_loads_modules_without_venv(cluster):
    """jobs/shards.slurm loads GS_MODULES via gs_modules even when GS_VENV is not set."""
    tmp_path, bin_dir, _ = cluster
    module_log = tmp_path / "module.log"
    _executable(bin_dir / "module", '#!/bin/bash\nprintf "%s\\n" "$*" >> "$MODULE_LOG"\n')
    code, ran, _ = _run_task(cluster, GS_MODULES="gcc/13 cuda/12", GS_VENV="", MODULE_LOG=str(module_log))
    assert code == 0
    assert [name.strip() for name in ran] == ["a", "b"]
    assert module_log.read_text().splitlines() == ["reset", "load gcc/13", "load cuda/12"]


def test_submit_preview_writes_nothing(tmp_path):
    """gs submit --print shows one sbatch line of the array and creates no log folder."""
    environment = {**os.environ, "GS_PARTITION": "gpu", "GS_GRES": "gpu:1", "GS_COMMAND": "run {}"}
    result = subprocess.run([str(HOME / "bin" / "gs"), "submit", "a.ini", "b.ini", "--tasks", "3", "--max-running", "2", "--print"],
                            cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "--array=0-2%2" in result.stdout and "--partition=gpu" in result.stdout
    assert not any(tmp_path.iterdir())

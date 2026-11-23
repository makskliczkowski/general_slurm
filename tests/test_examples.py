"""The example projects: the commands of docs/examples.md preview the placement of each project's own settings, and the example programs
split their runs into shards that cover every run once."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HOME = Path(__file__).resolve().parents[1]


def _environment(config_dir):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GS_")}
    environment.update({"GS_CONFIG_DIR": str(config_dir), "GS_HOSTNAME": "orion-login1"})
    return environment


def _gs(arguments, project, config_dir):
    """Run gs in an example folder as a login shell would: the cluster is chosen by host name before the command starts."""
    words = " ".join(f"'{argument}'" for argument in arguments)
    script = f'source "{HOME}/lib/cluster.sh"; gs_cluster_load; exec "{HOME}/bin/gs" {words}'
    return subprocess.run(["bash", "-c", script], cwd=HOME / "examples" / project, env=_environment(config_dir), capture_output=True, text=True)


def _configure(config_dir):
    """The commands of step 1 and step 2 of the two example READMEs, on the artificial cluster orion."""
    steps = [
        ("cpp", ["env", "host", "orion-login*", "orion"]),
        ("cpp", ["env", "set", "orion", "GS_PARTITION", "gpu"]),
        ("cpp", ["env", "set", "orion", "GS_GRES", "gpu:1"]),
        ("cpp", ["env", "set", "orion", "GS_CPU_PARTITION", "short"]),
        ("cpp", ["env", "set", "orion", "GS_CPU_PARTITION", "long", "--project", "example_cpp"]),
        ("cpp", ["env", "set", "orion", "SIM_SCRATCH", "/scratch/example_cpp", "--project", "example_cpp"]),
        ("python", ["env", "set", "orion", "GS_PARTITION", "gpu-big", "--project", "example_python"]),
        ("python", ["env", "set", "orion", "GS_GRES", "gpu:2", "--project", "example_python"]),
        ("python", ["env", "set", "orion", "FIT_SCRATCH", "/scratch/example_python/out", "--project", "example_python"]),
    ]
    for project, arguments in steps:
        assert _gs(arguments, project, config_dir).returncode == 0


def test_examples_preview_their_own_partition_and_variable(tmp_path):
    """Following the README steps, two projects on one cluster get the partition of their own settings file and a value of their own
    variable in the command; the cluster value stays where the project sets none. Reference: examples/*/README.md."""
    _configure(tmp_path)
    cpp = _gs(["submit", "runs/a.cfg", "runs/b.cfg", "--cpu", "--tasks", "4", "--time=01:00:00", "--print"], "cpp", tmp_path)
    python = _gs(["submit", "runs/a.toml", "runs/b.toml", "--tasks", "4", "--time=01:00:00", "--print"], "python", tmp_path)
    assert "--partition=long" in cpp.stdout and "build/sim" in cpp.stdout and "SIM_SCRATCH" in cpp.stdout
    assert "--partition=gpu-big" in python.stdout and "--gres=gpu:2" in python.stdout and "FIT_SCRATCH" in python.stdout


def test_doctor_requires_the_variables_a_project_declares(tmp_path):
    """The C++ example fails gs doctor while SIM_SCRATCH is empty and names the project command that sets it; once set, it passes.
    A stub sinfo and sbatch stand in for Slurm."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, text in {"sinfo": "#!/bin/bash\ncase \"$*\" in *%P*) echo short;; *%G*) echo '(null)';; *%l*) echo 7-00:00:00;; esac\n",
                       "sbatch": "#!/bin/bash\necho slurm 24.05\n", "squeue": "#!/bin/bash\n", "sacct": "#!/bin/bash\n", "scontrol": "#!/bin/bash\n"}.items():
        (bin_dir / name).write_text(text)
        (bin_dir / name).chmod(0o755)
    config = tmp_path / "config"
    config.mkdir()
    environment = _environment(config)
    environment.update({"PATH": f"{bin_dir}:{environment['PATH']}", "GS_CLUSTER": "orion", "GS_CPU_PARTITION": "short"})
    command = [str(HOME / "bin" / "gs"), "doctor", "--job", "shards", "--lang", "cpp", "--cpu"]
    failed = subprocess.run(command, cwd=HOME / "examples" / "cpp", env=environment, capture_output=True, text=True)
    assert failed.returncode == 1 and "SIM_SCRATCH" in failed.stdout and "--project example_cpp" in failed.stdout
    environment["SIM_SCRATCH"] = "/scratch/example_cpp"
    passed = subprocess.run(command, cwd=HOME / "examples" / "cpp", env=environment, capture_output=True, text=True)
    assert "SIM_SCRATCH" not in "".join(line for line in passed.stdout.splitlines() if line.startswith("fail"))


@pytest.mark.skipif(shutil.which("c++") is None, reason="no C++ compiler")
def test_cpp_example_shards_cover_every_run_once(tmp_path):
    """The C++ example, compiled as the Makefile does, runs the blocks 0/2 and 1/2 of a config with eight runs: runs 0 to 7 once each."""
    program = tmp_path / "sim"
    subprocess.run(["c++", "-O2", "-std=c++17", "-o", str(program), str(HOME / "examples" / "cpp" / "src" / "sim.cpp")], check=True)
    runs = []
    for shard in ("0/2", "1/2"):
        out = subprocess.run([str(program), "runs/a.cfg", "--shard", shard], cwd=HOME / "examples" / "cpp", capture_output=True, text=True,
                             check=True).stdout
        runs += [line.split()[1] for line in out.splitlines() if line.startswith("run ")]
    assert runs == [str(run) for run in range(8)]


def test_python_example_shards_cover_every_run_once():
    """The blocks 0/2 and 1/2 of a config with four runs together run each of runs 0 to 3 once."""
    runs = []
    for shard in ("0/2", "1/2"):
        out = subprocess.run([sys.executable, str(HOME / "examples" / "python" / "scripts" / "run.py"), "runs/b.toml", "--shard", shard],
                             cwd=HOME / "examples" / "python", capture_output=True, text=True, check=True).stdout
        runs += [line.split()[1] for line in out.splitlines() if line.startswith("run ")]
    assert runs == ["0", "1", "2", "3"]

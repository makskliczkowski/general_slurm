"""The tools: gs new and gs check, gs status and gs rerun against stub sacct and sbatch, and gs doctor against a stub sinfo."""

import os
import stat
import subprocess
from pathlib import Path

HOME = Path(__file__).resolve().parents[1]

# sacct prints the file SACCT_OUT; sbatch prints job id 200 and records its arguments in SBATCH_LOG
SACCT   = '#!/bin/bash\ncat "$SACCT_OUT"\n'
SBATCH  = '#!/bin/bash\nprintf "%s\\n" "$@" > "$SBATCH_LOG"\necho "200;cluster"\n'
# sinfo answers the three questions gs doctor asks: partitions, GPUs, time limit
SINFO   = """#!/bin/bash
case "$*" in
    *"%P"*) printf 'gpu*\\ncpu\\n' ;;
    *"%G"*) echo "gpu:a100:4(S:0-1)" ;;
    *"%l"*) echo "2-00:00:00" ;;
esac
"""


def _stubs(tmp_path, **scripts):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name, text in scripts.items():
        path = bin_dir / name
        path.write_text(text)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return bin_dir


def _gs(*arguments, cwd, bin_dir=None, **variables):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GS_")}
    if bin_dir is not None:
        environment["PATH"] = f"{bin_dir}:{environment['PATH']}"
    environment.update(variables)
    return subprocess.run([str(HOME / "bin" / "gs"), *arguments], cwd=cwd, env=environment, capture_output=True, text=True)


def test_new_script_passes_check_and_its_help_shows_the_summary(tmp_path):
    """A script from the job template passes gs check and is not overwritten; a script without usage fails. Regression: --help of a
    script with #SBATCH lines printed an #SBATCH line instead of its summary."""
    assert _gs("new", "job", "jobs/fit.slurm", cwd=tmp_path).returncode == 0
    assert _gs("new", "job", "jobs/fit.slurm", cwd=tmp_path).returncode == 2
    assert _gs("check", "jobs/fit.slurm", cwd=tmp_path).returncode == 0
    (tmp_path / "bad.sh").write_text("#!/usr/bin/env bash\n# Does a thing.\necho hi\n")
    bad = _gs("check", "bad.sh", cwd=tmp_path)
    assert bad.returncode == 1 and "no # usage: line" in bad.stdout

    help_text = subprocess.run(["bash", "jobs/fit.slurm", "--help"], cwd=tmp_path, env={**os.environ, "GS_HOME": str(HOME)}, capture_output=True, text=True).stdout
    assert help_text.splitlines()[0].startswith("Computes INPUT")


def test_env_set_writes_every_pair(tmp_path):
    """gs env set takes one or more NAME VALUE pairs and writes one export line per pair into the cluster file."""
    result = _gs("env", "set", "clusterA", "FIRST", "1", "SECOND", "two words", cwd=tmp_path, GS_CONFIG_DIR=str(tmp_path / "config"))
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "config" / "clusterA.sh").read_text().splitlines()[1:] == ['export FIRST=1', 'export SECOND="two words"']


def test_jupyter_preview_registers_a_kernel_and_prints_the_server(tmp_path):
    """gs jupyter --print shows the install, the kernel registration and the server line, and writes nothing."""
    result = _gs("jupyter", "--print", "--kernel", "demo", cwd=tmp_path, GS_PYTHON="/usr/bin/python3")
    assert result.returncode == 0, result.stderr
    assert "ipykernel install --user --name demo" in result.stdout
    assert "-m jupyter lab" in result.stdout and "--ServerApp.root_dir" in result.stdout
    assert list(tmp_path.iterdir()) == []


def test_status_counts_tasks_by_name_and_state(tmp_path):
    """A pending range counts as its number of tasks, "CANCELLED by N" as CANCELLED, and a run folder selects its own job names.
    Reference: the counts written by hand from the stub sacct lines."""
    (tmp_path / "sacct.txt").write_text("100_0|myrun_full|COMPLETED\n100_1|myrun_full|FAILED\n100_[2-5,8%2]|myrun_full|PENDING\n"
                                        "100_9|myrun_full|CANCELLED by 42\n101_0|other_x|RUNNING\n")
    (tmp_path / "myrun").mkdir()
    bin_dir = _stubs(tmp_path, sacct=SACCT)
    result  = _gs("status", "myrun", cwd=tmp_path, bin_dir=bin_dir, SACCT_OUT=str(tmp_path / "sacct.txt"))
    counts  = [line.split() for line in result.stdout.splitlines()]
    assert counts == [["myrun_full", "CANCELLED", "1"], ["myrun_full", "COMPLETED", "1"], ["myrun_full", "FAILED", "1"], ["myrun_full", "PENDING", "5"]]


def test_rerun_submits_the_failed_tasks_with_the_recorded_line(tmp_path):
    """gs submit records its line; gs rerun submits it again with only the failed and timed-out tasks, the array limit kept, the time
    replaced and the job variables unchanged."""
    bin_dir     = _stubs(tmp_path, sacct=SACCT, sbatch=SBATCH)
    sbatch_log  = tmp_path / "sbatch.txt"
    variables   = {"SACCT_OUT": str(tmp_path / "sacct.txt"), "SBATCH_LOG": str(sbatch_log), "GS_PARTITION": "gpu", "GS_GRES": "gpu:1"}
    submitted   = _gs("submit", "a.ini", "--command", "run {} --fast", "--tasks", "4", "--max-running", "2", "--time=04:00:00",
                      cwd=tmp_path, bin_dir=bin_dir, **variables)
    assert submitted.stdout.strip().endswith("submitted 200")
    (tmp_path / "logs" / "submissions.tsv").write_text((tmp_path / "logs" / "submissions.tsv").read_text().replace("200\t", "150\t"))

    # the columns gs rerun asks for: JobID, State
    (tmp_path / "sacct.txt").write_text("150_0|COMPLETED\n150_1|FAILED\n150_2|CANCELLED by 1\n150_3|TIMEOUT\n")
    rerun = _gs("rerun", "150", "--time=08:00:00", cwd=tmp_path, bin_dir=bin_dir, **variables)
    assert rerun.returncode == 0, rerun.stderr
    arguments = sbatch_log.read_text().splitlines()
    assert "--array=1,3%2" in arguments and "--time=08:00:00" in arguments and "--time=04:00:00" not in arguments
    assert arguments[-1].endswith("jobs/shards.slurm")
    assert "GS_COMMAND=run\\ \\{\\}\\ --fast" in (tmp_path / "logs" / "submissions.tsv").read_text().splitlines()[-1]


def test_run_submits_command_and_slurm_script(tmp_path):
    """gs run previews without writes, submits commands via jobs/run.slurm, submits .slurm scripts directly, and loads GS_MODULES locally."""
    bin_dir     = _stubs(tmp_path, sbatch=SBATCH, module='#!/bin/bash\nprintf "%s\\n" "$*" >> "$MODULE_LOG"\n')
    sbatch_log  = tmp_path / "sbatch.txt"
    variables   = {"SBATCH_LOG": str(sbatch_log), "GS_PARTITION": "gpu", "GS_GRES": "gpu:1", "GS_CPU_PARTITION": "cpu"}

    preview = _gs("run", "--time=02:00:00", "--print", "--", "./sim", "a.cfg", cwd=tmp_path, bin_dir=bin_dir, **variables)
    assert preview.returncode == 0, preview.stderr
    assert str(HOME / "jobs" / "run.slurm") in preview.stdout and "--partition=gpu" in preview.stdout and "--time=02:00:00" in preview.stdout
    assert [path.name for path in tmp_path.iterdir()] == ["bin"]

    submitted = _gs("run", "--time=02:00:00", "--", "./sim", "a.cfg", "--steps", "5", cwd=tmp_path, bin_dir=bin_dir, **variables)
    assert submitted.returncode == 0, submitted.stderr
    assert submitted.stdout.strip().endswith("submitted 200")
    arguments = sbatch_log.read_text().splitlines()
    assert "--partition=gpu" in arguments and "--gres=gpu:1" in arguments and "--time=02:00:00" in arguments
    assert not any(argument.startswith("--array=") for argument in arguments)
    assert arguments[-5:] == [str(HOME / "jobs" / "run.slurm"), "./sim", "a.cfg", "--steps", "5"]

    (tmp_path / "jobs").mkdir()
    (tmp_path / "jobs" / "my.slurm").write_text("#!/bin/bash\necho ok\n")
    slurm_sub = _gs("run", "--cpu", "jobs/my.slurm", "in.cfg", cwd=tmp_path, bin_dir=bin_dir, **variables)
    assert slurm_sub.returncode == 0, slurm_sub.stderr
    slurm_args = sbatch_log.read_text().splitlines()
    assert "--partition=cpu" in slurm_args and "--gres=none" in slurm_args
    assert slurm_args[-2:] == ["jobs/my.slurm", "in.cfg"] and str(HOME / "jobs" / "run.slurm") not in slurm_args

    show = tmp_path / "show"
    show.write_text('#!/bin/bash\nprintf "%s\\n" "$*" > "$ARGS_OUT"\n')
    show.chmod(show.stat().st_mode | stat.S_IEXEC)
    module_log  = tmp_path / "module.log"
    args_out    = tmp_path / "args.txt"
    local_env   = {key: value for key, value in os.environ.items() if not key.startswith("GS_")}
    local_env.update({"PATH": f"{bin_dir}:{local_env['PATH']}", "GS_HOME": str(HOME), "GS_MODULES": "gcc/13", "FOO": "hello", "MODULE_LOG": str(module_log), "ARGS_OUT": str(args_out)})
    local       = subprocess.run(["bash", str(HOME / "jobs" / "run.slurm"), str(show), "{FOO}", "bar"], cwd=tmp_path, env=local_env, capture_output=True, text=True)
    assert local.returncode == 0, local.stderr
    assert module_log.read_text().splitlines() == ["reset", "load gcc/13"]
    assert args_out.read_text().strip() == "hello bar"


def test_rerun_submits_single_failed_job(tmp_path):
    """gs rerun handles non-array single jobs: skips completed jobs and resubmits failed or timed-out jobs without --array."""
    bin_dir     = _stubs(tmp_path, sacct=SACCT, sbatch=SBATCH)
    sbatch_log  = tmp_path / "sbatch.txt"
    variables   = {"SACCT_OUT": str(tmp_path / "sacct.txt"), "SBATCH_LOG": str(sbatch_log), "GS_PARTITION": "gpu", "GS_GRES": "gpu:1"}
    submitted   = _gs("run", "--time=02:00:00", "--", "./sim", "a.cfg", cwd=tmp_path, bin_dir=bin_dir, **variables)
    assert submitted.returncode == 0, submitted.stderr
    (tmp_path / "logs" / "submissions.tsv").write_text((tmp_path / "logs" / "submissions.tsv").read_text().replace("200\t", "160\t"))

    sbatch_log.unlink()
    (tmp_path / "sacct.txt").write_text("160|COMPLETED\n")
    skipped = _gs("rerun", "160", cwd=tmp_path, bin_dir=bin_dir, **variables)
    assert skipped.returncode == 0 and "not in" in skipped.stdout
    assert not sbatch_log.exists()

    (tmp_path / "sacct.txt").write_text("160|TIMEOUT\n160.batch|FAILED\n")
    rerun = _gs("rerun", "160", "--time=06:00:00", "--mem=32G", cwd=tmp_path, bin_dir=bin_dir, **variables)
    assert rerun.returncode == 0, rerun.stderr
    arguments = sbatch_log.read_text().splitlines()
    assert "--time=06:00:00" in arguments and "--mem=32G" in arguments and "--time=02:00:00" not in arguments
    assert not any(argument.startswith("--array=") for argument in arguments)
    assert arguments[-3:] == [str(HOME / "jobs" / "run.slurm"), "./sim", "a.cfg"]


def test_doctor_fails_on_a_missing_partition_and_a_too_long_limit(tmp_path):
    """The GPU partition and its GPU request pass; a CPU partition that does not exist and a job limit above the partition's fail."""
    bin_dir = _stubs(tmp_path, sinfo=SINFO, sbatch="#!/bin/bash\necho slurm 24.05\n", squeue="", sacct="", scontrol="")
    result  = _gs("doctor", cwd=tmp_path, bin_dir=bin_dir, GS_PARTITION="gpu", GS_GRES="gpu:a100:1", GS_CPU_PARTITION="short",
                  GS_MAX_HOURS="72", GS_TARGET_HOURS="12")
    lines   = {tuple(line.split()[:2]) for line in result.stdout.splitlines()}
    assert result.returncode == 1
    assert {("ok", "GS_PARTITION"), ("ok", "GS_GRES"), ("fail", "GS_CPU_PARTITION"), ("fail", "GS_MAX_HOURS")} <= lines


def test_doctor_names_the_settings_a_job_kind_and_language_miss(tmp_path):
    """A sharded Python job without GS_COMMAND and GS_VENV fails on both and says where to set them; with both set it passes."""
    bin_dir = _stubs(tmp_path, sinfo=SINFO, sbatch="#!/bin/bash\necho slurm 24.05\n", squeue="", sacct="", scontrol="")
    placed  = {"GS_PARTITION": "gpu", "GS_GRES": "gpu:a100:1"}
    result  = _gs("doctor", "--job", "shards", "--lang", "python", cwd=tmp_path, bin_dir=bin_dir, **placed)
    assert result.returncode == 1
    assert "slurm.env: GS_COMMAND=VALUE" in result.stdout and "--project" in result.stdout
    result  = _gs("doctor", "--job", "shards", "--lang", "python", cwd=tmp_path, bin_dir=bin_dir, GS_COMMAND="./sim {}", GS_VENV="venv", **placed)
    assert "all settings of job=shards lang=python are set" in result.stdout


def test_info_lists_settings_with_their_source_and_the_projects(tmp_path):
    """gs info prints each set setting with the file it comes from, the settings left unset, and the projects of this cluster."""
    config = tmp_path / "config"
    (config / "alpha").mkdir(parents=True)
    (config / "a.sh").write_text("export GS_PARTITION=gpu\n")
    (config / "alpha" / "a.sh").write_text("export GS_DATA=/scratch/alpha\n")
    repo   = tmp_path / "alpha"
    repo.mkdir()
    (repo / "slurm.env").write_text("GS_COMMAND=./sim {}\n")
    result = _gs("info", cwd=repo, GS_CONFIG_DIR=str(config), GS_CLUSTER="a", GS_PARTITION="gpu", GS_DATA="/scratch/alpha")
    text   = result.stdout
    assert result.returncode == 0
    assert "GS_PARTITION" in text and "cluster settings of a" in text
    assert "/scratch/alpha" in text and "project settings for a" in text
    assert "./sim {}" in text and "slurm.env" in text
    assert "alpha  (this repository)" in text and "not set:" in text

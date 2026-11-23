"""Cluster settings by host name: the first matching pattern wins, an unknown host loads nothing and says so, gs env writes the files, and
gs env install keeps one block in ~/.bashrc."""

import os
import subprocess
from pathlib import Path

HOME = Path(__file__).resolve().parents[1]


def _bash(script, config, host, **variables):
    """Run SCRIPT after sourcing lib/cluster.sh, with the config folder and a host name; return stdout and stderr."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GS_")}
    environment.update({"GS_HOME": str(HOME), "GS_CONFIG_DIR": str(config), "GS_HOSTNAME": host, **variables})
    result = subprocess.run(["bash", "-c", f'source "{HOME}/lib/cluster.sh"; {script}'], env=environment, capture_output=True, text=True)
    return result.stdout, result.stderr


def _gs(*arguments, config, **variables):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GS_")}
    environment.update({"GS_CONFIG_DIR": str(config), **variables})
    return subprocess.run([str(HOME / "bin" / "gs"), "env", *arguments], env=environment, capture_output=True, text=True, check=True).stdout


def test_host_selects_its_cluster_and_project_files(tmp_path):
    """Overlapping patterns: the first that matches wins. The cluster file and every project file of that cluster are loaded; another
    cluster's files are not. Reference: the variables each host must see."""
    (tmp_path / "hosts").write_text("n2login*  a\nlogin*  b\n")
    (tmp_path / "a.sh").write_text("export GS_PARTITION=gpu\n")
    (tmp_path / "b.sh").write_text("export GS_PARTITION=other\n")
    (tmp_path / "proj").mkdir()
    (tmp_path / "proj" / "a.sh").write_text("export PROJ_STORAGE=/scratch/a\n")
    show = 'gs_cluster_load; echo "$GS_CLUSTER $GS_PARTITION ${PROJ_STORAGE:-none}"'
    assert _bash(show, tmp_path, "n2login1")[0].split() == ["a", "gpu", "/scratch/a"]
    assert _bash(show, tmp_path, "login3")[0].split() == ["b", "other", "none"]


def test_unknown_host_loads_nothing_and_says_so_and_inherited_settings_stay(tmp_path):
    """An unknown host gets one line on stderr and no settings; a shell that already has GS_CLUSTER (a job) keeps its settings."""
    (tmp_path / "hosts").write_text("n2login*  a\n")
    (tmp_path / "a.sh").write_text("export GS_PARTITION=gpu\n")
    out, err = _bash('gs_cluster_load; echo "${GS_CLUSTER:-none} ${GS_PARTITION:-none}"', tmp_path, "laptop")
    assert out.split() == ["none", "none"] and "matches no pattern" in err
    out, err = _bash('gs_cluster_load; echo "$GS_CLUSTER ${GS_PARTITION:-none}"', tmp_path, "node042", GS_CLUSTER="a", GS_PARTITION="kept")
    assert out.split() == ["a", "kept"] and err == ""


def test_gs_env_writes_settings_and_host_order(tmp_path):
    """set adds and then replaces one line, values with spaces are quoted, unset removes it; host appends, inserts before a pattern, and
    changes an existing pattern in place."""
    _gs("set", "a", "GS_MODULES", "python/3.12 cuda/12", config=tmp_path)
    _gs("set", "a", "GS_PARTITION", "gpu", config=tmp_path)
    _gs("set", "a", "GS_PARTITION", "gpu-a100", config=tmp_path)
    lines = [line for line in (tmp_path / "a.sh").read_text().splitlines() if line.startswith("export")]
    assert lines == ['export GS_MODULES="python/3.12 cuda/12"', "export GS_PARTITION=gpu-a100"]
    _gs("unset", "a", "GS_MODULES", config=tmp_path)
    assert "GS_MODULES" not in (tmp_path / "a.sh").read_text()

    _gs("host", "login*", "b", config=tmp_path)
    _gs("host", "n2login*", "a", "--before", "login*", config=tmp_path)
    _gs("host", "login*", "c", config=tmp_path)
    entries = [line.split() for line in (tmp_path / "hosts").read_text().splitlines() if not line.startswith("#")]
    assert entries == [["n2login*", "a"], ["login*", "c"]]


def test_install_keeps_one_block(tmp_path):
    """Installing twice leaves the other lines of ~/.bashrc and exactly one marked block."""
    bashrc = tmp_path / "bashrc"
    bashrc.write_text("export EDITOR=vim\n")
    _gs("install", config=tmp_path, GS_BASHRC=str(bashrc))
    _gs("install", config=tmp_path, GS_BASHRC=str(bashrc))
    text = bashrc.read_text()
    assert text.count("# >>> general_slurm >>>") == 1 and "export EDITOR=vim" in text and "gs_cluster_load" in text

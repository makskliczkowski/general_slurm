"""The Python side of the contract: shard split, deadline checks, held signals and the status file."""

import os
import signal

import pytest

import general_slurm as gs


def test_shards_cover_the_work_once_in_order():
    """Reference: for every count, the blocks of all indices concatenate to the whole list, and their sizes differ by at most one."""
    items = list(range(23))
    for count in (1, 2, 5, 23, 40):
        blocks = [gs.shard(items, index, count) for index in range(count)]
        assert sum(blocks, []) == items
        assert max(map(len, blocks)) - min(map(len, blocks)) <= 1


def test_deadline_checks():
    """A run fits when its budget and the ten-minute stop margin fit before the deadline; a fresh allocation is the allocation length less the
    start-up of the process. Reference: hand-computed times."""
    assert gs.fits(None, 100.0, now=0.0)
    assert gs.fits(3600.0, 4200.0, now=0.0)
    assert not gs.fits(3600.0, 4199.0, now=0.0)
    # 24 h allocation, 20 h used by an earlier part, 1 min start-up: a 10 h run waits for a new allocation, which can hold it
    assert gs.fresh_allocation_fits(36000.0, deadline=86400.0, allocation_start=0.0, process_start=72000.0, now=72060.0)
    # a 1 h allocation can never hold a 2 h run
    assert not gs.fresh_allocation_fits(7200.0, deadline=3600.0, allocation_start=0.0, process_start=0.0, now=60.0)


def test_stop_signal_during_a_save_is_held_and_reported():
    """SIGTERM inside held_signals does not interrupt the block; afterwards held.stop is true and the previous handler is back."""
    previous = signal.getsignal(signal.SIGTERM)
    with gs.held_signals() as held:
        os.kill(os.getpid(), signal.SIGTERM)
        saved = True
    assert saved and held.stop
    assert signal.getsignal(signal.SIGTERM) is previous


def test_budget_alarm_interrupts_and_says_so():
    """A budget of a few milliseconds raises KeyboardInterrupt, marks itself expired, and leaves no alarm behind."""
    with pytest.raises(KeyboardInterrupt):
        with gs.budget_alarm(0.01) as budget:
            signal.pause()
    assert budget.expired
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0.0


def test_status_file_has_one_header_and_one_line_per_run(tmp_path):
    """Two appends give the header once and two lines in column order; a tab in a value does not split it."""
    path = tmp_path / "status.tsv"
    gs.append_status(path, {"status": "done", "note": "a\tb"}, ["status", "note"])
    gs.append_status(path, {"status": "failed"}, ["status", "note"])
    lines = path.read_text().splitlines()
    assert lines[0] == "time\tstatus\tnote"
    assert [line.split("\t")[1:] for line in lines[1:]] == [["done", "a b"], ["failed", ""]]

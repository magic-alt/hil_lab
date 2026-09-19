from pathlib import Path

import pytest

from lab.resources import BenchResource, ResourceBusy, ResourceLock


def test_bench_resource_is_traceable():
    resource = BenchResource(
        resource_id="servo-bench-01",
        controller="rpi4",
        backend="bbb_pru",
        dut="gd32-servo-r2",
        adapter_revision="adapter-r1",
        fieldbus_interface="eth1",
    )
    assert resource.to_dict()["backend"] == "bbb_pru"


def test_resource_lock_prevents_parallel_acquisition(tmp_path: Path):
    lock_path = tmp_path / "servo-bench-01.lock"
    first = ResourceLock(lock_path, "servo-bench-01")
    second = ResourceLock(lock_path, "servo-bench-01")

    first.acquire()
    try:
        with pytest.raises(ResourceBusy):
            second.acquire()
    finally:
        first.release()

    second.acquire()
    second.release()

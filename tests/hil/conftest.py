from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from lab.resources import BenchResource


def pytest_addoption(parser):
    parser.addoption(
        "--hil-resource",
        action="store",
        default=os.environ.get("HIL_RESOURCE_JSON"),
        help="path to physical HIL resource inventory JSON",
    )


@pytest.fixture(scope="session")
def hil_resource(request):
    value = request.config.getoption("--hil-resource")
    if not value:
        pytest.skip("physical HIL resource not configured")
    document = json.loads(Path(value).read_text(encoding="utf-8"))
    return BenchResource(
        resource_id=document["resource_id"],
        controller=document["controller"],
        backend=document["backend"],
        dut=document["dut"],
        adapter_revision=document["adapter_revision"],
        fieldbus_interface=document.get("fieldbus_interface"),
    )

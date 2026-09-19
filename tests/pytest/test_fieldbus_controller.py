from __future__ import annotations

import pytest

from fieldbus import CommandEvidence, ToolUnavailable
from fieldbus.canopen import (
    CanFrame,
    NmtCommand,
    NmtState,
    build_nmt_frame,
    pack_can_frame,
    parse_heartbeat,
    unpack_can_frame,
)
from fieldbus.ethercat.igh import IghEthercatCli
from fieldbus.ethercat.soem import SoemSlaveInfo


def fake_runner(argv, timeout_s):
    command = tuple(argv)
    if command[-1] == "master":
        stdout = "Master0\n"
    elif command[-1] == "slaves":
        stdout = "0  0:0  PREOP  +  ServoA\n1  0:1  OP  +  ServoB\n"
    else:
        stdout = "SOEM scan ok\n"
    return CommandEvidence(command, 0, stdout, "", 1234)


def test_igh_adapter_preserves_command_evidence():
    cli = IghEthercatCli(
        runner=fake_runner,
        which=lambda name: f"/usr/bin/{name}",
    )
    master = cli.master_status()
    scan, slaves = cli.scan_slaves()

    assert master.ok
    assert master.argv == ("/usr/bin/ethercat", "master")
    assert len(slaves) == 2
    assert scan.duration_ns == 1234


def test_igh_adapter_fails_closed_when_tool_missing():
    cli = IghEthercatCli(which=lambda _: None)
    with pytest.raises(ToolUnavailable):
        cli.master_status()


def test_soem_adapter_requires_explicit_interface():
    cli = SoemSlaveInfo(
        runner=fake_runner,
        which=lambda name: f"/opt/soem/{name}",
    )
    evidence = cli.scan("eth1")
    assert evidence.argv == ("/opt/soem/slaveinfo", "eth1")


def test_socketcan_frame_encoding_round_trip():
    frame = CanFrame(can_id=0x123, data=b"\x01\x02\x03")
    assert unpack_can_frame(pack_can_frame(frame)) == frame


def test_canopen_nmt_and_heartbeat_primitives():
    command = build_nmt_frame(NmtCommand.START_REMOTE_NODE, 5)
    assert command == CanFrame(0, b"\x01\x05")

    heartbeat = parse_heartbeat(CanFrame(0x705, bytes((NmtState.OPERATIONAL,))))
    assert heartbeat.node_id == 5
    assert heartbeat.state is NmtState.OPERATIONAL

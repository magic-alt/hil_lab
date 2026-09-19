from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from boards.raspberry_pi.qualification import CyclictestQualifier, parse_cyclictest_metrics
from fieldbus import CommandEvidence
from fieldbus.canopen import (
    CanFrame, CanopenCiA402Node, CanopenSdoClient, CiA402State,
    CIA402_RPDO, NmtState, PdoMapping, PdoMappingEntry, SdoAbort,
    configure_pdo_mapping, decode_state, parse_emcy, wait_for_heartbeat,
    with_node_id,
)
from fieldbus.ethercat.igh.cycle import IghCycleQualifier
from fieldbus.ethercat.soem.cycle import SoemCycleQualifier
from lab.labgrid.client import LabgridPlaceLease
from lab.session import ServoHilSession
from lab.resources import ResourceLock


class FakeBus:
    def __init__(self, responses=()):
        self.responses = list(responses)
        self.sent = []
    def send(self, frame):
        self.sent.append(frame)
    def recv(self):
        if not self.responses:
            raise TimeoutError("no frame")
        return self.responses.pop(0)


def ev(argv, timeout_s, stdout='{}'):
    return CommandEvidence(tuple(argv), 0, stdout, "", 1000)


def test_igh_cycle_metrics_and_observe_only_default():
    stdout = '{"cycles":1000,"cycle_ns":1000000,"last_wkc":6,"wc_complete_cycles":1000,"bad_wkc":0,"max_abs_jitter_ns":12000,"mean_abs_jitter_ns":2300.0,"deadline_misses":0,"statusword":64,"operation_enabled_cycles":0,"enable_drive":false}\n'
    q = IghCycleQualifier(runner=lambda a,t: ev(a,t,stdout), which=lambda n:"/x/"+n)
    evidence, metrics = q.run(position=0,vendor_id=1,product_code=2,seconds=1)
    assert metrics.bad_wkc == 0
    assert metrics.enable_drive is False
    assert evidence.argv[-1] == "0"


def test_soem_cycle_metrics():
    stdout = '{"cycles":1000,"cycle_ns":1000000,"expected_wkc":6,"last_wkc":6,"bad_wkc":0,"max_abs_jitter_ns":9000,"mean_abs_jitter_ns":1900.0,"deadline_misses":0,"dc_time_ns":123,"slave_count":2}\n'
    q=SoemCycleQualifier(runner=lambda a,t:ev(a,t,stdout),which=lambda n:"/x/"+n)
    _,m=q.run("eth1",seconds=1)
    assert m.slave_count==2 and m.bad_wkc==0


def test_sdo_expedited_download_upload_and_abort():
    bus=FakeBus([
        CanFrame(0x581,b"\x60\x40\x60\x00\x00\x00\x00\x00"),
        CanFrame(0x581,b"\x4b\x41\x60\x00\x27\x00\x00\x00"),
    ])
    sdo=CanopenSdoClient(bus,1)
    sdo.download_u16(0x6040,0,0x0006)
    assert sdo.upload_u16(0x6041,0)==0x0027
    assert bus.sent[0].can_id==0x601

    abort_bus=FakeBus([
        CanFrame(0x581,b"\x80\x00\x20\x00\x00\x00\x02\x06")
    ])
    with pytest.raises(SdoAbort):
        CanopenSdoClient(abort_bus,1).upload(0x2000,0)


def test_cia402_state_machine_with_fake_sdo():
    class FakeSdo:
        def __init__(self):
            self.states=iter((0x0040,0x0021,0x0023,0x0027))
            self.writes=[]
        def download_i8(self,*a): self.writes.append(a)
        def download_u16(self,*a): self.writes.append(a)
        def upload_u16(self,*a): return next(self.states)
    bus=FakeBus()
    node=CanopenCiA402Node(bus,1,FakeSdo())
    assert node.enable_operation(8)==CiA402State.OPERATION_ENABLED
    assert bus.sent[0].data==b"\x01\x01"
    assert decode_state(0x0008)==CiA402State.FAULT


def test_heartbeat_emcy_and_cyclictest_parser():
    hb=wait_for_heartbeat(FakeBus([CanFrame(0x705,b"\x05")]),5)
    assert hb.state is NmtState.OPERATIONAL
    emcy=parse_emcy(CanFrame(0x085,b"\x10\x23\x01abcde"))
    assert emcy.node_id==5 and emcy.error_code==0x2310
    m=parse_cyclictest_metrics("T: 0 Min: 2 Act: 3 Avg: 4 Max: 11")
    assert m.max_us==11


def test_labgrid_and_session_cleanup(tmp_path: Path):
    commands=[]
    def runner(argv,timeout):
        commands.append(tuple(argv)); return ev(argv,timeout,"ok")
    lease=LabgridPlaceLease("servo",runner=runner,which=lambda n:"/usr/bin/"+n)

    class Backend:
        def __init__(self): self.safe_calls=0
        def force_safe(self,value=True): assert value; self.safe_calls+=1
    backend=Backend()
    lock=ResourceLock(tmp_path/"bench.lock","bench")
    with ServoHilSession(backend,lock,lease):
        assert lease.acquired
    assert not lease.acquired
    assert backend.safe_calls==2
    assert commands[0][-1]=="acquire" and commands[-1][-1]=="release"


def test_cyclictest_qualifier_uses_requested_1ms_period():
    text="T: 0 Min: 1 Act: 2 Avg: 3 Max: 9\n"
    q=CyclictestQualifier(runner=lambda a,t:ev(a,t,text),which=lambda n:"/usr/bin/cyclictest")
    evidence,metrics=q.run(seconds=1,interval_us=1000)
    assert metrics.max_us==9
    assert "1000" in evidence.argv


def test_pdo_codec_and_standard_mapping_sequence():
    mapping = with_node_id(CIA402_RPDO, 5)
    frame = mapping.encode(
        {
            "controlword": 0x000F,
            "mode": 10,
            "target_torque": -20,
            "target_velocity": 123456,
        }
    )
    assert frame.can_id == 0x205
    decoded = mapping.decode(frame)
    assert decoded["target_torque"] == -20
    assert decoded["target_velocity"] == 123456

    class Recorder:
        def __init__(self):
            self.calls = []
        def download_u32(self, *args): self.calls.append(("u32",) + args)
        def download_u8(self, *args): self.calls.append(("u8",) + args)

    recorder = Recorder()
    configure_pdo_mapping(
        recorder,
        mapping_index=0x1600,
        communication_index=0x1400,
        mapping=mapping,
        transmission_type=1,
    )
    assert recorder.calls[0] == ("u32", 0x1400, 1, mapping.cob_id | 0x80000000)
    assert ("u8", 0x1600, 0, len(mapping.entries)) in recorder.calls
    assert recorder.calls[-1] == ("u32", 0x1400, 1, mapping.cob_id)


def test_pdo_rejects_payload_above_classic_can_limit():
    entries = tuple(
        PdoMappingEntry(f"x{i}", 0x2000 + i, 0, 32)
        for i in range(3)
    )
    with pytest.raises(ValueError, match="64 bits"):
        PdoMapping(0x200, entries)

from pathlib import Path

from boards.raspberry_pi import probe_controller_environment


def test_controller_probe_reports_tools_and_interfaces(tmp_path: Path):
    net = tmp_path / "net"
    net.mkdir()
    (net / "eth0").mkdir()
    (net / "can0").mkdir()

    paths = {
        "cyclictest": "/usr/bin/cyclictest",
        "ethercat": "/usr/local/bin/ethercat",
    }

    env = probe_controller_environment(
        tools=("cyclictest", "ethercat", "slaveinfo"),
        sysfs_net=net,
        which=lambda name: paths.get(name),
    )

    assert env.network_interfaces == ("can0", "eth0")
    assert env.tool("cyclictest").available
    assert env.tool("ethercat").path == "/usr/local/bin/ethercat"
    assert not env.tool("slaveinfo").available

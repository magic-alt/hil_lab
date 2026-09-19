# Zynq PS/PL AXI control plane

The PS/PL control ABI is a 4 KiB AXI4-Lite register window shared by AX7010 and AXU2CGB.

## Fixed identity

| Offset | Register |
|---:|---|
| 0x000 | magic = 0x48494c32 (HIL2) |
| 0x004 | ABI version = 0x00010000 |
| 0x008 | backend ID |
| 0x00c | capability bitmap |
| 0x010 | hardware tick rate |
| 0x014 | counter width |
| 0x018/0x01c | 64-bit hardware timestamp |
| 0x02c | bitstream/build ID |

Backend IDs:

- AX7010: 0x00007010
- AXU2CGB: 0x0002c600

## Control/status

0x020 control bits:

- bit0 HIL enable
- bit1 FORCE_SAFE
- bit2 clear-fault pulse
- bit3 ABZ enable
- bit4 ABZ forward direction

Reset state is fail-safe: HIL disabled and FORCE_SAFE asserted.

PWM snapshot starts at 0x040 with a 0x10-byte stride per phase: period/high/low. Valid/fault/sequence registers are at 0x06c/0x070/0x034.

## Timestamped event FIFO

Event staging is 0x100..0x114; status is 0x118. The PL FIFO stores timestamp/mask/value/event-id and dispatches only when the deterministic DIO scheduler is idle. FORCE_SAFE clears the FIFO.

The FIFO memory is explicitly marked `ram_style="block"` so a 64-entry default queue maps naturally to BRAM on Xilinx devices.

## Linux UIO

`host.hil.transports.ZynqUioTransport` mmaps the register page from `/dev/uioN` and implements the common backend transport operations.

Example:

~~~python
from host.hil.backends import Ax7010Backend
from host.hil.transports import ZynqUioTransport

transport = ZynqUioTransport.open(
    "/dev/uio0",
    expected_backend_type="zynq7010_ax7010",
    hardware_revision="AX7010-r1",
)
backend = Ax7010Backend(transport)
~~~

Device-tree templates are under each board's `linux/` directory. The UIO base address must match the Vivado Address Editor before deployment.

## Physical qualification boundary

Cloud CI verifies the register ABI, AXI protocol behavior and Linux transport semantics. It does not prove PS DDR/FIXED_IO setup, Vivado timing closure or physical DUT wiring. Those remain C5/G0 board qualification evidence.

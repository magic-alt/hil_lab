import unittest

from hil_pru_protocol import (
    MAGIC,
    MSG_HELLO,
    MSG_RESPONSE_BIT,
    PROTOCOL_VERSION,
    WIRE,
    Message,
    ticks_to_us,
    us_to_ticks,
)


class ProtocolTests(unittest.TestCase):
    def test_wire_size_is_32_bytes(self) -> None:
        self.assertEqual(WIRE.size, 32)

    def test_round_trip(self) -> None:
        original = Message(
            type=MSG_HELLO,
            seq=0x12345678,
            flags=0x11,
            arg0=1,
            arg1=2,
            arg2=3,
            arg3=4,
        )
        decoded = Message.unpack(original.pack())
        self.assertEqual(decoded, original)
        self.assertEqual(decoded.magic, MAGIC)
        self.assertEqual(decoded.version, PROTOCOL_VERSION)

    def test_response_validation(self) -> None:
        Message(type=MSG_HELLO | MSG_RESPONSE_BIT, seq=7).validate_response(MSG_HELLO, 7)
        with self.assertRaises(RuntimeError):
            Message(type=MSG_HELLO | MSG_RESPONSE_BIT, seq=8).validate_response(MSG_HELLO, 7)

    def test_tick_conversion(self) -> None:
        self.assertEqual(us_to_ticks(1.0, 200_000_000), 200)
        self.assertAlmostEqual(ticks_to_us(200, 200_000_000), 1.0)


if __name__ == "__main__":
    unittest.main()

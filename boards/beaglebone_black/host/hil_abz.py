from __future__ import annotations


def transition_ticks_from_rpm(
    rpm: float,
    ppr: int,
    tick_hz: int,
) -> int:
    if rpm <= 0:
        raise ValueError("rpm must be > 0")
    if ppr <= 0:
        raise ValueError("ppr must be > 0")
    if tick_hz <= 0:
        raise ValueError("tick_hz must be > 0")

    transitions_per_second = (rpm / 60.0) * ppr * 4.0
    return int(round(tick_hz / transitions_per_second))


def transition_ticks_from_hz(
    transition_hz: float,
    tick_hz: int,
) -> int:
    if transition_hz <= 0:
        raise ValueError("transition_hz must be > 0")
    if tick_hz <= 0:
        raise ValueError("tick_hz must be > 0")
    return int(round(tick_hz / transition_hz))


def rpm_from_transition_ticks(
    transition_ticks: int,
    ppr: int,
    tick_hz: int,
) -> float:
    if transition_ticks <= 0:
        raise ValueError("transition_ticks must be > 0")
    if ppr <= 0:
        raise ValueError("ppr must be > 0")
    if tick_hz <= 0:
        raise ValueError("tick_hz must be > 0")

    transition_hz = tick_hz / transition_ticks
    return transition_hz * 60.0 / (ppr * 4.0)


def encode_config_flags(direction: str, initial_phase: int) -> int:
    if direction not in {"forward", "reverse"}:
        raise ValueError("direction must be forward or reverse")
    if initial_phase not in {0, 1, 2, 3}:
        raise ValueError("initial_phase must be 0..3")

    direction_bit = 0 if direction == "forward" else 1
    return direction_bit | (initial_phase << 8)


def decode_config_flags(flags: int) -> tuple[str, int]:
    direction = "reverse" if (flags & 1) else "forward"
    initial_phase = (flags >> 8) & 3
    return direction, initial_phase

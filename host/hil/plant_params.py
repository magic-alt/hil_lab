from __future__ import annotations

from dataclasses import dataclass
import math


Q16 = 1 << 16
Q32 = 1 << 32


def _q16(value: float) -> int:
    scaled = int(round(value * Q16))
    if not -(1 << 31) <= scaled <= (1 << 31) - 1:
        raise ValueError(f"Q16.16 coefficient out of range: {value}")
    return scaled


def _q32_positive(value: float) -> int:
    scaled = int(round(value * Q32))
    if not 0 <= scaled <= (1 << 31) - 1:
        raise ValueError(f"signed-positive Q0.32 coefficient out of range: {value}")
    return scaled


@dataclass(frozen=True)
class PmsmPhysicalParameters:
    rs_ohm: float
    ld_h: float
    lq_h: float
    flux_wb: float
    pole_pairs: int
    inertia_kg_m2: float
    viscous_nm_per_rad_s: float
    sample_time_s: float

    def __post_init__(self) -> None:
        if self.rs_ohm < 0:
            raise ValueError("rs_ohm must be >= 0")
        if self.ld_h <= 0 or self.lq_h <= 0:
            raise ValueError("Ld/Lq must be > 0")
        if self.flux_wb < 0:
            raise ValueError("flux_wb must be >= 0")
        if self.pole_pairs <= 0:
            raise ValueError("pole_pairs must be > 0")
        if self.inertia_kg_m2 <= 0:
            raise ValueError("inertia must be > 0")
        if self.viscous_nm_per_rad_s < 0:
            raise ValueError("viscous damping must be >= 0")
        if self.sample_time_s <= 0:
            raise ValueError("sample_time_s must be > 0")


@dataclass(frozen=True)
class PmsmQ16Coefficients:
    k_vd_q16: int
    k_vq_q16: int
    k_r_d_q16: int
    k_r_q_q16: int
    k_cross_d_q16: int
    k_cross_q_q16: int
    k_flux_q16: int
    k_torque_q16: int
    k_accel_q16: int
    k_damp_q16: int
    k_theta_q16: int
    k_rad_to_turn_q32: int


def derive_q16_coefficients(p: PmsmPhysicalParameters) -> PmsmQ16Coefficients:
    ts = p.sample_time_s
    k_theta = ts / (2.0 * math.pi)
    return PmsmQ16Coefficients(
        k_vd_q16=_q16(ts / p.ld_h),
        k_vq_q16=_q16(ts / p.lq_h),
        k_r_d_q16=_q16(ts * p.rs_ohm / p.ld_h),
        k_r_q_q16=_q16(ts * p.rs_ohm / p.lq_h),
        k_cross_d_q16=_q16(ts * p.lq_h / p.ld_h),
        k_cross_q_q16=_q16(ts * p.ld_h / p.lq_h),
        k_flux_q16=_q16(ts * p.flux_wb / p.lq_h),
        k_torque_q16=_q16(1.5 * p.pole_pairs * p.flux_wb),
        k_accel_q16=_q16(ts / p.inertia_kg_m2),
        k_damp_q16=_q16(ts * p.viscous_nm_per_rad_s / p.inertia_kg_m2),
        # Retained for the compatibility plant. Q16.16 is coarse at 20 kHz;
        # the closed-loop phase path therefore uses k_rad_to_turn_q32.
        k_theta_q16=_q16(k_theta),
        k_rad_to_turn_q32=_q32_positive(k_theta),
    )

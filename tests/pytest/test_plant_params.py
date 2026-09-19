import math

from host.hil.plant_params import (
    PmsmPhysicalParameters,
    derive_q16_coefficients,
)


def test_reference_48v_motor_coefficients_are_reproducible():
    # Reference motor from the lab notes: Rs=0.694 ohm, L=0.603 mH,
    # Kt=0.094 Nm/A, p=10. For SPMSM psi=Kt/(1.5*p).
    p = PmsmPhysicalParameters(
        rs_ohm=0.694,
        ld_h=0.000603,
        lq_h=0.000603,
        flux_wb=0.094 / (1.5 * 10),
        pole_pairs=10,
        inertia_kg_m2=0.0001,
        viscous_nm_per_rad_s=0.0001,
        sample_time_s=50e-6,
    )
    c = derive_q16_coefficients(p)

    assert c.k_vd_q16 > 5000
    assert c.k_r_d_q16 > 3000
    assert abs(c.k_torque_q16 / 65536.0 - 0.094) < 1e-4
    assert abs(c.k_rad_to_turn_q32 / 2**32 - 50e-6/(2*math.pi)) < 1e-10


def test_invalid_physical_parameters_are_rejected():
    try:
        PmsmPhysicalParameters(
            rs_ohm=1,
            ld_h=0,
            lq_h=1e-3,
            flux_wb=0.01,
            pole_pairs=4,
            inertia_kg_m2=1e-4,
            viscous_nm_per_rad_s=0,
            sample_time_s=50e-6,
        )
    except ValueError as exc:
        assert "Ld/Lq" in str(exc)
    else:
        raise AssertionError("expected ValueError")

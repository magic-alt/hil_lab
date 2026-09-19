# PMSM closed-loop HIL datapath

The closed-loop plant is now an explicit chain instead of an opaque Vd/Vq-only block:

~~~text
DUT PWM period/high
       |
       v
pwm_ticks_to_duty_q16
       |
       v
averaged_inverter_abc_q16
       |
       v
Clarke abc -> alpha/beta
       |
       v
Park(alpha/beta, electrical phase)
       |
       v
pmsm_dq_plant_q16
       |
       +---- torque -> mechanics -> omega
       |
       v
inverse Park / inverse Clarke
       |
       +---- Ia/Ib/Ic -> DAC code mapper
       |
       +---- mechanical phase -> 24-bit encoder word
~~~

Electrical and mechanical phases use Q0.32 modulo-turn accumulators. This avoids the poor 20 kHz angle-step resolution of the legacy Q16.16 `k_theta` term.

## Fixed point

- plant values: signed Q16.16;
- PWM duty: unsigned Q16.16, 0..1;
- phase: unsigned Q0.32 turns;
- sin/cos: signed Q16.16;
- DAC mapping: signed Q16.16 signal * Q16.16 codes/unit, then saturate to 16-bit code.

The sin/cos primitive is a 64-step-per-quadrant LUT (256 angular sectors per turn). It is intended for FPGA-Lite/bring-up; a higher-resolution BRAM/CORDIC implementation can replace it without changing the transform interfaces.

## Physical coefficient generator

`host.hil.plant_params.derive_q16_coefficients()` converts Rs/Ld/Lq/flux/pole-pairs/J/B/Ts into the discrete coefficients used by the RTL.

For a 20 kHz model, `k_rad_to_turn_q32 = Ts/(2*pi)` is generated separately in Q0.32 for accurate phase accumulation.

## ZU2CG feedback integration

The next board integration uses:

- captured PWM as plant excitation;
- plant Ia/Ib/Ic/Vbus mapped into the AD3542R four-channel stream;
- plant mechanical phase as the dynamic SPI encoder word.

The calibration pattern remains selectable and is never removed; it is needed to qualify the analog path independently of the plant.

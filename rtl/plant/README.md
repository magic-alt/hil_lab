# Plant RTL

Canonical Architecture v2 home for deterministic inverter, motor and mechanical plant models.

Current modules:

- `averaged_inverter_abc_q16.v` — Q16.16 duty/Vbus averaged two-level inverter with common-mode removal;
- `pmsm_dq_plant_q16.v` — existing fixed-step FPGA-Lite PMSM dq + mechanics compatibility model;
- `pmsm_mechanics_q16.v` — reusable torque/load/viscous-damping mechanical state integrator.

The compatibility PMSM-lite block still accepts `vd/vq` directly. A later integration step should connect captured PWM -> duty reconstruction -> averaged inverter -> Clarke/Park -> PMSM electrical model rather than hiding those transformations inside an opaque monolith.

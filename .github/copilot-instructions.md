# GitHub Copilot instructions for hil_lab

- Read the root `AGENTS.md` before editing.
- Synthesizable FPGA code under `rtl/` is Verilog-2001 (`.v`) only.
- Do not introduce SystemVerilog, HLS, vendor primitives, gated clocks, or hidden CDC crossings into reusable RTL.
- External asynchronous signals require an explicit synchronizer or a documented alternative CDC primitive in a board-specific wrapper.
- Use non-blocking assignments for sequential state.
- Preserve signal-level safety boundaries; do not add direct DC-bus, motor-phase or other high-energy control paths to G0.
- Every behavioral RTL change needs a self-checking simulation when practical.
- Run `make verify` before considering a change complete.
- Do not commit generated Vivado or simulator output.

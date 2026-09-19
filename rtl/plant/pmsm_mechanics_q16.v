`default_nettype none

// Reusable fixed-step mechanical state integrator.
//
// All data and coefficients use signed Q16.16. k_accel, k_damp and k_theta
// already include the selected fixed model step Ts.
//
//   d_omega = k_accel * (Tmotor - Tload) - k_damp * omega
//   omega[k+1] = omega + d_omega
//   theta[k+1] = theta + k_theta * omega
module pmsm_mechanics_q16 (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    update_en,

    input  wire signed [31:0]      motor_torque_q16,
    input  wire signed [31:0]      load_torque_q16,
    input  wire signed [31:0]      k_accel_q16,
    input  wire signed [31:0]      k_damp_q16,
    input  wire signed [31:0]      k_theta_q16,

    output reg  signed [31:0]      omega_m_q16,
    output reg  signed [31:0]      theta_m_q16,
    output wire signed [31:0]      delta_omega_q16
);

    function signed [31:0] qmul;
        input signed [31:0] a;
        input signed [31:0] b;
        reg signed [63:0] product;
        begin
            product = a * b;
            qmul = product >>> 16;
        end
    endfunction

    wire signed [31:0] torque_error_q16;
    wire signed [31:0] damping_step_q16;
    wire signed [31:0] theta_step_q16;

    assign torque_error_q16 = motor_torque_q16 - load_torque_q16;
    assign damping_step_q16 = qmul(k_damp_q16, omega_m_q16);
    assign delta_omega_q16 =
        qmul(k_accel_q16, torque_error_q16) -
        damping_step_q16;
    assign theta_step_q16 = qmul(k_theta_q16, omega_m_q16);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            omega_m_q16 <= 32'sd0;
            theta_m_q16 <= 32'sd0;
        end else if (update_en) begin
            omega_m_q16 <= omega_m_q16 + delta_omega_q16;
            theta_m_q16 <= theta_m_q16 + theta_step_q16;
        end
    end

endmodule

`default_nettype wire
